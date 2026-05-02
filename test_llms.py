import asyncio
from llm_client import call_llm

async def test_llms():
    print('Testing Groq...')
    try:
        response = await call_llm('You are a helpful assistant who responds in JSON.', 'Reply with {"status": "SUCCESS"}')
        print(f'Groq Response: {response}')
    except Exception as e:
        print(f'Groq Error: {e}')

asyncio.run(test_llms())
