# Disclosure drafts (not sent)

| Project | Draft | Repro | Where to file |
|---|---|---|---|
| LangChain | langchain-selfquery-filter-override.md | repro_langchain_selfquery.py | Private security advisory on github.com/langchain-ai/langchain (Security tab), then email security@langchain.dev naming the repo. Bounties via huntr; library code only. |
| Mem0 | mem0-wildcard-and-id-ownership.md | repro_mem0.py | Private vulnerability report on github.com/mem0ai/mem0 (Security tab), or support@mem0.ai. They acknowledge within 72 hours. No public issues. |

Both repros ran against Qdrant 1.19.1 on 2026-09-25 and reproduce as written.

Before sending:
1. Fill in the reporter line in both drafts.
2. Decide whether the 90-day window suits you.
3. These drafts and `docs/STACK_LEAK_REPORT.md` are in the repository. Keep the repository
   private until the maintainers have responded.
