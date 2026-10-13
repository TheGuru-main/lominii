"""ApiTube Video Service (Platform Layer)"""
import os
import httpx

API_KEY = os.getenv("APITUBE_API_KEY", "&&&&&&+++&&&&&")
BASE_URL = os.getenv("APITUBE_BASE_URL", "https://api.apitube.io/v1/news/everything?language.code=en&per_page=10")