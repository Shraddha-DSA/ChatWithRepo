from fastapi import FastAPI
from pydantic import BaseModel
from repo_loader import load_repo
from rag_pipeline import chat_with_repo
from database import save_chat, get_chat_history, save_repo

app = FastAPI()
class RepoRequest(BaseModel):
    repo_url: str
class ChatRequest(BaseModel):
    repo_id: str
    question: str
@app.post("/load_repo")
def load_repository(req:  RepoRequest):
    repo_id = load_repo(req.repo_url)
    return {"repo_id":repo_id}
@app.post("/chat")
def chat(req: ChatRequest):
    try:
        answer = chat_with_repo(req.repo_id, req.question)
        save_chat(req.repo_id, req.question, answer)
        return {"answer": answer}
    except Exception as e:
        return {"error": str(e)}
@app.get("/history/{repo_id}")
def history(repo_id:str):
    return get_chat_history(repo_id)