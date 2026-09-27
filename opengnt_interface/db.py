from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from opengnt_interface.paths import database_path

DATABASE_URL = f"sqlite:///{database_path()}"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
