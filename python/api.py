from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

import agent
from agent import answer

agent.DEBUG = False

app = FastAPI()

class ChatRequest(BaseModel):
    message: str
    squad: Optional[list[int]] = None

@app.post("/chat")
def chat(req: ChatRequest):
    message = req.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message is empty.")
    if len(message) > 500:
        raise HTTPException(status_code=400, detail="Message too long (max 500 characters).")

    try:
        return {"answer": answer(message, req.squad)}
    except Exception as e:
        print("chat error:", repr(e))
        raise HTTPException(status_code=500, detail="Something went wrong, please try again.")