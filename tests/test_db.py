import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from pims.database.core import Base
from pims.database.models import Company, TradePlan
from pims.schemas.agent_io import CIODecision

# Use an in-memory SQLite database for testing
TEST_DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture(scope="module")
def engine():
    return create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})

@pytest.fixture(scope="module")
def tables(engine):
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def db_session(engine, tables):
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    yield session
    session.close()

def test_company_creation(db_session):
    """Test creating a company record."""
    company = Company(ticker="AAPL", name="Apple Inc.", sector="Technology")
    db_session.add(company)
    db_session.commit()

    saved_company = db_session.query(Company).filter_by(ticker="AAPL").first()
    assert saved_company is not None
    assert saved_company.name == "Apple Inc."
    assert saved_company.sector == "Technology"

def test_trade_plan_creation(db_session):
    """Test creating a trade plan record."""
    plan = TradePlan(
        ticker="AAPL",
        decision="BUY",
        recommended_weight=0.05,
        status="PENDING"
    )
    db_session.add(plan)
    db_session.commit()

    saved_plan = db_session.query(TradePlan).filter_by(ticker="AAPL").first()
    assert saved_plan is not None
    assert saved_plan.decision == "BUY"

def test_cio_schema_validation():
    """Test the Pydantic schema validation for CIO Agent output."""
    valid_data = {
        "ticker": "AAPL",
        "company": "Apple Inc.",
        "decision": "BUY",
        "current_price": 150.0,
        "confidence": 0.85,
        "sources": ["Yahoo Finance", "SEC Edgar"]
    }

    decision = CIODecision(**valid_data)
    assert decision.decision == "BUY"
    assert decision.confidence == 0.85

    # Test validation error (invalid decision)
    invalid_data = valid_data.copy()
    invalid_data["decision"] = "YOLO"

    with pytest.raises(ValueError):
        CIODecision(**invalid_data)
