// Tenant Guard - deterministic tenant isolation for agent memory
//
// Shared agents keep long-term memory and RAG context in one vector store.
// When the tenant filter is built by the model (or forgotten by the app),
// one tenant can read, overwrite or delete another tenant's memories.
//
// The guard sits between the agent and the vector store (Qdrant REST API)
// and enforces the tenant boundary outside the agent's code:
//
//   - reads:   a mandatory tenant condition is ANDed into every filter
//   - writes:  every point is stamped with the caller's tenant, and points
//     owned by another tenant cannot be overwritten
//   - id-based updates/deletes are rewritten into tenant-scoped filters
//   - responses are re-checked and points from other tenants are dropped
//   - anything not on the allowlist is refused (default deny)
//
// The tenant comes from the X-Tenant-ID header, which the application sets
// from the authenticated session. It is never taken from model output.
//
// Agents point their Qdrant client at the sidecar with the "/vector" prefix:
//
//	QdrantClient(url="http://sidecar:8080", prefix="vector",
//	             headers={"X-Tenant-ID": session.tenant_id})

package main

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"net/url"
	"strings"
	"time"
)

const (
	vectorRoutePrefix  = "/vector"
	maxVectorBodyBytes = 16 << 20
	tenantHeader       = "X-Tenant-ID"
)

type opKind int

const (
	opDeny          opKind = iota
	opPassthrough          // no tenant data involved
	opUpsert               // PUT points
	opRetrieve             // POST points {ids}
	opGetPoint             // GET points/{id}
	opFilteredRead         // search, query, scroll, count, facet, matrix
	opSelectorWrite        // delete, set/overwrite/delete payload, delete vectors
)

type vectorOp struct {
	kind       opKind
	name       string
	collection string
	reason     string // why the operation is denied
}

// TenantGuard enforces tenant isolation on vector store traffic.
type TenantGuard struct {
	upstream  *url.URL
	tenantKey string
	apiKey    string
	client    *http.Client
}

// NewTenantGuard creates a guard in front of the vector store at upstreamURL.
func NewTenantGuard(upstreamURL, tenantKey, apiKey string) (*TenantGuard, error) {
	u, err := url.Parse(upstreamURL)
	if err != nil || u.Scheme == "" || u.Host == "" {
		return nil, fmt.Errorf("invalid vector store URL %q", upstreamURL)
	}
	if tenantKey == "" {
		tenantKey = "tenant_id"
	}
	return &TenantGuard{
		upstream:  u,
		tenantKey: tenantKey,
		apiKey:    apiKey,
		client:    &http.Client{Timeout: 30 * time.Second},
	}, nil
}

// guardResult collects what the guard did to a request, for the audit log.
type guardResult struct {
	contained []string // cross-tenant attempts that were neutralised
}

func (g *guardResult) contain(format string, args ...interface{}) {
	g.contained = append(g.contained, fmt.Sprintf(format, args...))
}

// ServeHTTP handles requests under /vector/.
func (g *TenantGuard) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	path := strings.TrimPrefix(r.URL.Path, vectorRoutePrefix)
	if path == "" {
		path = "/"
	}

	tenant := strings.TrimSpace(r.Header.Get(tenantHeader))
	userID := r.Header.Get("X-User-ID")
	if userID == "" {
		userID = tenant
	}
	session := r.Header.Get("X-Session-UUID")

	op := classifyVectorOp(r.Method, path)
	target := "vector-store"
	if op.collection != "" {
		target = "vector-store:" + op.collection
	}
	intent := op.name

	if op.kind == opDeny {
		LogBlocked(userID, target, r.Method+" "+path, op.reason, session)
		writeVectorError(w, http.StatusForbidden, op.reason)
		return
	}

	// Only the version check and health probes may run without a tenant.
	if tenant == "" && !(op.kind == opPassthrough && isAnonymousOp(op.name)) {
		reason := "missing tenant identity (" + tenantHeader + ")"
		LogBlocked(userID, target, intent, reason, session)
		writeVectorError(w, http.StatusForbidden, reason)
		return
	}

	var body []byte
	if r.Body != nil {
		var err error
		body, err = io.ReadAll(io.LimitReader(r.Body, maxVectorBodyBytes+1))
		if err != nil {
			writeVectorError(w, http.StatusBadRequest, "cannot read request body")
			return
		}
		if len(body) > maxVectorBodyBytes {
			LogBlocked(userID, target, intent, "request body too large", session)
			writeVectorError(w, http.StatusRequestEntityTooLarge, "request body too large")
			return
		}
	}

	if op.kind == opPassthrough {
		resp, respBody, err := g.forward(r.Context(), r.Method, path, r.URL.RawQuery, body, r.Header)
		if err != nil {
			writeVectorError(w, http.StatusBadGateway, "vector store unreachable")
			return
		}
		LogTraffic(userID, target, intent, session, int64(len(respBody)))
		writeUpstream(w, resp, respBody)
		return
	}

	res := &guardResult{}
	var req map[string]interface{}
	if op.kind != opGetPoint {
		var err error
		req, err = decodeObject(body)
		if err != nil {
			writeVectorError(w, http.StatusBadRequest, "request body must be a JSON object")
			return
		}
	}

	// Rewrite the request so the store can only act inside this tenant.
	var prefs []payloadPref
	var err error
	switch op.kind {
	case opUpsert:
		err = g.scopeUpsert(r.Context(), op.collection, req, tenant, res)
	case opRetrieve:
		prefs = []payloadPref{forcePayload(req, true)}
	case opFilteredRead:
		prefs, err = g.scopeRead(op.name, req, tenant, res)
	case opSelectorWrite:
		err = g.scopeSelectorWrite(op.name, req, tenant, res)
	}
	if err != nil {
		LogBlocked(userID, target, intent, err.Error(), session)
		writeVectorError(w, http.StatusForbidden, err.Error())
		return
	}

	if req != nil {
		body, err = json.Marshal(req)
		if err != nil {
			writeVectorError(w, http.StatusInternalServerError, "cannot encode request")
			return
		}
	}

	resp, respBody, err := g.forward(r.Context(), r.Method, path, r.URL.RawQuery, body, r.Header)
	if err != nil {
		writeVectorError(w, http.StatusBadGateway, "vector store unreachable")
		return
	}

	// Defense in depth: re-check what the store returned.
	if resp.StatusCode >= 200 && resp.StatusCode < 300 && (op.kind == opRetrieve || op.kind == opGetPoint || op.kind == opFilteredRead) {
		filtered, found, ferr := g.filterResponse(op, respBody, tenant, prefs, res)
		if ferr != nil {
			LogBlocked(userID, target, intent, "unreadable vector store response", session)
			writeVectorError(w, http.StatusBadGateway, "unreadable vector store response")
			return
		}
		if !found {
			writeVectorError(w, http.StatusNotFound, "point not found")
			g.audit(userID, target, intent, session, res, 0)
			return
		}
		respBody = filtered
	}

	g.audit(userID, target, intent, session, res, int64(len(respBody)))
	writeUpstream(w, resp, respBody)
}

func (g *TenantGuard) audit(user, target, intent, session string, res *guardResult, bytes int64) {
	if len(res.contained) > 0 {
		LogContained(user, target, intent, strings.Join(res.contained, "; "), session)
		return
	}
	LogTraffic(user, target, intent, session, bytes)
}

func isAnonymousOp(name string) bool {
	return name == "version" || name == "health"
}

// classifyVectorOp maps a Qdrant REST call to an operation. Unknown calls are denied.
func classifyVectorOp(method, path string) vectorOp {
	seg := strings.Split(strings.Trim(path, "/"), "/")
	if len(seg) == 1 && seg[0] == "" {
		seg = nil
	}
	deny := func(reason string) vectorOp { return vectorOp{kind: opDeny, name: "denied", reason: reason} }
	unsupported := deny("operation not allowed for agent traffic: " + method + " " + path)

	if len(seg) == 0 {
		if method == http.MethodGet {
			return vectorOp{kind: opPassthrough, name: "version"}
		}
		return unsupported
	}
	if len(seg) == 1 {
		switch {
		case method == http.MethodGet && (seg[0] == "healthz" || seg[0] == "livez" || seg[0] == "readyz"):
			return vectorOp{kind: opPassthrough, name: "health"}
		case method == http.MethodGet && seg[0] == "collections":
			return vectorOp{kind: opPassthrough, name: "list-collections"}
		}
		return unsupported
	}
	if seg[0] != "collections" {
		return unsupported
	}

	c := seg[1]
	op := func(kind opKind, name string) vectorOp { return vectorOp{kind: kind, name: name, collection: c} }

	if len(seg) == 2 {
		switch method {
		case http.MethodGet:
			return op(opPassthrough, "collection-info")
		case http.MethodPut:
			return op(opPassthrough, "create-collection")
		}
		d := deny("collection administration is not allowed for agent traffic: " + method + " " + path)
		d.collection = c
		return d
	}

	switch seg[2] {
	case "exists":
		if len(seg) == 3 && method == http.MethodGet {
			return op(opPassthrough, "collection-exists")
		}
	case "index":
		if len(seg) == 3 && method == http.MethodPut {
			return op(opPassthrough, "create-index")
		}
	case "facet":
		if len(seg) == 3 && method == http.MethodPost {
			return op(opFilteredRead, "facet")
		}
	case "points":
		if len(seg) == 3 {
			switch method {
			case http.MethodPut:
				return op(opUpsert, "upsert")
			case http.MethodPost:
				return op(opRetrieve, "retrieve")
			}
			break
		}
		rest := strings.Join(seg[3:], "/")
		if method == http.MethodGet && len(seg) == 4 {
			return op(opGetPoint, "get-point")
		}
		if method == http.MethodPut && rest == "payload" {
			return op(opSelectorWrite, "overwrite-payload")
		}
		if method != http.MethodPost {
			break
		}
		switch rest {
		case "search":
			return op(opFilteredRead, "search")
		case "search/batch":
			return op(opFilteredRead, "search-batch")
		case "search/matrix/pairs", "search/matrix/offsets":
			return op(opFilteredRead, "matrix")
		case "query":
			return op(opFilteredRead, "query")
		case "query/batch":
			return op(opFilteredRead, "query-batch")
		case "query/groups":
			return op(opFilteredRead, "query-groups")
		case "scroll":
			return op(opFilteredRead, "scroll")
		case "count":
			return op(opFilteredRead, "count")
		case "delete":
			return op(opSelectorWrite, "delete")
		case "payload":
			return op(opSelectorWrite, "set-payload")
		case "payload/delete":
			return op(opSelectorWrite, "delete-payload")
		case "vectors/delete":
			return op(opSelectorWrite, "delete-vectors")
		case "payload/clear":
			d := deny("clearing payloads would remove the tenant tag; not allowed")
			d.collection = c
			return d
		case "recommend", "recommend/batch", "recommend/groups", "discover", "discover/batch":
			d := deny("id-based recommend/discover queries are not supported by the tenant guard")
			d.collection = c
			return d
		}
	}
	d := unsupported
	d.collection = c
	return d
}

// --- request scoping -------------------------------------------------------

func (g *TenantGuard) tenantCondition(tenant string) map[string]interface{} {
	return map[string]interface{}{
		"key":   g.tenantKey,
		"match": map[string]interface{}{"value": tenant},
	}
}

// scopeFilter returns a filter that matches only this tenant's points and,
// within them, whatever the original filter matched.
func (g *TenantGuard) scopeFilter(original interface{}, tenant string, res *guardResult) map[string]interface{} {
	must := []interface{}{g.tenantCondition(tenant)}
	if original != nil {
		if g.referencesForeignTenant(original, tenant, false) {
			res.contain("filter referenced another tenant; scoped to %q", tenant)
		}
		must = append(must, original)
	}
	return map[string]interface{}{"must": must}
}

// referencesForeignTenant reports whether a filter tries to reach data outside
// the caller's tenant through the tenant key.
func (g *TenantGuard) referencesForeignTenant(node interface{}, tenant string, negated bool) bool {
	switch v := node.(type) {
	case []interface{}:
		for _, item := range v {
			if g.referencesForeignTenant(item, tenant, negated) {
				return true
			}
		}
	case map[string]interface{}:
		if key, ok := v["key"].(string); ok && (key == g.tenantKey || strings.HasPrefix(key, g.tenantKey+".")) {
			if negated {
				return true
			}
			match, ok := v["match"].(map[string]interface{})
			if !ok {
				return true // range, is_null, values_count, ... on the tenant key
			}
			if val, ok := match["value"]; ok {
				s, isStr := val.(string)
				return !isStr || s != tenant
			}
			if anyOf, ok := match["any"].([]interface{}); ok {
				for _, a := range anyOf {
					if s, isStr := a.(string); !isStr || s != tenant {
						return true
					}
				}
				return false
			}
			return true // except, text, ...
		}
		for field, child := range v {
			switch field {
			case "must_not":
				if g.referencesForeignTenant(child, tenant, !negated) {
					return true
				}
			case "must", "should", "filter":
				if g.referencesForeignTenant(child, tenant, negated) {
					return true
				}
			case "min_should":
				if ms, ok := child.(map[string]interface{}); ok && g.referencesForeignTenant(ms["conditions"], tenant, negated) {
					return true
				}
			case "nested":
				if n, ok := child.(map[string]interface{}); ok && g.referencesForeignTenant(n["filter"], tenant, negated) {
					return true
				}
			}
		}
	}
	return false
}

// scopeRead rewrites search/query/scroll/count/facet/matrix requests.
func (g *TenantGuard) scopeRead(name string, req map[string]interface{}, tenant string, res *guardResult) ([]payloadPref, error) {
	switch name {
	case "search", "scroll":
		req["filter"] = g.scopeFilter(req["filter"], tenant, res)
		return []payloadPref{forcePayload(req, name == "scroll")}, nil
	case "count", "facet", "matrix":
		req["filter"] = g.scopeFilter(req["filter"], tenant, res)
		return nil, nil
	case "search-batch":
		searches, ok := req["searches"].([]interface{})
		if !ok {
			return nil, fmt.Errorf("search batch without searches")
		}
		prefs := make([]payloadPref, len(searches))
		for i, s := range searches {
			m, ok := s.(map[string]interface{})
			if !ok {
				return nil, fmt.Errorf("malformed search batch")
			}
			m["filter"] = g.scopeFilter(m["filter"], tenant, res)
			prefs[i] = forcePayload(m, false)
		}
		return prefs, nil
	case "query", "query-groups":
		if err := g.scopeQuery(req, tenant, res); err != nil {
			return nil, err
		}
		if name == "query-groups" {
			if _, ok := req["with_lookup"]; ok {
				return nil, fmt.Errorf("with_lookup is not supported by the tenant guard")
			}
		}
		return []payloadPref{forcePayload(req, false)}, nil
	case "query-batch":
		searches, ok := req["searches"].([]interface{})
		if !ok {
			return nil, fmt.Errorf("query batch without searches")
		}
		prefs := make([]payloadPref, len(searches))
		for i, s := range searches {
			m, ok := s.(map[string]interface{})
			if !ok {
				return nil, fmt.Errorf("malformed query batch")
			}
			if err := g.scopeQuery(m, tenant, res); err != nil {
				return nil, err
			}
			prefs[i] = forcePayload(m, false)
		}
		return prefs, nil
	}
	return nil, fmt.Errorf("unsupported read operation %s", name)
}

// scopeQuery scopes a universal query request and its prefetches.
func (g *TenantGuard) scopeQuery(q map[string]interface{}, tenant string, res *guardResult) error {
	if err := checkQueryInput(q["query"]); err != nil {
		return err
	}
	if _, ok := q["lookup_from"]; ok {
		return fmt.Errorf("lookup_from is not supported by the tenant guard")
	}
	q["filter"] = g.scopeFilter(q["filter"], tenant, res)

	switch p := q["prefetch"].(type) {
	case nil:
	case map[string]interface{}:
		return g.scopeQuery(p, tenant, res)
	case []interface{}:
		for _, item := range p {
			m, ok := item.(map[string]interface{})
			if !ok {
				return fmt.Errorf("malformed prefetch")
			}
			if err := g.scopeQuery(m, tenant, res); err != nil {
				return err
			}
		}
	default:
		return fmt.Errorf("malformed prefetch")
	}
	return nil
}

// checkQueryInput allows vector queries and fusion/ordering/sampling, and refuses
// queries that reference stored points by id (they could use another tenant's
// vectors as the query).
func checkQueryInput(query interface{}) error {
	switch v := query.(type) {
	case nil, []interface{}:
		return nil
	case map[string]interface{}:
		if _, ok := v["indices"]; ok { // sparse vector
			return nil
		}
		for key, inner := range v {
			switch key {
			case "nearest":
				switch n := inner.(type) {
				case []interface{}:
				case map[string]interface{}:
					if _, sparse := n["indices"]; !sparse {
						return fmt.Errorf("nearest query must be a vector")
					}
				default:
					return fmt.Errorf("queries by point id are not supported by the tenant guard")
				}
			case "fusion", "rrf", "order_by", "sample", "mmr":
			default:
				return fmt.Errorf("query type %q is not supported by the tenant guard", key)
			}
		}
		return nil
	}
	return fmt.Errorf("queries by point id are not supported by the tenant guard")
}

// scopeUpsert stamps points with the tenant and refuses to overwrite points
// that belong to another tenant.
func (g *TenantGuard) scopeUpsert(ctx context.Context, collection string, req map[string]interface{}, tenant string, res *guardResult) error {
	var ids []interface{}

	stamp := func(payload interface{}) (map[string]interface{}, error) {
		p, ok := payload.(map[string]interface{})
		if payload == nil {
			p, ok = map[string]interface{}{}, true
		}
		if !ok {
			return nil, fmt.Errorf("malformed payload")
		}
		if existing, has := p[g.tenantKey]; has {
			if s, isStr := existing.(string); !isStr || s != tenant {
				res.contain("write tried to set %s=%v; stamped %q", g.tenantKey, existing, tenant)
			}
		}
		p[g.tenantKey] = tenant
		return p, nil
	}

	switch {
	case req["points"] != nil:
		points, ok := req["points"].([]interface{})
		if !ok {
			return fmt.Errorf("malformed points")
		}
		for _, item := range points {
			pt, ok := item.(map[string]interface{})
			if !ok {
				return fmt.Errorf("malformed point")
			}
			p, err := stamp(pt["payload"])
			if err != nil {
				return err
			}
			pt["payload"] = p
			ids = append(ids, pt["id"])
		}
	case req["batch"] != nil:
		batch, ok := req["batch"].(map[string]interface{})
		if !ok {
			return fmt.Errorf("malformed batch")
		}
		ids, ok = batch["ids"].([]interface{})
		if !ok {
			return fmt.Errorf("batch without ids")
		}
		payloads, _ := batch["payloads"].([]interface{})
		if payloads == nil {
			payloads = make([]interface{}, len(ids))
		}
		if len(payloads) != len(ids) {
			return fmt.Errorf("batch payloads and ids differ in length")
		}
		for i := range payloads {
			p, err := stamp(payloads[i])
			if err != nil {
				return err
			}
			payloads[i] = p
		}
		batch["payloads"] = payloads
	default:
		return fmt.Errorf("upsert without points")
	}

	if uf, ok := req["update_filter"]; ok && uf != nil {
		req["update_filter"] = g.scopeFilter(uf, tenant, res)
	}

	owners, err := g.pointOwners(ctx, collection, ids)
	if err != nil {
		return err
	}
	for id, owner := range owners {
		if owner != tenant {
			return fmt.Errorf("point %s belongs to another tenant; overwrite refused", id)
		}
	}
	return nil
}

// pointOwners looks up the tenant of points that already exist.
// Note: this is a check-then-write; a concurrent write between the lookup and
// the upsert is not covered.
func (g *TenantGuard) pointOwners(ctx context.Context, collection string, ids []interface{}) (map[string]string, error) {
	owners := map[string]string{}
	if len(ids) == 0 {
		return owners, nil
	}
	body, _ := json.Marshal(map[string]interface{}{"ids": ids, "with_payload": true, "with_vector": false})
	resp, respBody, err := g.forward(ctx, http.MethodPost, "/collections/"+url.PathEscape(collection)+"/points", "", body, nil)
	if err != nil {
		return nil, fmt.Errorf("vector store unreachable")
	}
	if resp.StatusCode == http.StatusNotFound {
		return owners, nil // collection does not exist yet
	}
	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("cannot verify point ownership (status %d)", resp.StatusCode)
	}
	doc, err := decodeObject(respBody)
	if err != nil {
		return nil, fmt.Errorf("cannot verify point ownership")
	}
	points, _ := doc["result"].([]interface{})
	for _, item := range points {
		pt, ok := item.(map[string]interface{})
		if !ok {
			continue
		}
		owner := ""
		if p, ok := pt["payload"].(map[string]interface{}); ok {
			owner, _ = p[g.tenantKey].(string)
		}
		owners[fmt.Sprint(pt["id"])] = owner
	}
	return owners, nil
}

// scopeSelectorWrite turns id- or filter-based writes into tenant-scoped filters.
func (g *TenantGuard) scopeSelectorWrite(name string, req map[string]interface{}, tenant string, res *guardResult) error {
	switch name {
	case "set-payload":
		if key, ok := req["key"].(string); ok && (key == g.tenantKey || strings.HasPrefix(key, g.tenantKey+".")) {
			return fmt.Errorf("the tenant tag cannot be modified")
		}
		if p, ok := req["payload"].(map[string]interface{}); ok {
			if v, has := p[g.tenantKey]; has {
				delete(p, g.tenantKey)
				res.contain("payload update tried to set %s=%v; ignored", g.tenantKey, v)
			}
		}
	case "overwrite-payload":
		p, ok := req["payload"].(map[string]interface{})
		if !ok {
			return fmt.Errorf("overwrite without payload")
		}
		if v, has := p[g.tenantKey]; has {
			if s, isStr := v.(string); !isStr || s != tenant {
				res.contain("payload overwrite tried to set %s=%v; stamped %q", g.tenantKey, v, tenant)
			}
		}
		p[g.tenantKey] = tenant
	case "delete-payload":
		keys, _ := req["keys"].([]interface{})
		for _, k := range keys {
			if s, ok := k.(string); ok && (s == g.tenantKey || strings.HasPrefix(s, g.tenantKey+".")) {
				return fmt.Errorf("the tenant tag cannot be deleted")
			}
		}
	}

	must := []interface{}{g.tenantCondition(tenant)}
	selected := false
	if pts, ok := req["points"]; ok && pts != nil {
		ids, ok := pts.([]interface{})
		if !ok {
			return fmt.Errorf("malformed points selector")
		}
		must = append(must, map[string]interface{}{"has_id": ids})
		selected = true
	}
	if f, ok := req["filter"]; ok && f != nil {
		if g.referencesForeignTenant(f, tenant, false) {
			res.contain("filter referenced another tenant; scoped to %q", tenant)
		}
		must = append(must, f)
		selected = true
	}
	if !selected {
		return fmt.Errorf("write without a points or filter selector")
	}
	delete(req, "points")
	req["filter"] = map[string]interface{}{"must": must}
	return nil
}

// --- response filtering ----------------------------------------------------

// payloadPref remembers what payload the client asked for, since the guard
// always requests the full payload to check ownership.
type payloadPref struct {
	value          interface{}
	set            bool
	defaultInclude bool
}

func forcePayload(req map[string]interface{}, defaultInclude bool) payloadPref {
	v, set := req["with_payload"]
	req["with_payload"] = true
	return payloadPref{value: v, set: set && v != nil, defaultInclude: defaultInclude}
}

func (p payloadPref) apply(point map[string]interface{}) {
	payload, _ := point["payload"].(map[string]interface{})
	if !p.set {
		if !p.defaultInclude {
			point["payload"] = nil
		}
		return
	}
	switch v := p.value.(type) {
	case bool:
		if !v {
			point["payload"] = nil
		}
	case []interface{}:
		point["payload"] = pickKeys(payload, v, true)
	case map[string]interface{}:
		if inc, ok := v["include"].([]interface{}); ok {
			point["payload"] = pickKeys(payload, inc, true)
		} else if exc, ok := v["exclude"].([]interface{}); ok {
			point["payload"] = pickKeys(payload, exc, false)
		}
	}
}

func pickKeys(payload map[string]interface{}, keys []interface{}, include bool) map[string]interface{} {
	if payload == nil {
		return nil
	}
	set := map[string]bool{}
	for _, k := range keys {
		if s, ok := k.(string); ok {
			set[s] = true
		}
	}
	out := map[string]interface{}{}
	for k, v := range payload {
		if set[k] == include {
			out[k] = v
		}
	}
	return out
}

func (g *TenantGuard) ownedBy(point map[string]interface{}, tenant string) bool {
	payload, ok := point["payload"].(map[string]interface{})
	if !ok {
		return false
	}
	owner, ok := payload[g.tenantKey].(string)
	return ok && owner == tenant
}

// keepOwned drops points that do not belong to the tenant and applies the
// client's payload preference to the rest.
func (g *TenantGuard) keepOwned(list interface{}, tenant string, pref payloadPref, res *guardResult) []interface{} {
	items, _ := list.([]interface{})
	kept := make([]interface{}, 0, len(items))
	dropped := 0
	for _, item := range items {
		pt, ok := item.(map[string]interface{})
		if !ok || !g.ownedBy(pt, tenant) {
			dropped++
			continue
		}
		pref.apply(pt)
		kept = append(kept, pt)
	}
	if dropped > 0 {
		res.contain("removed %d point(s) owned by other tenants from the response", dropped)
	}
	return kept
}

// filterResponse re-checks points returned by the store. found is false when a
// single-point lookup hit another tenant's point.
func (g *TenantGuard) filterResponse(op vectorOp, body []byte, tenant string, prefs []payloadPref, res *guardResult) ([]byte, bool, error) {
	switch op.name {
	case "count", "facet", "matrix":
		return body, true, nil
	}
	doc, err := decodeObject(body)
	if err != nil {
		return nil, false, err
	}
	pref := func(i int) payloadPref {
		if i < len(prefs) {
			return prefs[i]
		}
		return payloadPref{defaultInclude: true}
	}

	switch op.name {
	case "get-point":
		pt, ok := doc["result"].(map[string]interface{})
		if !ok || !g.ownedBy(pt, tenant) {
			if ok {
				res.contain("blocked read of a point owned by another tenant")
			}
			return nil, false, nil
		}
	case "retrieve", "search":
		doc["result"] = g.keepOwned(doc["result"], tenant, pref(0), res)
	case "search-batch":
		batches, _ := doc["result"].([]interface{})
		for i := range batches {
			batches[i] = g.keepOwned(batches[i], tenant, pref(i), res)
		}
	case "query", "scroll":
		if r, ok := doc["result"].(map[string]interface{}); ok {
			r["points"] = g.keepOwned(r["points"], tenant, pref(0), res)
		}
	case "query-batch":
		batches, _ := doc["result"].([]interface{})
		for i, b := range batches {
			if r, ok := b.(map[string]interface{}); ok {
				r["points"] = g.keepOwned(r["points"], tenant, pref(i), res)
			}
		}
	case "query-groups":
		if r, ok := doc["result"].(map[string]interface{}); ok {
			groups, _ := r["groups"].([]interface{})
			kept := make([]interface{}, 0, len(groups))
			for _, gr := range groups {
				m, ok := gr.(map[string]interface{})
				if !ok {
					continue
				}
				hits := g.keepOwned(m["hits"], tenant, pref(0), res)
				if len(hits) > 0 {
					m["hits"] = hits
					kept = append(kept, m)
				}
			}
			r["groups"] = kept
		}
	}

	out, err := json.Marshal(doc)
	return out, true, err
}

// --- plumbing --------------------------------------------------------------

func (g *TenantGuard) forward(ctx context.Context, method, path, rawQuery string, body []byte, in http.Header) (*http.Response, []byte, error) {
	u := *g.upstream
	u.Path = strings.TrimSuffix(g.upstream.Path, "/") + path
	u.RawPath = ""
	u.RawQuery = rawQuery

	var reader io.Reader
	if len(body) > 0 {
		reader = bytes.NewReader(body)
	}
	req, err := http.NewRequestWithContext(ctx, method, u.String(), reader)
	if err != nil {
		return nil, nil, err
	}
	if in != nil {
		if a := in.Get("Accept"); a != "" {
			req.Header.Set("Accept", a)
		}
	}
	if len(body) > 0 {
		req.Header.Set("Content-Type", "application/json")
	}
	// The agent never holds the store's API key; the sidecar injects it.
	if g.apiKey != "" {
		req.Header.Set("api-key", g.apiKey)
	}

	resp, err := g.client.Do(req)
	if err != nil {
		log.Printf("❌ Vector store request failed: %v", err)
		return nil, nil, err
	}
	defer resp.Body.Close()
	respBody, err := io.ReadAll(io.LimitReader(resp.Body, maxVectorBodyBytes))
	if err != nil {
		return nil, nil, err
	}
	return resp, respBody, nil
}

func decodeObject(body []byte) (map[string]interface{}, error) {
	if len(bytes.TrimSpace(body)) == 0 {
		return map[string]interface{}{}, nil
	}
	dec := json.NewDecoder(bytes.NewReader(body))
	dec.UseNumber() // keep 64-bit point ids exact
	var m map[string]interface{}
	if err := dec.Decode(&m); err != nil {
		return nil, err
	}
	if m == nil {
		return nil, fmt.Errorf("not a JSON object")
	}
	return m, nil
}

func writeUpstream(w http.ResponseWriter, resp *http.Response, body []byte) {
	if ct := resp.Header.Get("Content-Type"); ct != "" {
		w.Header().Set("Content-Type", ct)
	}
	w.WriteHeader(resp.StatusCode)
	w.Write(body)
}

// writeVectorError replies in Qdrant's error format so clients surface the reason.
func writeVectorError(w http.ResponseWriter, status int, reason string) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(map[string]interface{}{
		"status": map[string]string{"error": "DAC tenant guard: " + reason},
		"time":   0,
	})
}
