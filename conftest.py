import importlib
import shutil
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import models

# ─────────── БД (SQLite in-memory) ───────────
@pytest.fixture(scope="session")
def engine():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
    )
    models.Base.metadata.create_all(engine)
    return engine


@pytest.fixture()
def db_session(engine):
    connection = engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection, autoflush=False, autocommit=False)
    session = Session()
    yield session
    session.close()
    transaction.rollback()
    connection.close()

# ─────────── FastAPI TestClient + monkeypatch ───────────
@pytest.fixture()
def client(db_session, monkeypatch, tmp_path):
    svc = importlib.import_module("python_service_initial")  # ваш основной файл

    # 1) подменяем зависимость get_db
    def _override_get_db():
        try:
            yield db_session
        finally:
            pass
    svc.app.dependency_overrides[svc.get_db] = _override_get_db

    # 2) временные каталоги для файлов
    audio_dir = tmp_path / "audio"
    tr_dir    = tmp_path / "transcripts"
    audio_dir.mkdir(); tr_dir.mkdir()
    monkeypatch.setattr(svc, "AUDIO_DIR", audio_dir)
    monkeypatch.setattr(svc, "TRANSCRIPT_DIR", tr_dir)

    # 3) глушим тяжёлые функции
    def fake_run_whisper(wav_path, out_stem, lang=svc.LANG_DEFAULT):
        out_stem.with_suffix(".txt").write_text("test transcript", encoding="utf-8")
    monkeypatch.setattr(svc, "_run_whisper", fake_run_whisper)

    def fake_convert_to_wav(src):
        dst = src.with_suffix(".16k.wav")
        shutil.copy(src, dst)
        return dst
    monkeypatch.setattr(svc, "_convert_to_wav", fake_convert_to_wav)

    return TestClient(svc.app)
