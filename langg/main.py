from fastapi import FastAPI
from pydantic import BaseModel
from langg.agents import run_langgraph

app = FastAPI()

class ChatRequest(BaseModel):
    message: str

@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.post("/chat")
async def chat(data: ChatRequest):
    response = run_langgraph(data.message)
    return {"response": response}


