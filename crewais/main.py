from fastapi import FastAPI
from pydantic import BaseModel
from crewais.crew import run_crewai

app = FastAPI()

class ChatRequest(BaseModel):
    message: str

@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.post("/chat")
async def chat(data: ChatRequest):
    response = run_crewai(data.message)
    return {"response": response}


