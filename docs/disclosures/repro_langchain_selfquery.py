"""SelfQueryRetriever drops a filter pinned in search_kwargs when the model emits any filter.

Needs a local Qdrant (docker run -p 6333:6333 qdrant/qdrant) and:
pip install langchain-classic==1.0.8 langchain-community==0.4.2 langchain-qdrant==1.1.0 lark
"""
import json

from langchain_classic.chains.query_constructor.schema import AttributeInfo
from langchain_classic.retrievers.self_query.base import SelfQueryRetriever
from langchain_community.query_constructors.qdrant import QdrantTranslator
from langchain_core.embeddings import FakeEmbeddings
from langchain_core.language_models.fake import FakeListLLM
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient, models

client = QdrantClient(url="http://localhost:6333")
name = "selfquery_repro"
if client.collection_exists(name):
    client.delete_collection(name)
client.create_collection(name, vectors_config=models.VectorParams(size=16, distance=models.Distance.COSINE))
store = QdrantVectorStore(client=client, collection_name=name, embedding=FakeEmbeddings(size=16))
store.add_texts(
    ["Acme: Contoso renewal at $40k", "Globex: Q4 revenue forecast $12.4M (confidential)"],
    metadatas=[{"tenant_id": "acme", "topic": "sales"}, {"tenant_id": "globex", "topic": "finance"}],
)

# The application pins the current tenant, as recommended for fixed filters.
tenant_filter = models.Filter(must=[models.FieldCondition(
    key="metadata.tenant_id", match=models.MatchValue(value="acme"))])

# The model adds an ordinary filter for "what are my finance notes?". No injection.
llm = FakeListLLM(responses=[json.dumps({"query": "notes", "filter": 'eq("topic", "finance")'})])
retriever = SelfQueryRetriever.from_llm(
    llm, store, "Account notes",
    [AttributeInfo(name="topic", description="Note topic", type="string")],
    search_kwargs={"filter": tenant_filter, "k": 5},
    # Explicit because the built-in translator lookup fails to import with langchain-community 0.4.2;
    # this is the translator that lookup returns for QdrantVectorStore.
    structured_query_translator=QdrantTranslator(metadata_key="metadata"),
)

docs = retriever.invoke("what are my finance notes?")
print("Pinned tenant: acme")
for d in docs:
    print(f"  returned: {d.page_content!r} (tenant {d.metadata['tenant_id']})")
leaked = [d for d in docs if d.metadata["tenant_id"] != "acme"]
print("REPRODUCED: pinned tenant filter was replaced" if leaked else "not reproduced")
client.delete_collection(name)
