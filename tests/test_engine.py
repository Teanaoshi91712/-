import pytest
from pims.engine.quant import QuantEngine
from pims.engine.llm import MockAdapter, ModelResponse
from pims.engine.planner import TradePlanner
from pims.database.models import Decision, Company, TradePlan
from pims.database.core import Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

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

def test_quant_per():
    assert QuantEngine.calculate_per(150.0, 10.0) == 15.0
    assert QuantEngine.calculate_per(150.0, 0.0) is None
    assert QuantEngine.calculate_per(150.0, -5.0) is None

def test_quant_pbr():
    assert QuantEngine.calculate_pbr(50.0, 25.0) == 2.0
    assert QuantEngine.calculate_pbr(50.0, 0.0) is None

def test_quant_roe():
    assert QuantEngine.calculate_roe(100.0, 1000.0) == 10.0
    assert QuantEngine.calculate_roe(-50.0, 1000.0) == -5.0
    assert QuantEngine.calculate_roe(100.0, 0.0) is None

def test_quant_roic():
    assert QuantEngine.calculate_roic(150.0, 1500.0) == 10.0
    assert QuantEngine.calculate_roic(150.0, 0) is None

def test_quant_fcf():
    assert QuantEngine.calculate_fcf(500.0, 150.0) == 350.0
    assert QuantEngine.calculate_fcf(500.0, -150.0) == 350.0 # Tests absolute value logic

def test_quant_portfolio_weights():
    positions = {"AAPL": 1000.0, "MSFT": 2000.0}
    cash = 1000.0

    weights = QuantEngine.calculate_portfolio_weights(positions, cash)

    assert weights["AAPL"] == 0.25
    assert weights["MSFT"] == 0.50
    assert weights["CASH"] == 0.25

    # Test empty portfolio
    weights_empty = QuantEngine.calculate_portfolio_weights({}, 0)
    assert weights_empty == {}

def test_quant_drawdown():
    assert QuantEngine.calculate_drawdown(1000.0, 900.0) == 10.0
    assert QuantEngine.calculate_drawdown(1000.0, 1000.0) == 0.0
    assert QuantEngine.calculate_drawdown(1000.0, 1100.0) == 0.0 # Price is higher than peak
    assert QuantEngine.calculate_drawdown(0.0, 100.0) == 0.0

def test_mock_llm_adapter():
    adapter = MockAdapter()
    response = adapter.generate(
        system_prompt="You are a helpful assistant.",
        user_prompt="Analyze AAPL"
    )

    assert isinstance(response, ModelResponse)
    assert response.model == "mock-model-fast"
    assert response.input_tokens > 0
    assert response.output_tokens > 0
    assert response.estimated_cost > 0.0
    assert response.latency_ms > 0

def test_trade_planner(db_session):
    # Setup test data
    company = Company(ticker="TESTPLAN", name="Plan Inc.")
    db_session.add(company)
    db_session.commit()

    decision = Decision(
        company_id=company.id,
        decision="BUY",
        confidence=0.9,
        recommended_quantity=50,
        entry_conditions=["Under $100"]
    )
    db_session.add(decision)
    db_session.commit()

    # Generate Plan
    plan = TradePlanner.generate_plan(db_session, decision.id)

    assert plan.ticker == "TESTPLAN"
    assert plan.decision == "BUY"
    assert plan.recommended_quantity == 50
    assert plan.status == "PENDING"
    assert plan.preferred_order_type == "LIMIT" # Because entry conditions exist

    # Test non-actionable decision
    decision_hold = Decision(
        company_id=company.id,
        decision="HOLD",
        confidence=0.9
    )
    db_session.add(decision_hold)
    db_session.commit()

    plan_hold = TradePlanner.generate_plan(db_session, decision_hold.id)
    assert plan_hold.status == "CANCELLED"
