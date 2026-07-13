"""LOMINII Search Room – Unified Search Router (Real DB + GSG + Cache + Live AI)"""
import asyncio
import hashlib
import httpx
from datetime import datetime, timedelta
from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from platform.gsp import normalise, calculate_lsum, calculate_ssum, first_letter_index, gsp_place, elastic_cloud
from platform.prompts import get_prompt
from platform.content_filter import is_blocked, is_ai_blocked
from platform.auth import get_current_user
from platform.database import get_db
from platform.gsg import gps_to_gsg
from platform.intent_analyzer import analyze
from models import User, Search, SearchCache

router = APIRouter(prefix="/api/search", tags=["Search"])

CACHE_TTL_ANONYMOUS = 5
CACHE_TTL_AUTHENTICATED = 300

