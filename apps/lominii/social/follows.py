from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from platform.database import get_db
from platform.auth import get_current_user
from platform.models import User, Follow