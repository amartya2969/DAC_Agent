# Wildcard entity ids bypass Mem0's required scope, and id-based methods skip ownership checks

**File as:** GitHub private vulnerability report on `mem0ai/mem0` (or email support@mem0.ai).
Not a public issue.

## Summary

Two related hardening gaps in the open-source `Memory` class (mem0ai 2.2.0) weaken the
per-user scoping that multi-user apps rely on, especially when a model supplies arguments to
memory tools.

1. **`"*"` satisfies the required-scope check.** `search` and `get_all` require at least one
   of `user_id`, `agent_id` or `run_id` in `filters`. The documented wildcard,
   `{"user_id": "*"}`, passes that check and matches every user. The check is meant to keep
   calls scoped, and the wildcard makes it ineffective.
2. **`get`, `update`, `delete` and `history` take a memory id and do not check who owns
   it.** Any caller with a memory id can read, change or delete that memory, including its
   history, whichever user it belongs to. Ids are UUIDs, so they cannot be guessed, but they
   are returned by `add`, `search` and `get_all` and can reach the model through tool
   results, logs or shared transcripts.

## Reproduction

`repro_mem0.py` (attached) uses a local Qdrant, `infer=False` and a stub embedder, so no API
is called. Output:

```
1. get_all(filters={'user_id': '*'}): ["Bob's note: salary is $180k", "Alice's note: prefers email"]
   search(filters={'user_id': '*'}): ["Bob's note: salary is $180k", "Alice's note: prefers email"]
2. get(bob_id): Bob's note: salary is $180k
   history(bob_id): ["Bob's note: salary is $180k"]
   delete(bob_id) -> bob's memories now: []
```

## Impact

In agent integrations where the model fills in memory-tool arguments (the user id or a
memory id), a prompt injection or a confused model can read or delete other users' memories.
Apps that scope every call themselves are not affected by (1). They are affected by (2)
whenever a memory id can reach the model.

## Suggested fix

- Reject `"*"` for `user_id`, `agent_id` and `run_id` in the required-scope check, or
  accept it only with an explicit opt-in such as `allow_all=True`.
- Give `get`, `update`, `delete` and `history` optional scope arguments (for example
  `filters={"user_id": ...}`). When given, return not-found for memories outside that scope.
  Document that without them the methods are unscoped.

## Disclosure

We plan to publish a write-up of cross-tenant behaviour in agent-memory frameworks. We will
hold back the details of these issues for 90 days, or until a fix or documentation change is
released, whichever comes first. We are happy to adjust the timing.

Reporter: [name, contact]
