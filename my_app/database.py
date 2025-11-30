from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base  # ← Change l'import
import os

DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://apollo:apollo123@db:5432/apollo')

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()  # ← Garde comme ça, juste change l'import

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()