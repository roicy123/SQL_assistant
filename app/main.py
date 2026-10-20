from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.assistant import answer

app = FastAPI(title="SQL Assistant")


class AskRequest(BaseModel):
    question: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ask")
def ask(req: AskRequest):
    try:
        return answer(req.question)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"LLM service error: {type(e).__name__}")