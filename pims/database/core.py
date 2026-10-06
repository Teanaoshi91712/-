from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Use SQLite for the MVP, as specified in the design.
# In a production environment, this would be read from environment variables.
DATABASE_URL = "sqlite:///./pims.db"

# Create the SQLAlchemy engine
# connect_args={"check_same_thread": False} is required for SQLite if sharing across threads
engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)

# Create a session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for declarative models
Base = declarative_base()

def get_db() -> Generator:
    """
    Dependency function to get a database session.
    Automatically closes the session after use.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
