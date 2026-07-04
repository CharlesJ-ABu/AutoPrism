import asyncio
import os
import sys
from dotenv import load_dotenv

# Ensure app is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app.core.config import settings

# Override settings manually for standalone script test
load_dotenv(".env")
settings.AI_API_BASE = os.getenv("AI_API_BASE", settings.AI_API_BASE)
settings.AI_API_KEY = os.getenv("AI_API_KEY", settings.AI_API_KEY)
settings.AI_MODEL = os.getenv("AI_MODEL", settings.AI_MODEL)

# Mocked DB Session
class MockSession:
    pass

from app.services.ai_service import AIService

async def test_denoising():
    print(f"=== Testing AutoPrism AI Denoising Pipeline ===")
    print(f"Model: {settings.AI_MODEL}")
    print(f"API Base: {settings.AI_API_BASE}")
    
    if not settings.AI_API_KEY or settings.AI_API_KEY == "sk-xxxxxxxxxxxxxxxxxxx":
        print("\n[ERROR] Please update AI_API_KEY in .env file before testing!")
        return

    # A mock news article
    sample_news = """
    路透社报道：受红海局势持续紧张影响，特斯拉宣布将其位于德国柏林格伦海德(Gruenheide)的超级工厂停产约两周。
    特斯拉在一份声明中表示，由于胡塞武装在红海袭击船只导致运输路线改变，零部件供应出现短缺。
    停产时间将从 1 月 29 日持续到 2 月 11 日。这对特斯拉在欧洲的市场交付可能会带来一定负面影响，
    同时，也有投资者担忧其他欧洲车企的供应链稳定性。
    """
    
    print("\n[INPUT] Raw News Content:")
    print(sample_news.strip())
    
    service = AIService(db=MockSession())
    
    print("\n[PROCESSING] Calling AI Model... This may take a few seconds.")
    try:
        prompt = service._build_denoising_prompt(sample_news)
        result = await service._call_ai(prompt)
        
        print("\n[SUCCESS] AI Extraction Result:")
        import json
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
        print("\n✅ Pipeline is working correctly! You can now use this with the full database.")
    except Exception as e:
        print(f"\n❌ [ERROR] AI API Call failed: {str(e)}")
        print("Please check your .env configuration and network connection.")

if __name__ == "__main__":
    asyncio.run(test_denoising())
