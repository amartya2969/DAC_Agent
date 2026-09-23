# Memory isolation: the tenant guard

## The problem

Shared agents keep long-term memory and retrieval context in one vector store
for all customers. The only thing separating customers is a filter on each
query, and that filter is usually built by application code the model can
influence. A prompt injection or a bug that drops or rewrites the filter lets
one tenant read, overwrite or delete another tenant's memories.

Credential brokers (Okta Agent Gateway, Aembit and similar) scope the tokens an
agent uses to call APIs. They do not decide which rows of a shared memory
store come back, because every tenant's query goes to the same store with the
same credentials.

## What the guard does

The sidecar serves the Qdrant REST API under `/vector/` and enforces the tenant
boundary outside the agent's code:

| Operation | Enforcement |
|---|---|
| Search, query, scroll, count, facet, distance matrix | A mandatory `tenant_id` condition is ANDed into the filter, including every prefetch |
| Retrieve by id, get point | Points owned by other tenants are removed from the response; a single foreign point reads as not found |
| Upsert | Every point is stamped with the caller's tenant; overwriting a point owned by another tenant is refused |
| Delete, set/overwrite/delete payload, delete vectors | Id selectors become `tenant_id = caller AND has_id [...]` filters; the tenant tag cannot be changed or removed |
| Create collection or index, collection info, version, health | Passed through |
| Drop or change collections, snapshots, aliases, clear payload, recommend/discover, queries by point id, batch updates, anything else | Refused (default deny) |

Every response is re-checked: points not tagged with the caller's tenant are
dropped. Untagged legacy points are therefore hidden too.

Each request produces a structured audit event with the user, the operation
and the outcome:

- `ALLOWED`: normal traffic.
- `CONTAINED`: a cross-tenant attempt ran, but only inside the caller's tenant.
- `BLOCKED`: the request was refused.

```json
{"event":"SECURITY_ALERT","user":"alice@example.test","target":"vector-store:memories","intent":"query","outcome":"CONTAINED","reason":"filter referenced another tenant; scoped to \"alice\""}
```

The agent never holds the store's API key. The sidecar injects it.

## Using it

Run the sidecar with the vector store's address:

```bash
VECTOR_STORE_URL=http://qdrant:6333 \
VECTOR_STORE_API_KEY=... \
VECTOR_TENANT_KEY=tenant_id \
./dac-sidecar
```

| Variable | Default | Meaning |
|---|---|---|
| `VECTOR_STORE_URL` | (off) | Qdrant REST endpoint; enables the guard |
| `VECTOR_STORE_API_KEY` | (none) | Sent to the store as `api-key` |
| `VECTOR_TENANT_KEY` | `tenant_id` | Payload key that holds the tenant; dotted paths such as `metadata.tenant_id` are supported |

Framework defaults: LangChain stores metadata under `metadata`, so use
`metadata.tenant_id`. LlamaIndex stores it at the top level (`tenant_id`).
Mem0 scopes by `user_id`.

Point the agent's Qdrant client at the sidecar and pass the tenant from the
authenticated session:

```python
client = QdrantClient(
    url="http://sidecar:8080",
    prefix="vector",
    headers={"X-Tenant-ID": session.tenant_id, "X-User-ID": session.user_id},
)
```

## Verifying it

```bash
cd sidecar && go test ./...          # unit tests for rewriting, filtering and denial
./scripts/memory_isolation_demo.sh   # 15 attacks, direct vs through the sidecar
./scripts/stack_leaktest.sh          # LangChain, LlamaIndex and Mem0 scenarios
```

The framework results are in [STACK_LEAK_REPORT.md](STACK_LEAK_REPORT.md).

See [`tools/leaktest/README.md`](../tools/leaktest/README.md) for the attack list
and results.

## Limitations

- **The tenant comes from a header.** The guard trusts `X-Tenant-ID`, which the
  application must set from the authenticated session, never from model output.
  Anything that can set arbitrary headers on the agent's store requests can pick
  a tenant. The next step is to replace the header with a signed session token
  issued by the control plane.
- **The ownership check on upsert is check-then-write.** A concurrent write
  between the lookup and the upsert is not covered.
- **Id-based writes to another tenant's points are skipped silently.** The store
  just finds no match, so they are logged as `ALLOWED`, not `CONTAINED`.
- **Only data in the vector store is protected.** For example, Mem0 keeps
  memory history in a local SQLite database, and the guard does not see it.
- **Only the Qdrant REST API is covered.** gRPC traffic, other vector stores and
  memory layers are not yet supported.
- **Some operations are refused, not supported.** This includes queries that
  reference stored points by id (recommend, discover, `lookup_from`). Agents that
  depend on them need an exception.
