# Cross-tenant leaks in agent memory frameworks

*Tested September 2026 against Qdrant 1.19.1 with LangChain, LlamaIndex and Mem0.*

## Summary

We ran 17 scenarios across three popular agent-memory stacks. In each, one
customer's session (`alice`) shares a Qdrant collection with another
customer (`bob`), following the framework's own multi-tenant pattern.

| Stack | Scenarios where bob's data leaked or was changed (direct) | Through the DAC sidecar |
|---|---|---|
| LangChain (langchain-qdrant, SelfQueryRetriever) | 4 of 4 | 0 |
| LlamaIndex (QdrantVectorStore, VectorIndexAutoRetriever) | 2 of 3 | 0 |
| Mem0 (open-source `Memory` with Qdrant) | 6 of 7 | 1 (history, stored outside the vector store) |

Each stack also has a sanity check (alice reads her own data with the
documented tenant filter). All three passed, both directly and through the
sidecar, so the sidecar result is not caused by broken reads.

Most of these leaks follow from a design choice all three frameworks share:
tenant isolation is a filter that application code passes on every call. When
that filter is forgotten, or when the model gets to write it, tenants mix.
That is not a bug in any of them. Three findings go further and are worth
knowing even if your code is careful:

1. **LangChain's self-query retriever drops a pinned tenant filter whenever the
   model adds any filter.** `SelfQueryRetriever` builds its search arguments as
   `{**self.search_kwargs, **new_kwargs}` (`langchain_classic/retrievers/self_query/base.py`,
   line 292). A tenant filter pinned in `search_kwargs` is replaced by the
   model's filter, not combined with it. In our test, alice asked for "my
   finance notes", the model added an ordinary `topic = finance` filter, and
   bob's unreleased revenue forecast came back. No injection was involved.
2. **Mem0's `"*"` wildcard satisfies its "a user must be given" check.** In
   `search` and `get_all`, `filters={"user_id": "*"}` passes validation and
   matches every user. Mem0 requires a user, agent or run id so results stay
   scoped. The wildcard defeats that when the model can influence the value.
3. **Mem0's `get`, `delete` and `history` take a memory id and do not check
   who owns it.** Memory ids are UUIDs, so they cannot be guessed. But any id
   that reaches the model (an earlier tool result, a log line, a shared
   transcript) can be used to read or delete another user's memory.

One behaviour is worth copying: **LlamaIndex's auto-retriever combines
`extra_filters` with the model's filters using AND.** With the tenant pinned
there, an injected `tenant_id = bob` filter returned nothing.

## Results

| Stack | Scenario | Direct to Qdrant | Through DAC sidecar |
|---|---|---|---|
| LangChain | App passes the tenant filter on every search | OK | OK |
| LangChain | One code path builds a retriever without the tenant filter | LEAKED (3) | SAFE |
| LangChain | Self-query, tenant pinned; model adds an ordinary topic filter | LEAKED (1) | SAFE |
| LangChain | Self-query, tenant pinned; injected model asks for `tenant_id=bob` | LEAKED (3) | SAFE |
| LangChain | Memory tool writes with model-chosen metadata `tenant_id=bob` | DAMAGED | SAFE |
| LlamaIndex | App passes the tenant filter on every retrieval | OK | OK |
| LlamaIndex | One code path builds a retriever without the tenant filter | LEAKED (3) | SAFE |
| LlamaIndex | Auto-retriever, `tenant_id` listed as filterable; injected model asks for bob | LEAKED (3) | SAFE |
| LlamaIndex | Auto-retriever, tenant pinned via `extra_filters`; injected model asks for bob | SAFE | SAFE |
| Mem0 | App passes the session's `user_id` on every search | OK | OK |
| Mem0 | Memory tool lets the model choose `user_id`; injected model asks for bob | LEAKED (1) | SAFE |
| Mem0 | Model supplies `user_id="*"` to `search` | LEAKED (1) | SAFE |
| Mem0 | Model supplies `user_id="*"` to `get_all` | LEAKED (3) | SAFE |
| Mem0 | App merges model filters but sets `user_id` last; model adds `OR user_id=bob` | SAFE | SAFE |
| Mem0 | Model passes another user's memory id to `get()` | LEAKED (1) | SAFE |
| Mem0 | Model passes another user's memory id to `delete()` | DAMAGED | SAFE |
| Mem0 | Model passes another user's memory id to `history()` | LEAKED (1) | LEAKED (1) |

LEAKED (n) = n of bob's memories returned. DAMAGED = bob's data changed or
deleted. SAFE = stayed inside alice's tenant. OK = normal use works.

The one leak through the sidecar is expected. Mem0 keeps memory history in a
local SQLite database, which never passes through the vector store, so the
sidecar cannot see it.

## How the sidecar stops the rest

The DAC sidecar sits between the framework's Qdrant client and Qdrant. It
takes the tenant from the authenticated session, not from the request
contents. It:

- ANDs a tenant condition into every filter,
- stamps writes with the caller's tenant,
- turns id-based deletes into tenant-scoped filters,
- drops other tenants' points from every response.

The frameworks needed no code changes beyond pointing their Qdrant client at
the sidecar. Each framework stores the tenant under a different payload key
(`metadata.tenant_id`, `tenant_id`, `user_id`), which is set per sidecar with
`VECTOR_TENANT_KEY`. See [MEMORY_ISOLATION.md](MEMORY_ISOLATION.md).

## Method

- **Store.** Real Qdrant 1.19.1 (the `qdrant/qdrant` Docker image). Each
  scenario starts from a freshly seeded collection. Every result is checked
  against the store's contents, not just the framework's return value.
- **Versions.** langchain-classic 1.0.8, langchain-core 1.6.4,
  langchain-qdrant 1.1.0, langchain-community 0.4.2, llama-index-core 0.14.25,
  llama-index-vector-stores-qdrant 0.10.3, mem0ai 2.2.0, qdrant-client 1.19.1.
- **Scripted models.** Where a framework asks an LLM for a filter, the test
  returns fixed output: either what an injected model would write, or an
  ordinary filter. This measures what the stack does with a model's output. It
  does not measure how easily a given model is injected.
- **Embeddings and setup.** Embeddings are a deterministic hash of words.
  Mem0 runs with `infer=False`, so no LLM is called.
- **One workaround.** LangChain's built-in translator lookup fails to import
  with current langchain-community. The test passes `QdrantTranslator`
  directly, which is what that lookup returns for `QdrantVectorStore`.

Reproduce:

```bash
pip install -r tools/leaktest/requirements-stacks.txt
./scripts/stack_leaktest.sh
```

## Limitations

- Three frameworks and one vector store. pgvector, Pinecone, Chroma,
  LangGraph's store and Mem0's graph memory are not covered yet.
- The scenarios are code paths we consider realistic. They are not taken from
  specific production applications.
- We have not checked whether the LangChain and Mem0 behaviours above are
  already documented or reported. They should be raised with the maintainers
  before this report is published.
