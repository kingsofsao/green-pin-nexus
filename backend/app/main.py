from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

from .database import init_db
from .routes.api import router


# Load environment variables from backend/.env
load_dotenv()


app = FastAPI(
    title="GREEN PIN NEXUS API",
    version="1.0.0"
)


# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event():
    # Initialize DB and generate data if needed
    init_db()


# Include routers
app.include_router(router, prefix="/api")


@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "environment": os.getenv("ENVIRONMENT", "simulation")
    }