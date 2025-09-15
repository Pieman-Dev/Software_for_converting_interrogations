from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from dotenv import load_dotenv
import os
from urllib.parse import quote_plus
from dotenv import load_dotenv
import os

load_dotenv()

class Base(DeclarativeBase):
    pass



load_dotenv()  # ⚠️ вызов единожды

def _build_dsn() -> str:
    user = quote_plus(os.getenv("DB_USER", "postgres"))
    pwd  = quote_plus(os.getenv("DB_PASS", "1234"))
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    name = os.getenv("DB_NAME", "postgres")
    return f"postgresql+psycopg2://{user}:{pwd}@{host}:{port}/{name}"

engine = create_engine(_build_dsn(), echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)