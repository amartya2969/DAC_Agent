package main

import (
	"bytes"
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

// fakeStore records requests that reach the vector store and replies with
// canned responses keyed by "METHOD path".
type fakeStore struct {
	t         *testing.T
	requests  []recorded
	responses map[string]string
}

type recorded struct {
	method, path string
	body         map[string]interface{}
	headers      http.Header
}

func (f *fakeStore) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	raw, _ := io.ReadAll(r.Body)
	var body map[string]interface{}
	if len(raw) > 0 {
		if err := json.Unmarshal(raw, &body); err != nil {
			f.t.Fatalf("store got invalid JSON: %v", err)
		}
	}
	f.requests = append(f.requests, recorded{r.Method, r.URL.Path, body, r.Header.Clone()})
	resp, ok := f.responses[r.Method+" "+r.URL.Path]
	if !ok {
		resp = `{"result":true,"status":"ok","time":0}`
	}
	w.Header().Set("Content-Type", "application/json")
	w.Write([]byte(resp))
}

func (f *fakeStore) last() recorded {
	if len(f.requests) == 0 {
		f.t.Fatal("no request reached the store")
	}
	return f.requests[len(f.requests)-1]
}

type harness struct {
	store *fakeStore
	guard *TenantGuard
	audit *bytes.Buffer
}

func newHarness(t *testing.T, responses map[string]string) *harness {
	t.Helper()
	store := &fakeStore{t: t, responses: responses}
	srv := httptest.NewServer(store)
	t.Cleanup(srv.Close)

	guard, err := NewTenantGuard(srv.URL, "tenant_id", "store-secret")
	if err != nil {
		t.Fatal(err)
	}
	buf := &bytes.Buffer{}
	prev := auditOut
	auditOut = buf
	t.Cleanup(func() { auditOut = prev })
	return &harness{store: store, guard: guard, audit: buf}
}

func (h *harness) do(method, path, tenant, body string) *httptest.ResponseRecorder {
	req := httptest.NewRequest(method, "/vector"+path, strings.NewReader(body))
	if tenant != "" {
		req.Header.Set(tenantHeader, tenant)
	}
	req.Header.Set("api-key", "agent-supplied-key")
	rec := httptest.NewRecorder()
	h.guard.ServeHTTP(rec, req)
	return rec
}

func (h *harness) auditEvents(t *testing.T) []AuditLog {
	var events []AuditLog
	dec := json.NewDecoder(bytes.NewReader(h.audit.Bytes()))
	for dec.More() {
		var e AuditLog
		if err := dec.Decode(&e); err != nil {
			t.Fatal(err)
		}
		events = append(events, e)
	}
	return events
}

func mustJSON(t *testing.T, s string) map[string]interface{} {
	t.Helper()
	var m map[string]interface{}
	if err := json.Unmarshal([]byte(s), &m); err != nil {
		t.Fatal(err)
	}
	return m
}

func canon(v interface{}) string {
	b, _ := json.Marshal(v)
	return string(b)
}

const tenantAlice = `{"key":"tenant_id","match":{"value":"alice"}}`

func TestClassifyVectorOp(t *testing.T) {
	cases := []struct {
		method, path string
		kind         opKind
		name         string
	}{
		{"GET", "/", opPassthrough, "version"},
		{"GET", "/collections", opPassthrough, "list-collections"},
		{"PUT", "/collections/mem", opPassthrough, "create-collection"},
		{"DELETE", "/collections/mem", opDeny, "denied"},
		{"PATCH", "/collections/mem", opDeny, "denied"},
		{"PUT", "/collections/mem/points", opUpsert, "upsert"},
		{"POST", "/collections/mem/points", opRetrieve, "retrieve"},
		{"GET", "/collections/mem/points/42", opGetPoint, "get-point"},
		{"POST", "/collections/mem/points/query", opFilteredRead, "query"},
		{"POST", "/collections/mem/points/query/groups", opFilteredRead, "query-groups"},
		{"POST", "/collections/mem/points/scroll", opFilteredRead, "scroll"},
		{"POST", "/collections/mem/points/search/matrix/pairs", opFilteredRead, "matrix"},
		{"POST", "/collections/mem/facet", opFilteredRead, "facet"},
		{"POST", "/collections/mem/points/delete", opSelectorWrite, "delete"},
		{"PUT", "/collections/mem/points/payload", opSelectorWrite, "overwrite-payload"},
		{"POST", "/collections/mem/points/payload/clear", opDeny, "denied"},
		{"POST", "/collections/mem/points/recommend", opDeny, "denied"},
		{"PUT", "/collections/mem/points/vectors", opDeny, "denied"},
		{"POST", "/collections/mem/points/batch", opDeny, "denied"},
		{"POST", "/collections/mem/snapshots", opDeny, "denied"},
		{"POST", "/aliases", opDeny, "denied"},
		{"GET", "/cluster", opDeny, "denied"},
	}
	for _, c := range cases {
		op := classifyVectorOp(c.method, c.path)
		if op.kind != c.kind || op.name != c.name {
			t.Errorf("%s %s: got (%d, %s), want (%d, %s)", c.method, c.path, op.kind, op.name, c.kind, c.name)
		}
	}
}

func TestMissingTenantIsRefused(t *testing.T) {
	h := newHarness(t, nil)
	rec := h.do("POST", "/collections/mem/points/query", "", `{"query":{"nearest":[0.1,0.2]}}`)
	if rec.Code != http.StatusForbidden {
		t.Fatalf("status %d, want 403", rec.Code)
	}
	if len(h.store.requests) != 0 {
		t.Fatal("request reached the store without a tenant")
	}
	// The version check stays open so clients can connect.
	if rec := h.do("GET", "/", "", ""); rec.Code != http.StatusOK {
		t.Fatalf("version check status %d", rec.Code)
	}
}

func TestQueryFilterIsScopedToTenant(t *testing.T) {
	h := newHarness(t, map[string]string{
		"POST /collections/mem/points/query": `{"result":{"points":[]},"status":"ok"}`,
	})
	injected := `{"must":[{"key":"tenant_id","match":{"value":"bob"}}]}`
	rec := h.do("POST", "/collections/mem/points/query", "alice",
		`{"query":{"nearest":[0.1,0.2]},"filter":`+injected+`,"limit":5}`)
	if rec.Code != http.StatusOK {
		t.Fatalf("status %d: %s", rec.Code, rec.Body)
	}

	got := h.store.last().body["filter"]
	want := mustJSON(t, `{"must":[`+tenantAlice+`,`+injected+`]}`)
	if canon(got) != canon(want) {
		t.Fatalf("filter sent to store:\n got %s\nwant %s", canon(got), canon(want))
	}
	events := h.auditEvents(t)
	if len(events) != 1 || events[0].Outcome != "CONTAINED" {
		t.Fatalf("expected one CONTAINED audit event, got %+v", events)
	}
}

func TestMissingFilterGetsTenantFilter(t *testing.T) {
	h := newHarness(t, map[string]string{
		"POST /collections/mem/points/scroll": `{"result":{"points":[],"next_page_offset":null},"status":"ok"}`,
	})
	h.do("POST", "/collections/mem/points/scroll", "alice", `{"limit":100}`)
	if canon(h.store.last().body["filter"]) != canon(mustJSON(t, `{"must":[`+tenantAlice+`]}`)) {
		t.Fatalf("scroll filter: %s", canon(h.store.last().body["filter"]))
	}
	if h.auditEvents(t)[0].Outcome != "ALLOWED" {
		t.Fatal("an unfiltered scroll is not a cross-tenant attempt by itself")
	}
}

func TestOrAndNegationBypassesAreDetected(t *testing.T) {
	g, _ := NewTenantGuard("http://store", "tenant_id", "")
	cases := map[string]bool{
		`{"should":[{"key":"tenant_id","match":{"value":"alice"}},{"key":"tenant_id","match":{"value":"bob"}}]}`: true,
		`{"must_not":[{"key":"tenant_id","match":{"value":"alice"}}]}`:                                           true,
		`{"must":[{"key":"tenant_id","match":{"any":["alice","bob"]}}]}`:                                         true,
		`{"must":[{"key":"tenant_id","match":{"except":["alice"]}}]}`:                                            true,
		`{"must":[{"must":[{"key":"tenant_id","match":{"value":"bob"}}]}]}`:                                      true,
		`{"must":[{"key":"tenant_id","match":{"value":"alice"}}]}`:                                               false,
		`{"must":[{"key":"topic","match":{"value":"pricing"}}]}`:                                                 false,
	}
	for filter, want := range cases {
		var f interface{}
		json.Unmarshal([]byte(filter), &f)
		if got := g.referencesForeignTenant(f, "alice", false); got != want {
			t.Errorf("%s: got %v, want %v", filter, got, want)
		}
	}
}

func TestForeignPointsAreDroppedFromResponses(t *testing.T) {
	h := newHarness(t, map[string]string{
		"POST /collections/mem/points/query": `{"result":{"points":[
			{"id":1,"score":0.9,"payload":{"tenant_id":"alice","text":"mine"}},
			{"id":2,"score":0.8,"payload":{"tenant_id":"bob","text":"secret"}},
			{"id":3,"score":0.7,"payload":{"text":"untagged"}}]},"status":"ok"}`,
	})
	rec := h.do("POST", "/collections/mem/points/query", "alice", `{"query":{"nearest":[0.1]},"with_payload":true}`)
	body := rec.Body.String()
	if strings.Contains(body, "secret") || strings.Contains(body, "untagged") {
		t.Fatalf("foreign or untagged point leaked: %s", body)
	}
	if !strings.Contains(body, "mine") {
		t.Fatalf("own point missing: %s", body)
	}
	if h.store.last().body["with_payload"] != true {
		t.Fatal("guard must request payloads to check ownership")
	}
	if h.auditEvents(t)[0].Outcome != "CONTAINED" {
		t.Fatal("dropping foreign points should be audited")
	}
}

func TestPayloadPreferenceIsRestored(t *testing.T) {
	h := newHarness(t, map[string]string{
		"POST /collections/mem/points/query": `{"result":{"points":[
			{"id":1,"score":0.9,"payload":{"tenant_id":"alice","text":"mine","topic":"x"}}]},"status":"ok"}`,
	})
	rec := h.do("POST", "/collections/mem/points/query", "alice", `{"query":{"nearest":[0.1]}}`)
	if strings.Contains(rec.Body.String(), "mine") {
		t.Fatalf("payload returned although the client did not ask for it: %s", rec.Body)
	}
	rec = h.do("POST", "/collections/mem/points/query", "alice", `{"query":{"nearest":[0.1]},"with_payload":["text"]}`)
	if !strings.Contains(rec.Body.String(), "mine") || strings.Contains(rec.Body.String(), "topic") {
		t.Fatalf("payload selector not applied: %s", rec.Body)
	}
}

func TestGetForeignPointLooksMissing(t *testing.T) {
	h := newHarness(t, map[string]string{
		"GET /collections/mem/points/7": `{"result":{"id":7,"payload":{"tenant_id":"bob","text":"secret"}},"status":"ok"}`,
	})
	rec := h.do("GET", "/collections/mem/points/7", "alice", "")
	if rec.Code != http.StatusNotFound || strings.Contains(rec.Body.String(), "secret") {
		t.Fatalf("status %d body %s", rec.Code, rec.Body)
	}
}

func TestUpsertStampsTenant(t *testing.T) {
	h := newHarness(t, map[string]string{
		"POST /collections/mem/points": `{"result":[],"status":"ok"}`,
	})
	rec := h.do("PUT", "/collections/mem/points", "alice",
		`{"points":[{"id":10,"vector":[0.1],"payload":{"text":"note","tenant_id":"bob"}},{"id":11,"vector":[0.2]}]}`)
	if rec.Code != http.StatusOK {
		t.Fatalf("status %d: %s", rec.Code, rec.Body)
	}
	up := h.store.last()
	if up.method != "PUT" {
		t.Fatalf("last store call %s %s", up.method, up.path)
	}
	for _, p := range up.body["points"].([]interface{}) {
		payload := p.(map[string]interface{})["payload"].(map[string]interface{})
		if payload["tenant_id"] != "alice" {
			t.Fatalf("point not stamped: %v", payload)
		}
	}
	if h.auditEvents(t)[0].Outcome != "CONTAINED" {
		t.Fatal("writing into another tenant should be audited")
	}
	if got := up.headers.Get("api-key"); got != "store-secret" {
		t.Fatalf("store api-key %q; the agent's key must be replaced", got)
	}
}

func TestUpsertBatchStampsTenant(t *testing.T) {
	h := newHarness(t, map[string]string{
		"POST /collections/mem/points": `{"result":[],"status":"ok"}`,
	})
	h.do("PUT", "/collections/mem/points", "alice", `{"batch":{"ids":[1,2],"vectors":[[0.1],[0.2]]}}`)
	payloads := h.store.last().body["batch"].(map[string]interface{})["payloads"].([]interface{})
	for _, p := range payloads {
		if p.(map[string]interface{})["tenant_id"] != "alice" {
			t.Fatalf("batch payload not stamped: %v", payloads)
		}
	}
}

func TestUpsertCannotOverwriteAnotherTenantsPoint(t *testing.T) {
	h := newHarness(t, map[string]string{
		"POST /collections/mem/points": `{"result":[{"id":5,"payload":{"tenant_id":"bob"}}],"status":"ok"}`,
	})
	rec := h.do("PUT", "/collections/mem/points", "alice", `{"points":[{"id":5,"vector":[0.1],"payload":{"text":"x"}}]}`)
	if rec.Code != http.StatusForbidden {
		t.Fatalf("status %d, want 403", rec.Code)
	}
	for _, r := range h.store.requests {
		if r.method == "PUT" {
			t.Fatal("overwrite reached the store")
		}
	}
}

func TestDeleteByIdsBecomesScopedFilter(t *testing.T) {
	h := newHarness(t, nil)
	h.do("POST", "/collections/mem/points/delete", "alice", `{"points":[5,6]}`)
	body := h.store.last().body
	if _, ok := body["points"]; ok {
		t.Fatal("id selector must be replaced by a filter")
	}
	want := mustJSON(t, `{"must":[`+tenantAlice+`,{"has_id":[5,6]}]}`)
	if canon(body["filter"]) != canon(want) {
		t.Fatalf("delete filter %s", canon(body["filter"]))
	}
}

func TestPayloadWritesCannotRetagPoints(t *testing.T) {
	h := newHarness(t, nil)
	h.do("POST", "/collections/mem/points/payload", "alice", `{"payload":{"tenant_id":"bob","text":"x"},"points":[1]}`)
	payload := h.store.last().body["payload"].(map[string]interface{})
	if _, ok := payload["tenant_id"]; ok {
		t.Fatalf("set payload kept the tenant tag: %v", payload)
	}

	rec := h.do("POST", "/collections/mem/points/payload/delete", "alice", `{"keys":["tenant_id"],"points":[1]}`)
	if rec.Code != http.StatusForbidden {
		t.Fatalf("deleting the tenant tag: status %d", rec.Code)
	}
	rec = h.do("POST", "/collections/mem/points/payload", "alice", `{"payload":{"v":"bob"},"key":"tenant_id","points":[1]}`)
	if rec.Code != http.StatusForbidden {
		t.Fatalf("setting a nested key under the tenant tag: status %d", rec.Code)
	}

	h.do("PUT", "/collections/mem/points/payload", "alice", `{"payload":{"text":"y"},"points":[1]}`)
	if h.store.last().body["payload"].(map[string]interface{})["tenant_id"] != "alice" {
		t.Fatal("overwrite must keep the tenant tag")
	}
}

func TestDeniedOperationsNeverReachStore(t *testing.T) {
	h := newHarness(t, nil)
	denied := []struct{ method, path, body string }{
		{"DELETE", "/collections/mem", ""},
		{"POST", "/collections/mem/points/payload/clear", `{"points":[1]}`},
		{"POST", "/collections/mem/points/recommend", `{"positive":[1]}`},
		{"POST", "/collections/mem/points/query", `{"query":"8b1e6c4e-0000-0000-0000-000000000000"}`},
		{"POST", "/collections/mem/points/query", `{"query":{"nearest":7}}`},
		{"POST", "/collections/mem/points/query", `{"query":{"recommend":{"positive":[1]}}}`},
		{"POST", "/collections/mem/points/query", `{"query":[0.1],"lookup_from":{"collection":"other"}}`},
		{"POST", "/collections/mem/points/delete", `{}`},
	}
	for _, d := range denied {
		if rec := h.do(d.method, d.path, "alice", d.body); rec.Code != http.StatusForbidden {
			t.Errorf("%s %s %s: status %d, want 403", d.method, d.path, d.body, rec.Code)
		}
	}
	if len(h.store.requests) != 0 {
		t.Fatalf("%d denied request(s) reached the store", len(h.store.requests))
	}
	for _, e := range h.auditEvents(t) {
		if e.Outcome != "BLOCKED" {
			t.Fatalf("denied request audited as %s", e.Outcome)
		}
	}
}

func TestPrefetchFiltersAreScoped(t *testing.T) {
	h := newHarness(t, map[string]string{
		"POST /collections/mem/points/query": `{"result":{"points":[]},"status":"ok"}`,
	})
	h.do("POST", "/collections/mem/points/query", "alice",
		`{"prefetch":[{"query":[0.1],"limit":20},{"query":{"indices":[1],"values":[0.5]},"limit":20}],"query":{"fusion":"rrf"}}`)
	for _, p := range h.store.last().body["prefetch"].([]interface{}) {
		f := p.(map[string]interface{})["filter"]
		if canon(f) != canon(mustJSON(t, `{"must":[`+tenantAlice+`]}`)) {
			t.Fatalf("prefetch filter %s", canon(f))
		}
	}
}

func TestLargePointIdsSurvive(t *testing.T) {
	req, err := decodeObject([]byte(`{"points":[18446744073709551615]}`))
	if err != nil {
		t.Fatal(err)
	}
	g, _ := NewTenantGuard("http://store", "tenant_id", "")
	if err := g.scopeSelectorWrite("delete", req, "alice", &guardResult{}); err != nil {
		t.Fatal(err)
	}
	out, _ := json.Marshal(req)
	if !strings.Contains(string(out), "18446744073709551615") {
		t.Fatalf("point id lost precision: %s", out)
	}
}
