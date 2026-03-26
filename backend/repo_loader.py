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
    """
    Error handler for shutil.rmtree to overcome read-only file permissions on Windows.
    This changes the file permission to writable and retries the deletion.
    """
    os.chmod(path, stat.S_IWRITE)
    func(path)

def process_ipynb(filepath):
    """Extract code and markdown content from a Jupyter Notebook, ignoring metadata/outputs."""
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
            
            # 1. Parse .ipynb files specifically to avoid raw JSON clutter
            if file.endswith(".ipynb"):
                content = process_ipynb(filepath)
                if content.strip():
                    documents.append(f"File: {file}\n{content}")
            
            # 2. Try to read any other file as a normal text file
            else:
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        content = f.read()
                        if content.strip():
                            documents.append(f"File: {file}\n{content}")
                except UnicodeDecodeError:
                    # If it's a binary file (like .png, .exe, .zip), reading as text fails.
                    # We simply ignore it and move on.
                    pass

    # If no files were successfully read, clean up and raise an error
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

    # Clean up the cloned repo safely using the Windows permission error handler
    shutil.rmtree(repo_path, onerror=on_rm_error)

    return repo_id