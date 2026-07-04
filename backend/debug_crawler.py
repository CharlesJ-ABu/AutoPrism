import asyncio
import sys
import os

# 确保能找到 app 目录
sys.path.append(os.getcwd())

async def test_crawler():
    try:
        from app.tasks.scheduler import refresh_all_sources
        print("--- 启动抓取任务测试 ---")
        await refresh_all_sources()
        print("--- 任务运行结束 ---")
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_crawler())
