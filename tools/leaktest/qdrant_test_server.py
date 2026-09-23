#!/usr/bin/env python3
"""Qdrant-compatible REST server for local testing.

Serves the subset of the Qdrant REST API that agent memory uses (collections,
upsert, retrieve, query, search, scroll, count, facet, delete and payload
updates). Storage and filtering are handled by qdrant-client's local mode,
which implements Qdrant's filter semantics, so filters behave as they do on
a real Qdrant server.

Use it when a real Qdrant instance is not available. To test against real
Qdrant instead:  docker run -p 6333:6333 qdrant/qdrant

    python3 qdrant_test_server.py --port 6333
"""

import argparse
import json
import re
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from qdrant_client import QdrantClient, models

VERSION = "1.15.0"

client = QdrantClient(":memory:")
lock = threading.Lock()


class NotFound(Exception):
    pass


def dump(value):
    if isinstance(value, list):
        return [dump(v) for v in value]
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return value


def selector(body):
    if body.get("points") is not None:
        return models.PointIdsList(points=body["points"])
    if body.get("filter") is not None:
        return models.FilterSelector(filter=models.Filter.model_validate(body["filter"]))
    raise ValueError("points or filter selector required")


def require_collection(name):
    if not client.collection_exists(name):
        raise NotFound(f"Collection `{name}` doesn't exist!")


def completed():
    return {"operation_id": 0, "status": "completed"}


def filt(body, field="filter"):
    raw = body.get(field)
    return models.Filter.model_validate(raw) if raw is not None else None


def handle(method, path, body):
    if method == "GET" and path == "/":
        return {"title": "qdrant - vector search engine", "version": VERSION}
    if method == "GET" and path in ("/healthz", "/livez", "/readyz"):
        return "ok"
    if method == "GET" and path == "/collections":
        return {"collections": [{"name": c.name} for c in client.get_collections().collections]}

    m = re.fullmatch(r"/collections/([^/]+)(/.*)?", path)
    if not m:
        raise NotFound(f"unknown path {path}")
    name, rest = m.group(1), m.group(2) or ""

    if rest == "":
        if method == "PUT":
            spec = models.CreateCollection.model_validate(body)
            client.create_collection(name, vectors_config=spec.vectors,
                                     sparse_vectors_config=spec.sparse_vectors)
            return True
        if method == "DELETE":
            return client.delete_collection(name)
        if method == "GET":
            require_collection(name)
            return {"status": "green", "points_count": client.count(name, exact=True).count}
    if rest == "/exists" and method == "GET":
        return {"exists": client.collection_exists(name)}

    require_collection(name)

    if rest == "/index" and method == "PUT":
        return completed()  # local mode needs no payload indexes

    if rest == "/points" and method == "PUT":
        if "batch" in body:
            points = models.PointsBatch.model_validate(body).batch
        else:
            points = models.PointsList.model_validate(body).points
        client.upsert(name, points=points)
        return completed()
    if rest == "/points" and method == "POST":
        req = models.PointRequest.model_validate(body)
        with_payload = True if req.with_payload is None else req.with_payload
        return dump(client.retrieve(name, ids=req.ids, with_payload=with_payload,
                                    with_vectors=req.with_vector or False))

    pm = re.fullmatch(r"/points/([^/]+)", rest)
    if pm and method == "GET" and pm.group(1) not in ("scroll", "count", "query", "search", "delete", "payload", "facet"):
        raw_id = pm.group(1)
        point_id = int(raw_id) if raw_id.isdigit() else raw_id
        found = client.retrieve(name, ids=[point_id], with_payload=True)
        if not found:
            raise NotFound(f"No point with id {raw_id} found")
        return dump(found[0])

    if method == "POST" and rest == "/points/query":
        req = models.QueryRequest.model_validate(body)
        resp = client.query_points(
            name, query=req.query, prefetch=req.prefetch, query_filter=req.filter,
            using=req.using, limit=req.limit or 10, offset=req.offset,
            score_threshold=req.score_threshold, search_params=req.params,
            with_payload=False if req.with_payload is None else req.with_payload,
            with_vectors=req.with_vector or False,
        )
        return dump(resp)
    if method == "POST" and rest == "/points/search":
        resp = client.query_points(
            name, query=body["vector"], query_filter=filt(body), limit=body.get("limit", 10),
            offset=body.get("offset"), score_threshold=body.get("score_threshold"),
            with_payload=body.get("with_payload", False), with_vectors=body.get("with_vector", False),
        )
        return dump(resp.points)
    if method == "POST" and rest == "/points/scroll":
        req = models.ScrollRequest.model_validate(body)
        records, next_offset = client.scroll(
            name, scroll_filter=req.filter, limit=req.limit or 10, offset=req.offset,
            with_payload=True if req.with_payload is None else req.with_payload,
            with_vectors=req.with_vector or False, order_by=req.order_by,
        )
        return {"points": dump(records), "next_page_offset": next_offset}
    if method == "POST" and rest == "/points/count":
        req = models.CountRequest.model_validate(body)
        return dump(client.count(name, count_filter=req.filter, exact=True))
    if method == "POST" and rest == "/facet":
        req = models.FacetRequest.model_validate(body)
        return dump(client.facet(name, key=req.key, facet_filter=req.filter,
                                 limit=req.limit or 10, exact=True))
    if method == "POST" and rest == "/points/delete":
        client.delete(name, points_selector=selector(body))
        return completed()
    if rest == "/points/payload" and method in ("POST", "PUT"):
        if method == "POST":
            client.set_payload(name, payload=body["payload"], points=selector(body), key=body.get("key"))
        else:
            client.overwrite_payload(name, payload=body["payload"], points=selector(body))
        return completed()
    if method == "POST" and rest == "/points/payload/delete":
        client.delete_payload(name, keys=body["keys"], points=selector(body))
        return completed()
    if method == "POST" and rest == "/points/payload/clear":
        client.clear_payload(name, points_selector=selector(body))
        return completed()

    raise NotFound(f"unsupported: {method} {path}")


class Handler(BaseHTTPRequestHandler):
    verbose = False

    def _serve(self):
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b""
        path = self.path.split("?", 1)[0]
        try:
            body = json.loads(raw) if raw else {}
            with lock:
                result = handle(self.command, path, body)
            status, payload = 200, {"result": result, "status": "ok", "time": 0.0}
        except NotFound as e:
            status, payload = 404, {"status": {"error": f"Not found: {e}"}, "time": 0.0}
        except Exception as e:  # report bad requests the way Qdrant does
            status, payload = 400, {"status": {"error": f"Bad request: {e}"}, "time": 0.0}
        data = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    do_GET = do_POST = do_PUT = do_DELETE = do_PATCH = _serve

    def log_message(self, fmt, *args):
        if self.verbose:
            super().log_message(fmt, *args)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=6333)
    parser.add_argument("--verbose", action="store_true", help="log every request")
    args = parser.parse_args()
    Handler.verbose = args.verbose
    server = HTTPServer((args.host, args.port), Handler)
    print(f"Qdrant-compatible test server on http://{args.host}:{args.port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
