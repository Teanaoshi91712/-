import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from pims.database.core import Base
from pims.database.models import Company, Research, AgentRun
from pims.engine.llm import MockAdapter, ModelResponse
from pims.agents.research import ResearchAgent
from pims.schemas.agent_io import ResearchOutput, ValuationOutput, CIODecision
from pims.agents.valuation import ValuationAgent
from pims.agents.cio import CIOAgent

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

class CustomMockAdapter(MockAdapter):
    """A mock adapter that returns valid JSON to test the parsing logic."""
    def generate(self, system_prompt, user_prompt, response_schema=None):
        content = '{"facts": ["Company A reported 10% growth."], "interpretations": ["Strong performance"], "hypotheses": ["Will grow 15% next year"], "unknowns": ["CEO successor"], "sources": ["Q3 Earnings Call"]}'

        return ModelResponse(
            content=content,
            model=self.model_name,
            input_tokens=100,
            output_tokens=50,
            estimated_cost=0.002,
            latency_ms=150,
            tool_calls=0
        )

def test_research_agent_analyze(db_session):
    # Setup test data
    company = Company(ticker="TEST", name="Test Inc.")
    db_session.add(company)
    db_session.commit()

    # Initialize agent with our custom mock adapter
    adapter = CustomMockAdapter()
    agent = ResearchAgent(adapter=adapter)

    raw_text = "In the Q3 Earnings Call, Company A reported 10% growth..."

    # Run analysis
    research_output, research_record = agent.analyze(ticker="TEST", raw_text=raw_text, db_session=db_session)

    # Assert schema parsed correctly
    assert isinstance(research_output, ResearchOutput)
    assert len(research_output.facts) == 1
    assert "10% growth" in research_output.facts[0]

    # Assert DB record created
    assert research_record is not None
    assert research_record.company_id == company.id
    assert research_record.raw_response is not None

    # Assert AgentRun logged
    run_log = db_session.query(AgentRun).filter_by(agent_name="ResearchAgent").first()
    assert run_log is not None
    assert run_log.input_tokens == 100
    assert run_log.estimated_cost == 0.002

class CustomValuationMockAdapter(MockAdapter):
    """A mock adapter that returns valid JSON for ValuationOutput to test parsing."""
    def generate(self, system_prompt, user_prompt, response_schema=None):
        content = '{"is_undervalued": "YES", "historical_context": "Trading below 5yr average", "peer_context": "Cheaper than MSFT", "market_expectations": "Low growth priced in"}'

        return ModelResponse(
            content=content,
            model=self.model_name,
            input_tokens=150,
            output_tokens=60,
            estimated_cost=0.003,
            latency_ms=200,
            tool_calls=0
        )

def test_valuation_agent_analyze(db_session):
    # Setup test data
    company = db_session.query(Company).filter_by(ticker="TEST").first()
    if not company:
        company = Company(ticker="TEST", name="Test Inc.")
        db_session.add(company)
        db_session.commit()

    # Initialize agent with custom mock adapter
    adapter = CustomValuationMockAdapter()
    agent = ValuationAgent(adapter=adapter)

    metrics = {"per": 12.5, "pbr": 1.5, "roe": 15.0}
    context_text = "The sector average PER is 20.0."

    # Run analysis
    valuation_output, valuation_record = agent.analyze(
        ticker="TEST",
        metrics=metrics,
        context_text=context_text,
        db_session=db_session
    )

    # Assert schema parsed correctly
    assert isinstance(valuation_output, ValuationOutput)
    assert valuation_output.is_undervalued == "YES"
    assert "5yr average" in valuation_output.historical_context

    # Assert DB record created
    assert valuation_record is not None
    assert valuation_record.company_id == company.id
    assert valuation_record.per == 12.5
    assert valuation_record.raw_response is not None

    # Assert AgentRun logged
    run_log = db_session.query(AgentRun).filter_by(agent_name="ValuationAgent").first()
    assert run_log is not None
    assert run_log.input_tokens == 150

class CustomCIOMockAdapter(MockAdapter):
    """A mock adapter that returns valid JSON for CIODecision to test parsing."""
    def generate(self, system_prompt, user_prompt, response_schema=None):
        content = """
        {
            "ticker": "TEST",
            "company": "Test Inc.",
            "decision": "BUY",
            "investment_thesis": ["Strong growth and cheap valuation."],
            "evidence": ["Revenue up 10%"],
            "counter_evidence": ["Macro risks"],
            "valuation": {"method": "DCF", "implied_price": 180},
            "current_price": 150.0,
            "fair_value": 180.0,
            "expected_return": 0.20,
            "downside": 0.10,
            "risk": {"volatility": "high"},
            "portfolio_impact": {"concentration": "acceptable"},
            "recommended_weight": 0.05,
            "recommended_quantity": 100,
            "entry_conditions": ["Price below 155"],
            "exit_conditions": ["Price hits 180"],
            "monitoring_conditions": ["Watch Q4 earnings"],
            "confidence": 0.85,
            "unknowns": ["New competitor product"],
            "sources": ["Research Team", "Valuation Team"]
        }
        """

        return ModelResponse(
            content=content,
            model=self.model_name,
            input_tokens=500,
            output_tokens=300,
            estimated_cost=0.015,
            latency_ms=800,
            tool_calls=0
        )

def test_cio_agent_analyze(db_session):
    # Setup test data
    company = db_session.query(Company).filter_by(ticker="TEST").first()
    if not company:
        company = Company(ticker="TEST", name="Test Inc.")
        db_session.add(company)
        db_session.commit()

    # Initialize agent with custom mock adapter
    adapter = CustomCIOMockAdapter()
    agent = CIOAgent(adapter=adapter)

    research_ctx = "Facts: 10% growth. Unknowns: succession."
    valuation_ctx = "Undervalued based on 5yr average."
    portfolio_ctx = "Current cash: 50%."

    # Run analysis
    cio_output, decision_record = agent.analyze(
        ticker="TEST",
        company_name="Test Inc.",
        current_price=150.0,
        research_context=research_ctx,
        valuation_context=valuation_ctx,
        portfolio_context=portfolio_ctx,
        db_session=db_session
    )

    # Assert schema parsed correctly
    assert isinstance(cio_output, CIODecision)
    assert cio_output.decision == "BUY"
    assert cio_output.confidence == 0.85
    assert cio_output.fair_value == 180.0

    # Assert DB record created
    assert decision_record is not None
    assert decision_record.company_id == company.id
    assert decision_record.decision == "BUY"
    assert decision_record.confidence == 0.85
    assert decision_record.raw_response is not None

    # Assert AgentRun logged
    run_log = db_session.query(AgentRun).filter_by(agent_name="CIOAgent").first()
    assert run_log is not None
    assert run_log.input_tokens == 500
