import os
import uuid
import shutil
import stat
import json
from git import Repo
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
import chromadb

model = SentenceTransformer("all-MiniLM-L6-v2")
chroma_client = chromadb.PersistentClient(path="chroma_db")

def on_rm_error(func, path, exc_info):
    
    os.chmod(path, stat.S_IWRITE)
    func(path)

def process_ipynb(filepath):
    
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            notebook = json.load(f)
        
        content = []
        for cell in notebook.get("cells", []):
            if cell.get("cell_type") in ["code", "markdown"]:
                source = cell.get("source", [])
                if isinstance(source, list):
                    content.append("".join(source))
                elif isinstance(source, str):
                    content.append(source)
        return "\n".join(content)
    except Exception as e:
        print(f"Error parsing notebook {filepath}: {e}")
        return ""

def load_repo(repo_url):
    repo_id = str(uuid.uuid4())
    repo_path = f"data/repos/{repo_id}"

    os.makedirs(os.path.dirname(repo_path), exist_ok=True)
    Repo.clone_from(repo_url, repo_path)

    documents = []

    for root, _, files in os.walk(repo_path):
        if ".git" in root:
            continue
            
        for file in files:
            filepath = os.path.join(root, file)
            
            
            if file.endswith(".ipynb"):
                content = process_ipynb(filepath)
                if content.strip():
                    documents.append(f"File: {file}\n{content}")
            
            
            else:
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        content = f.read()
                        if content.strip():
                            documents.append(f"File: {file}\n{content}")
                except UnicodeDecodeError:
                    
                    pass

    
    if not documents:
        shutil.rmtree(repo_path, onerror=on_rm_error)
        raise ValueError("No valid readable text or code files found in the repository.")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50
    )

    chunks = splitter.split_text("\n".join(documents))
    embeddings = model.encode(chunks).tolist()

    collection = chroma_client.get_or_create_collection(name=repo_id)

    ids = [str(i) for i in range(len(chunks))]
    collection.add(
        documents=chunks,
        embeddings=embeddings,
        ids=ids
    )

    
    shutil.rmtree(repo_path, onerror=on_rm_error)

    return repo_id