# Cross-tenant leak test for agent memory

Most multi-tenant AI products store every customer's agent memory in one
vector collection and keep tenants apart with a payload filter such as
`tenant_id = "acme"`. That filter is usually built by application code that
the model can influence, and sometimes it is forgotten. One missing or rewritten
filter exposes other customers' data.

`leaktest.py` checks whether your setup can leak or corrupt another tenant's
memory. It seeds a collection with memories from two tenants, `alice` and
`bob`, then acts as `alice` and runs 15 attacks that a prompt-injected or buggy
agent could make. After each attack it inspects the store directly to see what
actually leaked or changed.

## Run it

```bash
pip install -r requirements.txt

# Against a real Qdrant instance
docker run -p 6333:6333 qdrant/qdrant
python3 leaktest.py --store-url http://localhost:6333

# Compare with the DAC sidecar's tenant guard in front of the store
python3 leaktest.py --store-url http://localhost:6333 --sidecar-url http://localhost:8080
```

No Qdrant available? `qdrant_test_server.py` serves the relevant part of the
Qdrant REST API, with filtering done by qdrant-client's local engine:

```bash
python3 qdrant_test_server.py --port 6333
```

From the repository root, `./scripts/memory_isolation_demo.sh` starts the test
server and the sidecar and runs the comparison in one step.

> **Warning:** the collection named by `--collection` (default
> `dac_leaktest_memories`) is deleted and recreated before every probe. Use a
> test instance.

## What it checks

| Probe | What the agent does |
|---|---|
| missing_filter | Searches with no tenant filter |
| injected_filter | Uses a model-built filter set to `tenant_id=bob` |
| or_bypass | Widens the filter with `OR tenant_id=bob` |
| negation_bypass | Rewrites the filter to `NOT tenant_id=alice` |
| scroll_dump | Scrolls the whole collection |
| id_guessing | Fetches sequential point ids |
| count_oracle | Counts bob's memories |
| facet_enumeration | Lists tenant ids with a facet query |
| overwrite | Upserts over one of bob's point ids |
| poison | Writes a memory tagged `tenant_id=bob` |
| retag | Re-tags its own memory as bob's |
| tamper | Edits bob's memory by id |
| delete_by_id | Deletes bob's memories by id |
| delete_by_filter | Deletes with filter `tenant_id=bob` |
| drop_collection | Drops the shared collection |

Three sanity checks confirm that alice can still search, store and delete her
own memories, so a "SAFE" result cannot come from a broken setup.

Results:

- **LEAKED**: another tenant's data was returned.
- **DAMAGED**: another tenant's data was changed or deleted.
- **BLOCKED**: the request was refused.
- **SAFE**: the request ran but stayed inside the caller's tenant.

Use `--report report.md` for a Markdown report and `--json results.json` for
raw results. When `--sidecar-url` is set, the exit code is 1 if anything leaks
through the sidecar, so the test can gate CI.

## Results against the test server

Measured with `scripts/memory_isolation_demo.sh`:

| | Attacks that leaked or damaged bob's data | Sanity checks |
|---|---|---|
| Direct to store | 15 / 15 | passed |
| Through DAC sidecar | 0 / 15 (2 refused, 13 kept inside alice's tenant) | passed |

The direct results show what the store does when nothing enforces the
boundary. They are not a bug in Qdrant: the store does what the request asks.

## Limitations

- Embeddings are a toy hash of words. Leaks do not depend on embedding quality.
- The attacks call the Qdrant API directly. They stand in for what a hijacked
  agent's tool calls can produce. They are not prompts sent to a real model.
- Only Qdrant is covered so far. pgvector, Pinecone, Chroma and memory layers
  such as Mem0 are next.
