import httpx
import os
from dotenv import load_dotenv

load_dotenv()

key = os.getenv("GROQ_API_KEYS", "").split(",")[0]
print(f"Testing key: {key[:10]}...")

url = "https://api.groq.com/openai/v1/chat/completions"
headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
data = {
    "model": "llama3-8b-8192",
    "messages": [{"role": "user", "content": "Hi"}],
    "max_tokens": 10
}

with httpx.Client() as client:
    resp = client.post(url, headers=headers, json=data)
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.text}")
