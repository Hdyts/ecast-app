"""
eCast — FastAPI Main Application
REST API server orchestrating the full ePub → Podcast pipeline.
"""

import asyncio
import json
import logging
import shutil
import uuid
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.config import (
    UPLOAD_DIR,
    OUTPUT_DIR,
    MAX_FILE_SIZE_BYTES,
    MAX_FILE_SIZE_MB,
    ALLOWED_EXTENSIONS,
    CHAPTER_LIMIT,
    OUTPUT_FORMAT,
    get_config_summary,
)
from app.epub_parser import EpubParser
from app.preprocessor import ArabicPreprocessor
from app.translator import Translator
from app.tts_engine import TTSEngine
from app.summarizer import Summarizer
from app.llm_manager import LLMManager

# Logging Configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("ecast")

# FastAPI App
app = FastAPI(
    title="eCast — Arabic ePub to Podcast",
    description="Convert Arabic ePub books into multilingual podcast audio (AR, ID, EN)",
    version="1.0.0",
)

# CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global State
# Lazy-loaded services
_translator: Optional[Translator] = None
_tts_engine: Optional[TTSEngine] = None
_preprocessor: Optional[ArabicPreprocessor] = None
_summarizer: Optional[Summarizer] = None
_llm_manager: Optional[LLMManager] = None

# File tracking (file_id → dict)
_uploaded_files: dict[str, dict] = {}


def get_translator() -> Translator:
    global _translator
    if _translator is None:
        _translator = Translator()
    return _translator

def get_tts_engine() -> TTSEngine:
    global _tts_engine
    if _tts_engine is None:
        _tts_engine = TTSEngine()
    return _tts_engine

def get_preprocessor() -> ArabicPreprocessor:
    global _preprocessor
    if _preprocessor is None:
        glossary_path = Path(__file__).parent.parent / "glossary" / "islamic_terms.json"
        _preprocessor = ArabicPreprocessor(glossary_path=glossary_path)
    return _preprocessor

def get_summarizer() -> Summarizer:
    global _summarizer
    if _summarizer is None:
        _summarizer = Summarizer()
    return _summarizer

def get_llm_manager() -> LLMManager:
    global _llm_manager
    if _llm_manager is None:
        _llm_manager = LLMManager()
    return _llm_manager

# Static Files (Frontend)
static_dir = Path(__file__).parent.parent / "static"

@app.get("/")
async def serve_index():
    index_path = static_dir / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="Frontend not found")
    return FileResponse(str(index_path), media_type="text/html")

app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Models
class ChatRequest(BaseModel):
    file_id: str
    message: str
    history: list[dict] = []

class AudioRequest(BaseModel):
    text: str
    lang: str


# API Endpoints

@app.get("/api/status")
async def get_status():
    return {
        "status": "online",
        "version": "1.0.0",
        "config": get_config_summary(),
        "translator": get_translator().get_status(),
        "tts": get_tts_engine().get_status(),
    }

@app.post("/api/upload")
async def upload_epub(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type: {ext}. Only .epub files are supported."
        )

    content = await file.read()
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"File too large: {len(content) / 1024 / 1024:.1f}MB. Maximum is {MAX_FILE_SIZE_MB}MB."
        )

    file_id = str(uuid.uuid4())[:8]
    safe_filename = f"{file_id}_{file.filename}"
    file_path = UPLOAD_DIR / safe_filename

    with open(file_path, "wb") as f:
        f.write(content)

    logger.info(f"File uploaded: {safe_filename} ({len(content) / 1024:.1f} KB)")

    try:
        parser = EpubParser(file_path)
        parser.load()
        metadata = parser.get_book_metadata()
        chapters = parser.get_chapters()
        
        all_text = []
        for idx in range(len(chapters)):
            all_text.append(parser.get_chapter_text(idx))
            
        raw_text = "\n\n".join(all_text)
        
        preprocessor = get_preprocessor()
        clean_text = preprocessor.clean_text(raw_text)
        
    except Exception as e:
        file_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=f"Failed to parse ePub: {str(e)}")

    _uploaded_files[file_id] = {
        "path": file_path,
        "filename": file.filename,
        "metadata": metadata,
        "preview_text": clean_text,
        "translations": {}
    }

    return {
        "file_id": file_id,
        "filename": file.filename,
        "size_kb": round(len(content) / 1024, 1),
        "metadata": metadata,
    }


@app.get("/api/files")
async def list_files():
    """List all uploaded files."""
    return [
        {
            "file_id": fid,
            "filename": fdata["filename"],
            "metadata": fdata["metadata"]
        }
        for fid, fdata in _uploaded_files.items()
    ]


@app.get("/api/file/{file_id}/content")
async def get_file_content(file_id: str, lang: str = Query("ar")):
    """Get the text content of a file, translated if requested."""
    if file_id not in _uploaded_files:
        raise HTTPException(status_code=404, detail="File not found")
    
    file_data = _uploaded_files[file_id]
    text = file_data["preview_text"]
    
    if lang == "ar":
        return {"content": text}
    
    if lang in file_data["translations"]:
        return {"content": file_data["translations"][lang]}
        
    # Translate it on the fly
    translator = get_translator()
    preprocessor = get_preprocessor()
    sentences = preprocessor.segment_sentences(text)
    
    try:
        # Limited translation length for real-time responsiveness if it's too long
        max_sentences = 50
        if len(sentences) > max_sentences:
            sentences = sentences[:max_sentences]
            
        translated_sentences = await asyncio.to_thread(
            translator.translate_batch, sentences, lang, None, lambda c,t: None
        )
        translated_text = " ".join(translated_sentences)
        if len(sentences) < len(preprocessor.segment_sentences(text)):
            translated_text += "\n\n... [Translation Truncated for Preview]"
            
        file_data["translations"][lang] = translated_text
        return {"content": translated_text}
    except Exception as e:
        logger.error(f"Translation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat")
async def chat_with_file(req: ChatRequest):
    """Chat with the selected document."""
    if req.file_id not in _uploaded_files:
        raise HTTPException(status_code=404, detail="File not found")
        
    file_data = _uploaded_files[req.file_id]
    context_text = file_data["preview_text"]
    
    # Truncate context to fit in LLM context window
    max_context = 6000
    if len(context_text) > max_context:
        context_text = context_text[:max_context] + "\n...[truncated]"
        
    system_prompt = (
        "You are an AI reading assistant. You help users understand a provided document. "
        "Answer the user's questions based primarily on the following context. "
        "If you don't know the answer based on the context, say so. "
        "You must respond in the same language as the user's prompt.\n\n"
        f"Document Context:\n{context_text}"
    )
    
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(req.history)
    messages.append({"role": "user", "content": req.message})
    
    llm = get_llm_manager()
    try:
        response = await asyncio.to_thread(llm.generate_chat, messages)
        return {"response": response}
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/generate_audio")
async def generate_audio(req: AudioRequest):
    """Generate audio from arbitrary text."""
    tts = get_tts_engine()
    preprocessor = get_preprocessor()
    
    if req.lang not in ["ar", "id", "en"]:
        raise HTTPException(status_code=400, detail="Unsupported language")
        
    audio_id = str(uuid.uuid4())[:8]
    audio_filename = f"chat_audio_{audio_id}_{req.lang}.{OUTPUT_FORMAT}"
    audio_path = OUTPUT_DIR / audio_filename
    
    try:
        clean_text = preprocessor.clean_text(req.text, remove_tashkeel=False, normalize=True) if req.lang == "ar" else req.text
        sentences = preprocessor.segment_sentences(clean_text)
        
        # limit sentences to prevent huge generation overhead for simple chat
        if len(sentences) > 20:
             sentences = sentences[:20]

        tts_sentences = [preprocessor.preprocess_for_tts(s) for s in sentences]
        
        await tts.synthesize_podcast_async(tts_sentences, req.lang, audio_path, lambda c,t: None)
        
        return {
            "audio_id": audio_id,
            "filename": audio_filename,
            "url": f"/api/audio_file/{audio_filename}"
        }
    except Exception as e:
        logger.error(f"Audio generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/audio_file/{filename}")
async def get_audio_file(filename: str):
    """Serve a generated audio file."""
    audio_path = OUTPUT_DIR / filename
    if not audio_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found")
    return FileResponse(str(audio_path), media_type="audio/mpeg")


@app.on_event("startup")
async def startup_event():
    logger.info("=" * 50)
    logger.info("  eCast — Chatbot Interface")
    logger.info("=" * 50)
