"""
FastAPI‑сервис для транскрипции аудио/видео через whisper.cpp
============================================================

Запуск (разработческая среда):
    uvicorn interview_service:app --reload

Конфигурация берётся из переменных окружения (можно хранить в .env):
    DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASS  – для PostgreSQL
    WHISPER_BINARY        – путь к whisper-cli.exe (по умолч. ./whisper-cli.exe)
    WHISPER_MODEL         – путь к ggml‑*.bin модели (по умолч. ./model/large-v3-turbo-q5_1.bin)
    FFMPEG_BINARY         – путь к ffmpeg (если не в PATH)
    LANG_DEFAULT          – язык распознавания, ru|en|...  (по умолч. ru)

Папки data/audio и data/transcripts создаются автоматически.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import uuid
from pathlib import Path
from typing import Sequence

from fastapi.responses import StreamingResponse
from io import BytesIO

from dotenv import load_dotenv
from fastapi import BackgroundTasks, Depends, FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

# ──────────────────── Загрузка окружения и БД ─────────────────────
load_dotenv()

from db import SessionLocal  # импортируется из вашего проекта
import models  # Base.metadata уже содержит AudioFile / Transcript

# ──────────────────── Параметры (можно переопределить через env) ──
BASE_DIR = Path(__file__).resolve().parent

WHISPER_BINARY: Path = Path(os.getenv("WHISPER_BINARY", BASE_DIR / "whisper-cli.exe"))
WHISPER_MODEL: Path = Path(os.getenv("WHISPER_MODEL", BASE_DIR / "model" / "large-v3-turbo-q5_1.bin"))
FFMPEG_BINARY: str = os.getenv("FFMPEG_BINARY", shutil.which("ffmpeg") or "ffmpeg")
LANG_DEFAULT: str = os.getenv("LANG_DEFAULT", "ru")

AUDIO_DIR = BASE_DIR / "data" / "audio"
TRANSCRIPT_DIR = BASE_DIR / "data" / "transcripts"

THREADS = int(os.getenv("THREADS", os.cpu_count() or 4))

for d in (AUDIO_DIR, TRANSCRIPT_DIR):
    d.mkdir(parents=True, exist_ok=True)

# ──────────────────── Pydantic‑ответы ─────────────────────────────
class QueueResponse(BaseModel):
    id: int
    status: str = "queued"

    class Config:
        orm_mode = True

class TranscriptResponse(BaseModel):
    id: int
    transcript: str

    class Config:
        orm_mode = True

# ──────────────────── Утилиты ─────────────────────────────────────

def _convert_to_wav(src: Path) -> Path:
    """Конвертация/ресэмпл до 16 kHz mono PCM wav."""
    dst = src.with_suffix(".16k.wav")
    if dst.exists():  # кешируем, чтобы не пересоздавать
        return dst
    cmd: Sequence[str] = [
        FFMPEG_BINARY,
        "-y",
        "-i",
        str(src),
        "-ar",
        "16000",
        "-ac",
        "1",
        "-c:a",
        "pcm_s16le",
        str(dst),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg error\n{result.stderr}")
    return dst

def _run_whisper(wav_path: Path, out_stem: Path, lang: str = LANG_DEFAULT) -> None:
    """Запуск whisper-cli.exe с параметрами."""

    if not WHISPER_BINARY.exists() or not WHISPER_MODEL.exists():
        raise RuntimeError("Whisper binaries/models not found; service not configured")

    cmd: Sequence[str] = [
        str(WHISPER_BINARY),
        "-m",
        str(WHISPER_MODEL),
        "-f",
        str(wav_path),
        "-l",
        lang,
        "-t",
        str(THREADS),
        "-otxt",
        "--output-file",
        str(out_stem),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Whisper error\n{result.stderr}")

# ──────────────────── Задача пайплайна ────────────────────────────

def _pipeline(db: Session, audio_obj: models.AudioFile, lang: str) -> None:
    """Конвертируем, запускаем whisper, сохраняем Transcript."""
    original_path = Path(audio_obj.original_path)
    try:
        wav_path = (
            original_path if original_path.suffix.lower() == ".wav" else _convert_to_wav(original_path)
        )
        out_stem = TRANSCRIPT_DIR / original_path.stem
        _run_whisper(wav_path, out_stem, lang=lang)
        txt_file = out_stem.with_suffix(".txt")
        transcript_text = txt_file.read_text(encoding="utf-8")

        # Сохраняем в БД
        transcript_obj = models.Transcript(audio_id=audio_obj.id, language=lang, text=transcript_text)
        db.add(transcript_obj)
        audio_obj.duration = 0  # TODO: вычислить длительность, если нужно
        db.commit()

    except Exception as exc:
        db.rollback()
        raise exc

# ──────────────────── FastAPI ─────────────────────────────────────

app = FastAPI(
    title="Interview Processing Service",
    description="REST‑API для транскрипции через whisper.cpp",
    version="0.3.0",
)

# Dependency

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.post("/transcribe/", response_model=QueueResponse, summary="Отправить файл на транскрипцию")
async def transcribe_audio(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Видео/аудио (mp4, mov, wav, mp3, flac, m4a)"),
    lang: str = LANG_DEFAULT,
    db: Session = Depends(get_db),
):
    if not file.filename.lower().endswith((".mp4", ".mov", ".wav", ".mp3", ".flac", ".m4a")):
        raise HTTPException(status_code=400, detail="Unsupported media type")

    uid = uuid.uuid4().hex
    raw_path = AUDIO_DIR / f"{uid}_{file.filename}"

    # сохраняем файл
    with raw_path.open("wb") as f:
        f.write(await file.read())

    # создаём запись в БД
    audio_obj = models.AudioFile(original_path=str(raw_path), duration=0)
    db.add(audio_obj)
    db.commit()
    db.refresh(audio_obj)

    # фоновой задачей запустить pipeline
    background_tasks.add_task(_pipeline, db, audio_obj, lang)

    return QueueResponse(id=audio_obj.id)


@app.get(
    "/transcript/{audio_id}/download",
    summary="Скачать файл транскрипта",
    response_class=StreamingResponse,
)
def download_transcript_file(
    audio_id: int,
    db: Session = Depends(get_db),
):
    # 1. Найти в БД
    transcript = db.query(models.Transcript)\
                   .filter_by(audio_id=audio_id)\
                   .first()
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found")

    # 2. Упаковать текст в поток
    data = transcript.text.encode("utf-8")
    buf  = BytesIO(data)

    # 3. Отдать как attachment
    headers = {
        "Content-Disposition": f"attachment; filename=transcript_{audio_id}.txt"
    }
    return StreamingResponse(buf, media_type="text/plain", headers=headers)
