"""
LOMINII – Main FastAPI Application
Gurutech Platform Architecture – Shared Platform, Independent Modules
"""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# ── Import application routers ──────────────────────────
from apps.lominii.search.router import router as search_router

app = FastAPI(title="LOMINII Platform", version="1.0.0")

# CORS – allow requests from any frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Mount application routes ────────────────────────────
app.include_router(search_router)

@app.get("/health")
async def health():
    return {"status": "ok", "app": "LOMINII"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)