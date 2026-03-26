import chromadb
from sentence_transformers import SentenceTransformer
from groq import Groq
import os
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

embed_model = SentenceTransformer("all-MiniLM-L6-v2")

chroma_client = chromadb.PersistentClient(path="chroma_db")

def chat_with_repo(repo_id, question):
    try:
        
        collection = chroma_client.get_collection(name=repo_id)
    except ValueError:
        return "Repository context not found. Please load the repository again."

    query_embedding = embed_model.encode(question).tolist()

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=3
    )

    print("Results:", results)

    docs = results.get("documents", [])

    if not docs or not docs[0]:
        return "No relevant context found in repository."

    context = "\n".join(docs[0])

    prompt = f"""
You are a code assistant.
Use ONLY the repository context below.

Context:
{context}

Question:
{question}
"""

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}]
    )

    return response.choices[0].message.content