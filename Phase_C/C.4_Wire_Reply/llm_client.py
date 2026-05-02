import httpx
import logging
import random
from typing import Optional
from config import settings

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("vera.llm_client")

# Track the last used key index for round-robin
_last_key_idx = random.randint(0, 1)

async def call_llm(system_prompt: str, user_prompt: str) -> str:
    """
    Unified LLM entry point with rotation and fallback.
    """
    global _last_key_idx
    
    groq_keys = settings.groq_keys_list
    print(f"LLM Client: Found {len(groq_keys)} Groq keys")
    if not groq_keys:
        logger.error("No Groq API keys found in config!")
        return await _try_gemini(system_prompt, user_prompt)

    # 1. Select Round-Robin Key
    _last_key_idx = (_last_key_idx + 1) % len(groq_keys)
    primary_key = groq_keys[_last_key_idx]
    secondary_key = groq_keys[(_last_key_idx + 1) % len(groq_keys)]
    
    print(f"LLM Client: Using Groq key index {_last_key_idx}")
    
    # 2. Try Primary Groq
    result = await _try_groq(system_prompt, user_prompt, primary_key, "Primary")
    if result:
        return result
        
    # 3. Try Secondary Groq (on failure/rate limit)
    logger.info("Primary Groq failed or rate-limited. Trying secondary key...")
    result = await _try_groq(system_prompt, user_prompt, secondary_key, "Secondary")
    if result:
        return result
        
    # 4. Final Fallback to Gemini
    logger.warning("Both Groq keys failed. Falling back to Gemini...")
    return await _try_gemini(system_prompt, user_prompt)

async def _try_groq(system_prompt: str, user_prompt: str, api_key: str, label: str) -> Optional[str]:
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": settings.PRIMARY_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": settings.TEMPERATURE,
        "max_tokens": 1024
    }
    
    try:
        async with httpx.AsyncClient(timeout=settings.LLM_TIMEOUT) as client:
            response = await client.post(url, headers=headers, json=data)
            print(f"LLM Client: Groq {label} Response - Status: {response.status_code}")
            if response.status_code == 200:
                return response.json()["choices"][0]["message"]["content"]
            else:
                print(f"LLM Client: Groq {label} Error Text: {response.text}")
                logger.error(f"Groq {label} error ({response.status_code}): {response.text}")
                return None
    except Exception as e:
        print(f"LLM Client: Groq {label} Exception: {str(e)}")
        logger.error(f"Groq {label} exception: {str(e)}")
        return None

async def _try_gemini(system_prompt: str, user_prompt: str) -> str:
    if not settings.GEMINI_API_KEY:
        logger.error("No Gemini API key found for fallback!")
        return ""
        
    # Reverting to v1beta for gemini-1.5-flash
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={settings.GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    print(f"LLM Client: Attempting Gemini Fallback...")
    
    # Gemini prompt construction (System prompt is merged for simplicity in Flash 1.5)
    full_prompt = f"SYSTEM: {system_prompt}\n\nUSER: {user_prompt}"
    data = {
        "contents": [{
            "parts": [{"text": full_prompt}]
        }],
        "generationConfig": {
            "temperature": settings.TEMPERATURE,
            "maxOutputTokens": 1024,
        }
    }
    
    try:
        async with httpx.AsyncClient(timeout=settings.LLM_TIMEOUT) as client:
            response = await client.post(url, headers=headers, json=data)
            if response.status_code == 200:
                # Parse Gemini response structure
                return response.json()["candidates"][0]["content"]["parts"][0]["text"]
            else:
                logger.error(f"Gemini fallback error ({response.status_code}): {response.text}")
                return ""
    except Exception as e:
        logger.error(f"Gemini exception: {str(e)}")
        return ""

# Test script
if __name__ == "__main__":
    import asyncio
    
    async def test():
        print("Testing LLM Client...")
        res = await call_llm("You are a helpful assistant.", "Say 'Hello from Vera' and tell me which model you are.")
        print(f"\nResponse:\n{res}")
        
    asyncio.run(test())
