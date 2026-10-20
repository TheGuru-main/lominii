"""Admin Crawler Routes"""
from fastapi import APIRouter, Depends, HTTPException
from lominii_platform.auth import get_current_user
from lominii_platform.crawler import CRAWLER_ENABLED, crawl_url
from lominii_platform.pagerank import compute_pagerank

router = APIRouter(prefix="/api/admin/crawler", tags=["Admin"])

@router.post("/start")
async def start_crawler(seed_url: str, email: str = Depends(get_current_user)):
    if not CRAWLER_ENABLED:
        raise HTTPException(status_code=400, detail="Crawler is disabled")
    return {"message": "Crawler started", "seed": seed_url}

@router.get("/status")
async def crawler_status():
    return {"enabled": CRAWLER_ENABLED}