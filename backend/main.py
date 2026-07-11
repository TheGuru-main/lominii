"""
LOMINII – Main FastAPI Application
Gurutech Platform Architecture – Shared Platform, Independent Modules
"""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from apps.lominii.search.router import router as search_router
from apps.lominii.social.router import router as social_router
from apps.lominii.auth.router import router as auth_router
from apps.lominii.admin.router import router as admin_router
from platform.database import engine, Base

app = FastAPI(title="LOMINII Platform", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(search_router)
app.include_router(social_router)
app.include_router(auth_router)
app.include_router(admin_router)
app.mount("/", StaticFiles(directory="public", html=True), name="static")

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

@app.get("/health")
async def health():
    return {"status": "ok", "app": "LOMINII"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)