import httpx
import asyncio
from config import settings

async def list_models():
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={settings.GEMINI_API_KEY}"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            models = resp.json().get("models", [])
            for m in models:
                print(f"- {m['name']}")
        else:
            print(f"Error: {resp.text}")

if __name__ == "__main__":
    asyncio.run(list_models())
