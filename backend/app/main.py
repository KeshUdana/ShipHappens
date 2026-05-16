from pathlib import Path

from dotenv import load_dotenv

# Load .env before any module reads env vars at import time.
load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=True)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import Settings
from fastapi import APIRouter

# routers
from app.routers import sessions, sourcefiles, papers, generation, questions, style, blueprint

# Initialize settings
settings = Settings()

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="ShipHappens - Intelligent Exam Paper Generator",
    version="0.1.0",
)

# Add CORS middleware for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def welcome():
    """Welcome endpoint - returns a welcome message"""
    return JSONResponse(
        status_code=200,
        content={
            "message": "Welcome to ShipHappens API",
            "description": "Intelligent Exam Paper Generator for O/A Level Exams",
            "version": "0.1.0",
            "endpoints": {
                "health": "/health",
                "docs": "/docs",
                "redoc": "/redoc",
            },
        },
    )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return JSONResponse(
        status_code=200,
        content={
            "status": "healthy",
            "app": settings.app_name,
        },
    )


# include routers
app.include_router(sessions.router)
app.include_router(sourcefiles.router)
app.include_router(blueprint.router)
app.include_router(papers.router)
app.include_router(generation.router)
app.include_router(questions.router)
app.include_router(style.router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
