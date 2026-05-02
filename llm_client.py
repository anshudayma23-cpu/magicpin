import httpx
import logging
from typing import Optional, List, Dict, Any
from config import settings

logger = logging.getLogger("vera.llm_client")

# Key rotation state
_last_key_idx = -1

import asyncio

async def call_llm(system_prompt: str, user_prompt: str, temperature: float = None) -> str:
    """Entry point for LLM calls with Groq primary, Groq secondary, and Gemini fallback."""
    if temperature is None:
        temperature = settings.TEMPERATURE

    # 1. Try Groq Cascade (70B -> 8B) across keys
    groq_keys = settings.groq_keys_list
    if groq_keys:
        global _last_key_idx
        start_idx = (_last_key_idx + 1) % len(groq_keys)
        
        for i in range(len(groq_keys)):
            current_idx = (start_idx + i) % len(groq_keys)
            key = groq_keys[current_idx]
            _last_key_idx = current_idx
            
            # Try 70B
            res, status = await _try_groq(system_prompt, user_prompt, key, settings.PRIMARY_MODEL, f"Primary-70B-{current_idx}", temperature)
            if status == 429:
                logger.warning(f"Groq Primary 429 limit hit. Waiting 3s before retry...")
                await asyncio.sleep(3)
                res, status = await _try_groq(system_prompt, user_prompt, key, settings.PRIMARY_MODEL, f"Primary-70B-{current_idx}-Retry", temperature)
            if res:
                return res
                
            # If 70B fails, we skip the 8B fallback because it cannot reliably retain
            # the Phase K engagement levers (curiosity, loss, etc.) in a 5-sentence format.
            # We will rely on Gemini as the smart fallback.
            
            # If failed, wait a bit before trying next key to respect TPM reset
            if i < len(groq_keys) - 1:
                logger.info(f"Groq key {current_idx} failed, retrying with next key in 5s...")
                await asyncio.sleep(5)

    # 2. Try Gemini Fallback
    if settings.GEMINI_API_KEY:
        res = await _try_gemini(system_prompt, user_prompt, temperature)
        if res:
            return res

    logger.error("All LLM providers failed!")
    return ""


async def _try_groq(system_prompt: str, user_prompt: str, api_key: str, model_name: str, label: str, temperature: float) -> tuple[Optional[str], Optional[int]]:
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": temperature,
        "max_tokens": 512,
        "response_format": {"type": "json_object"}
    }
    
    try:
        async with httpx.AsyncClient(timeout=settings.LLM_TIMEOUT) as client:
            response = await client.post(url, headers=headers, json=data)
            if response.status_code == 200:
                return response.json()["choices"][0]["message"]["content"], 200
            else:
                logger.warning(f"Groq {label} error ({response.status_code}): {response.text}")
                return None, response.status_code
    except Exception as e:
        logger.error(f"Groq {label} exception: {str(e)}")
        return None, None


async def _try_gemini(system_prompt: str, user_prompt: str, temperature: float) -> str:
    if not settings.GEMINI_API_KEY:
        return ""
        
    # Using Gemini 1.5 Flash
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.FALLBACK_MODEL}:generateContent?key={settings.GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    
    full_prompt = f"SYSTEM: {system_prompt}\n\nUSER: {user_prompt}"
    data = {
        "contents": [{
            "parts": [{"text": full_prompt}]
        }],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": 512,
        }
    }
    
    try:
        async with httpx.AsyncClient(timeout=settings.LLM_TIMEOUT) as client:
            response = await client.post(url, headers=headers, json=data)
            if response.status_code == 200:
                res_json = response.json()
                if "candidates" in res_json and res_json["candidates"]:
                    return res_json["candidates"][0]["content"]["parts"][0]["text"]
            else:
                logger.warning(f"Gemini error ({response.status_code}): {response.text}")
                return ""
    except Exception as e:
        logger.error(f"Gemini exception: {str(e)}")
        return ""
    return ""

if __name__ == "__main__":
    import asyncio
    async def test():
        print(f"Testing LLM Client ({settings.PRIMARY_MODEL})...")
        res = await call_llm("You are a helpful assistant.", "Say 'Hello from Vera' and tell me which model you are.")
        print(f"\nResponse:\n{res}")
    asyncio.run(test())
