import os
from pims.database.core import Base, engine, SessionLocal
from pims.database.models import Company
from pims.engine.llm import get_llm_adapter
from pims.agents.research import ResearchAgent
from pims.agents.valuation import ValuationAgent
from pims.agents.cio import CIOAgent
from pims.engine.planner import TradePlanner
from pims.cli import main as cli_main

def setup_database():
    """Initializes the SQLite database and seed data."""
    print("Initializing Database...")
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        company = db.query(Company).filter_by(ticker="AAPL").first()
        if not company:
            company = Company(ticker="AAPL", name="Apple Inc.", sector="Technology", description="Consumer electronics giant.")
            db.add(company)
            db.commit()
            print("Seeded mock company: AAPL")

def run_pipeline():
    """Executes the AI Agent pipeline."""
    ticker = "AAPL"

    # 1. Gather Mock Data
    raw_news = "Apple reported Q3 earnings today with a 5% revenue increase driven by strong iPhone sales. However, analysts are concerned about slowing growth in the services sector and new regulatory fines in Europe."
    metrics = {"per": 30.5, "pbr": 42.1, "roe": 150.0, "current_price": 175.50}
    valuation_context = "AAPL typically trades at a premium. The 5-year average PER is 25.0. It is currently higher than its historical average."
    portfolio_context = "Current portfolio has 10% exposure to AAPL. Cash balance is $50,000. We want to avoid exceeding 15% concentration in a single stock."

    adapter = get_llm_adapter()

    with SessionLocal() as db:
        print(f"\n--- [1/4] Research Agent Analyzing {ticker} ---")
        research_agent = ResearchAgent(adapter)
        research_output, _ = research_agent.analyze(ticker, raw_news, db)
        print(f"Facts Extracted: {len(research_output.facts)}")

        print(f"\n--- [2/4] Valuation Agent Analyzing {ticker} ---")
        val_agent = ValuationAgent(adapter)
        val_output, _ = val_agent.analyze(ticker, metrics, valuation_context, db)
        print(f"Is Undervalued?: {val_output.is_undervalued}")

        print(f"\n--- [3/4] CIO Agent Synthesizing Decision for {ticker} ---")
        cio_agent = CIOAgent(adapter)

        research_ctx = f"Facts: {research_output.facts}. Interpretations: {research_output.interpretations}. Unknowns: {research_output.unknowns}"
        val_ctx = f"Undervalued: {val_output.is_undervalued}. Historical context: {val_output.historical_context}"

        cio_output, decision_record = cio_agent.analyze(
            ticker=ticker,
            company_name="Apple Inc.",
            current_price=metrics["current_price"],
            research_context=research_ctx,
            valuation_context=val_ctx,
            portfolio_context=portfolio_context,
            db_session=db
        )
        print(f"CIO Decision: {cio_output.decision} (Confidence: {cio_output.confidence})")

        print(f"\n--- [4/4] Trade Planner Generating Order ---")
        if decision_record:
            plan = TradePlanner.generate_plan(db, decision_record.id)
            print(f"Generated Trade Plan: Status={plan.status}, Qty={plan.recommended_quantity}, Type={plan.preferred_order_type}")
        else:
            print("No decision record created. Cannot plan trade.")

def main():
    print("="*50)
    print("PIMS E2E Pipeline Demonstration")
    print("="*50)

    setup_database()
    run_pipeline()

    print("\n" + "="*50)
    print("Launching Human Execution CLI")
    print("="*50)
    cli_main()

if __name__ == "__main__":
    main()
