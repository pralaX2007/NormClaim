"""
NormClaim — Database Setup
SQLAlchemy SQLite setup for persistent document tracking.
"""

from sqlalchemy import create_engine, Column, String, DateTime, Boolean, Float, Integer, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

DATABASE_URL = "sqlite:///./normclaim.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class DocumentRecord(Base):
    __tablename__ = "documents"

    id = Column(String, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    upload_time = Column(DateTime, default=datetime.utcnow)
    has_extraction = Column(Boolean, default=False)
    has_report = Column(Boolean, default=False)
    file_size_bytes = Column(Integer, nullable=True)


class ExtractionRecord(Base):
    __tablename__ = "extractions"

    document_id = Column(String, primary_key=True, index=True)
    result_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class ReportRecord(Base):
    __tablename__ = "reports"

    document_id = Column(String, primary_key=True, index=True)
    report_json = Column(Text, nullable=False)
    claim_delta_inr = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)


# Create all tables
Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
