import sys
import asyncio
from pathlib import Path

# Add the project dir to path
sys.path.append('c:/Users/other/Documents/Kuliah/Semester 6/KapSel/ecast')

from app.tts_engine import TTSEngine

async def test():
    tts = TTSEngine()
    try:
        await tts.synthesize_podcast_async(["Hello world"], "en", "test.mp3", lambda c,t: None)
        print("Success")
    except Exception as e:
        import traceback
        traceback.print_exc()

asyncio.run(test())
