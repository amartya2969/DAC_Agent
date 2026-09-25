# Demo video

`dac-agent-demo.mp4` is a 1:43 silent walkthrough with on-screen captions (1280×720, H.264). It covers:

- the shared-memory problem,
- a cross-customer read without DAC,
- the same request through the sidecar,
- a real run of `scripts/memory_isolation_demo.sh` against Qdrant 1.19.1,
- the framework results,
- how to deploy.

The framework scene shows totals only. It does not include the LangChain or Mem0 specifics
that are waiting for disclosure (see `docs/disclosures/`).

## Narration

Read this over the video, or record it as a voice-over. Times are when each scene starts.

| Time | Say |
|---|---|
| 0:00 | Many AI products run one shared agent for all of their customers. So what stops one customer's agent from reading another customer's memory? |
| 0:06 | Here are two customers, Acme and Globex. They share one agent and one memory store, a single Qdrant collection holding both companies' notes. |
| 0:15 | The only thing keeping them apart is a filter on each search that says "only Acme's data". That filter is built by code the model can steer, and sometimes a code path forgets it. |
| 0:23 | Watch what happens when Alice slips an instruction to the agent. The model writes a filter for Bob's account, and the store hands over all three of Globex's memories: an acquisition target, an unreleased forecast, a security incident. |
| 0:36 | It's not only reads. The same agent can overwrite Bob's memories, plant fake ones, delete them, or drop the whole collection. |
| 0:44 | Now add DAC. The sidecar sits next to the agent and takes the customer from the logged-in session, never from the model. Whatever filter the model writes, the sidecar adds "Alice only" before it reaches the store. Nothing from Globex comes back, and the attempt is logged. |
| 0:59 | This is a real run against Qdrant: fifteen attacks straight to the store, then the same fifteen through the sidecar. Every one leaks or does damage directly. None do through DAC, and Alice's normal use still works. |
| 1:15 | We ran the same test through LangChain, LlamaIndex and Mem0. Twelve of fourteen scenarios leaked directly; one did through DAC, and that one lives in a local file outside the vector store. |
| 1:25 | Adopting it is one change: point the agent's memory client at the sidecar. Everything else keeps working, and every request is audited. |
| 1:35 | DAC Agent: the isolation layer for multi-tenant AI. |

## Re-recording

The results table in the "real run" scene is embedded in `story.html`. To refresh it after a
new run, paste the new table from the demo script's output into the `TABLE` constant. Then:

```bash
pip install playwright imageio-ffmpeg
python3 demo/video/record.py   # set CHROMIUM_PATH if Playwright's browser isn't installed
```

The fonts are IBM Plex, under the SIL Open Font License (`fonts/OFL-LICENSE.txt`).
