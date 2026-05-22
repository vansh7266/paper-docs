import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DATABASE_NAME = "research_papers"
COLLECTION_NAME = "papers"

KEYWORDS = [
    "ai",
    "machine learning",
    "deep learning",
    "llm",
    "transformer",
    "nlp",
    "computer vision",
    "language model",
    "automation",
    "RAG",
    "VLM",
    "LangChain",
    "LangGraph",
    "agent"
]