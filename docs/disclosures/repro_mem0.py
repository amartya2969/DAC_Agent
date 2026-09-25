"""Mem0: "*" satisfies the required user_id check; id-based methods do not check ownership.

Needs a local Qdrant (docker run -p 6333:6333 qdrant/qdrant) and: pip install mem0ai==2.2.0
No LLM or embedding API is called (infer=False, stub embedder).
"""
import hashlib
import os
import tempfile

os.environ.setdefault("OPENAI_API_KEY", "sk-not-used")
os.environ["MEM0_TELEMETRY"] = "False"
from mem0 import Memory  # noqa: E402


class StubEmbedder:
    config = type("C", (), {"embedding_dims": 16})()

    def embed(self, text, memory_action=None):
        h = hashlib.sha256(text.encode()).digest()
        return [b / 255 for b in h[:16]]


m = Memory.from_config({
    "vector_store": {"provider": "qdrant", "config": {
        "host": "localhost", "port": 6333, "collection_name": "mem0_repro", "embedding_model_dims": 16}},
    "embedder": {"provider": "openai", "config": {"embedding_dims": 16}},
    "llm": {"provider": "openai", "config": {}},
    "history_db_path": os.path.join(tempfile.mkdtemp(), "history.db"),
})
m.embedding_model = StubEmbedder()
m.vector_store.delete_col()
m.vector_store.create_col(16, False)

m.add("Alice's note: prefers email", user_id="alice", infer=False)
bob_id = m.add("Bob's note: salary is $180k", user_id="bob", infer=False)["results"][0]["id"]

# 1. The wildcard passes the "user_id, agent_id or run_id required" check and matches every user.
hits = m.get_all(filters={"user_id": "*"})["results"]
print("1. get_all(filters={'user_id': '*'}):", [h["memory"] for h in hits])
hits = m.search("note", filters={"user_id": "*"}, threshold=0.0)["results"]
print("   search(filters={'user_id': '*'}):", [h["memory"] for h in hits])

# 2. Id-based methods take no user and do not check ownership.
print("2. get(bob_id):", m.get(bob_id)["memory"])
print("   history(bob_id):", [h.get("new_memory") for h in m.history(bob_id)])
m.delete(bob_id)
print("   delete(bob_id) -> bob's memories now:", [h["memory"] for h in m.get_all(filters={"user_id": "bob"})["results"]])
m.vector_store.delete_col()
