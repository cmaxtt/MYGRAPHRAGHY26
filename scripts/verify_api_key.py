
import asyncio
import os
from dotenv import load_dotenv

# Load key before import
load_dotenv() 

try:
    from api_client import api_client
except Exception as e:
    print(f"Import Error: {e}")
    exit(1)

async def verify():
    print(f"Verifying DeepSeek API Key: {os.environ.get('DEEPSEEK_API_KEY')[:10]}...")
    try:
        # Simple chat completion
        response = await api_client.get_completion("Hello, just checking connection.", system_prompt="Check")
        print(f"Success! Response: {response}")
    except Exception as e:
        print(f"Failed: {e}")

if __name__ == "__main__":
    asyncio.run(verify())
