from fastapi import FastAPI
from db import init_db, close_db
from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

@asynccontextmanager
async def lifespan(app:FastAPI):
    await init_db()
    yield
    await close_db()

app=FastAPI(title="Research Agent", description="A research agent that can help you with your research tasks.", version="0.0.1",lifespan=lifespan)


@app.get("/health")
async def health_check():
    return {"status":"Positive", "message":"Research Agent is up and running!"}