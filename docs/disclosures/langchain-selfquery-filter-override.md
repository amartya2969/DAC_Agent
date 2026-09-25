# SelfQueryRetriever replaces a filter pinned in `search_kwargs` with the model's filter

**File as:** private GitHub security advisory on `langchain-ai/langchain`, then email
security@langchain.dev saying an advisory was filed in that repository.

## Summary

`SelfQueryRetriever` merges its search arguments as
`{**self.search_kwargs, **new_kwargs}` (`langchain_classic/retrievers/self_query/base.py`,
`_prepare_query`, line 292 in langchain-classic 1.0.8). When the model's structured query
contains any filter, the translated filter replaces the `filter` set in `search_kwargs`
instead of being combined with it.

Applications that pin an access-control filter in `search_kwargs` (for example the current
tenant or user) lose it whenever the model adds a filter of its own. This happens in ordinary
use as well as under prompt injection. In our test, a user asking "what are my finance notes?"
led the model to add `topic = finance`, and the retriever returned another tenant's
confidential document.

## Affected versions

Tested with langchain-classic 1.0.8, langchain-core 1.6.4, langchain-community 0.4.2
(`QdrantTranslator`), langchain-qdrant 1.1.0 and Qdrant 1.19.1. The merge is in the generic
retriever, so it should not depend on the vector store. We verified it with Qdrant only.

## Reproduction

`repro_langchain_selfquery.py` (attached) needs only a local Qdrant. It uses a scripted LLM
(`FakeListLLM`) that returns an ordinary topic filter. Output:

```
Pinned tenant: acme
  returned: 'Globex: Q4 revenue forecast $12.4M (confidential)' (tenant globex)
REPRODUCED: pinned tenant filter was replaced
```

Side note: `SelfQueryRetriever.from_llm` without an explicit `structured_query_translator`
fails with `ImportError: cannot import name 'DatabricksVectorSearch' from
'langchain_community.vectorstores'` in this combination of versions. The repro passes
`QdrantTranslator(metadata_key="metadata")`, which is what the built-in lookup returns for
`QdrantVectorStore`.

## Impact

Multi-tenant RAG and agent-memory apps that rely on a pinned `search_kwargs` filter for
isolation can return other tenants' or users' documents. That filter is the natural place to
pin a fixed restriction. Anyone who can influence the query, including other users and
content read by the model, can trigger this, and it also happens without any adversary. We
are not aware of documentation that warns about the override. Please correct us if it exists.

## Suggested fix

- Combine the pinned filter with the generated one (AND) instead of replacing it. For
  translators that produce native filters, this could be a translator method that merges two
  filters, or a separate `fixed_filter` field applied after translation.
- Until then, document that a `filter` in `search_kwargs` is dropped whenever the model
  emits a filter, and warn against using it for access control.

## Disclosure

We plan to publish a write-up of cross-tenant behaviour in agent-memory frameworks. We will
hold back the details of this issue for 90 days, or until a fix or documentation change is
released, whichever comes first. We are happy to adjust the timing.

Reporter: [name, contact]
