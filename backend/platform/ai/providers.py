"""AI Service – Gemini (primary) + Hugging Face (fallback) (Platform Layer)"""
import os
import httpx
import google.generativeai as genai

# ── Configure Gemini ──────────────────────────────────

GEMINI_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)

HF_KEY = os.getenv("HUGGINGFACE_API_KEY")

# Use a fast, capable model on Hugging Face (free inference)

HF_MODEL = "mistralai/Mistral-7B-Instruct-v0.3"
HF_API_URL =f"https://api-inference.huggingface.co/models/{HF_MODEL}"


async def generate_text(prompt: str) -> str:
    """
    Generate text using Gemini first; if it fails, try Hugging Face.
    Returns a user‑friendly fallback if both are unavailable.
    """
    # 1. Try Gemini
    if GEMINI_KEY:
        try:
            model = genai.GenerativeModel("gemini-2.0-flash")
            response = await model.generate_content_async(prompt)
            if response and response.text:
                return response.text.strip()
        except Exception:
            pass   # silently fall through to Hugging Face

    # 2. Try Hugging Face
    if HF_KEY:
        try:
            headers = {"Authorization": f"Bearer {HF_KEY}"}
            payload = {
                "inputs": prompt,
                "parameters": {"max_new_tokens": 300, "temperature": 0.3}
            }
            async with httpx.AsyncClient(timeout=25) as client:
                resp = await client.post(HF_API_URL, json=payload, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    if isinstance(data, list) and len(data) > 0:
                        return data[0].get("generated_text", "").strip()
        except Exception:
            pass

    # 3. Fallback if both are unavailable
    return "Summary temporarily unavailable. Please try again shortly."