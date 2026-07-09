"""
LOMINII – Main FastAPI Application
Gurutech Platform Architecture – Shared Platform, Independent Modules
"""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# We will import these as soon as we create the platform files
# from platform.database import engine, Base

app = FastAPI(title="LOMINII Platform", version="1.0.0")

# CORS – allow requests from any frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files (we'll add the frontend later)
# app.mount("/", StaticFiles(directory="static", html=True), name="static")

@app.get("/health")
async def health():
    return {"status": "ok", "app": "LOMINII"}

# For local development
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)