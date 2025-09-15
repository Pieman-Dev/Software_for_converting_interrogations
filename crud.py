from sqlalchemy.orm import Session
import models

def create_audio(db: Session, file_path: str, duration: int) -> models.AudioFile:
    obj = models.AudioFile(original_path=file_path, duration=duration)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

def get_audio(db: Session, audio_id: int):
    return db.query(models.AudioFile).filter_by(id=audio_id).first()

def list_audio(db: Session, skip=0, limit=20):
    return db.query(models.AudioFile).order_by(models.AudioFile.uploaded_at.desc())\
             .offset(skip).limit(limit).all()