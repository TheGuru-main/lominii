"""LOMINII Chat Room – Conversational AI with real external sources"""
import asyncio
import uuid
import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from platform.database import get_db
from platform.auth import get_current_user
from platform.content_filter import is_blocked, is_ai_blocked
from platform.gsp import normalise, calculate_lsum, calculate_ssum, first_letter_index, gsp_place
from platform.prompts import PROMPTS
from platform.gsg import gps_to_gsg
from platform.intent_analyzer import analyze
from schemas import ChatResponse, GSPCellOut, NewsItem

router = APIRouter(prefix="/api/chat", tags=["Chat"])


@router.post("/", response_model=ChatResponse)
async def chat(
    request: Request,
    email: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    data = await request.json()
    query = data.get("query", "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="Missing query")
    if is_blocked(query):
        raise HTTPException(status_code=400, detail="Blocked query")

    # ---------- Conversation history ----------
    history_list = data.get("history", [])
    history_str = ""
    for msg in history_list:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        history_str += f"{role.capitalize()}: {content}\n"

    # ---------- User context (simplified, extend with DB later) ----------
    lang = "en"
    country = "Nigeria"

    # ---------- Normalisation & intent ----------
    norm_query = normalise(query, lang)
    ctx = analyze(norm_query)
    domain = ctx["domain"]

    # ---------- GSP placement (for logging) ----------
    L = calculate_lsum(norm_query, lang)
    S = calculate_ssum(norm_query, lang)
    c = first_letter_index(norm_query, lang)
    gsp = gsp_place(L, S, c, K=5)
    primary = gsp["primary_cell"]

    # ---------- GSG cell (optional) ----------
    gsg_data = None
    lat = data.get("lat")
    lon = data.get("lon")
    if lat is not None and lon is not None:
        try:
            gsg_cell, _ = gps_to_gsg(float(lat), float(lon))
            gsg_data = GSPCellOut(
                col=primary["col"],
                row=primary["row"],
                cell_id=f"city.{gsg_cell[0]}.{gsg_cell[1]}"
            )
        except Exception:
            pass

    # ---------- Fetch external sources (parallel) ----------
    async with httpx.AsyncClient() as client:
        dict_url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{norm_query}"
        news_url = f"https://gnews.io/api/v4/search?q={norm_query}&lang=en&max=6&apikey=demo"
        dict_task = client.get(dict_url)
        news_task = client.get(news_url)
        dict_resp, news_resp = await asyncio.gather(dict_task, news_task)

    definition = None
    if dict_resp.status_code == 200:
        try:
            dict_data = dict_resp.json()
            definition = dict_data[0]["meanings"][0]["definitions"][0]["definition"]
        except Exception:
            definition = None

    news_articles = []
    if news_resp.status_code == 200:
        try:
            news_data = news_resp.json()
            articles = news_data.get("articles", [])[:6]
            news_articles = [NewsItem(title=a["title"], url=a["url"]) for a in articles]
        except Exception:
            news_articles = []

    # ---------- Build sources string ----------
    sources = f"Dictionary: {definition or 'None'}\nNews: {news_articles}"

    # ---------- Conversation prompt ----------
    prompt_template = PROMPTS["conversation"]
    prompt = prompt_template.format(
        query=norm_query,
        conversation_history=history_str,
        sources=sources,
        country=country,
        language=lang
    )

    # ---------- AI call placeholder (replace with real AI call) ----------
    ai_answer = prompt   # TODO: replace with actual Hugging Face inference

    # ---------- Build response ----------
    response = ChatResponse(
        query=query,
        answer=ai_answer,
        gsp_cell=gsg_data,
        definition=definition,
        news=news_articles,
        did_you_mean=None,
        conversation_id=str(uuid.uuid4())
    )
    return response