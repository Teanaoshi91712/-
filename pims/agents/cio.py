import json
from typing import Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session

from pims.engine.llm import ModelAdapter
from pims.schemas.agent_io import CIODecision
from pims.database.models import Decision, AgentRun, Company

class CIOAgent:
    """
    The CIO (Chief Investment Officer) Agent is the orchestrator and final decision maker.
    It takes inputs from Research and Valuation agents (as well as quantitative data),
    synthesizes them, resolves contradictions, and outputs a structured CIODecision.
    The output is a *recommendation*. Humans make the actual final trade decision.
    """

    SYSTEM_PROMPT = """You are the Chief Investment Officer (CIO) for an institutional-grade investment team.
Your responsibility is to review the quantitative data and the qualitative reports from the Research and Valuation teams, synthesize them, and make a final investment recommendation.

Follow these strict guidelines:
1. Synthesize the core investment thesis, supporting evidence, and counter-evidence.
2. Resolve any contradictions between the Research and Valuation reports.
3. Determine a concrete recommendation: BUY, HOLD, WATCH, REDUCE, SELL, NO_ACTION, or NEED_MORE_RESEARCH.
4. Estimate fair value, expected return, and downside risk based on the provided inputs (do not hallucinate independent calculations).
5. Specify actionable entry/exit and monitoring conditions.
6. Provide a confidence score (0.0 to 1.0) and clearly list any UNKNOWNS and SOURCES.

You must return your analysis strictly adhering to the requested JSON schema.
"""

    def __init__(self, adapter: ModelAdapter):
        self.adapter = adapter

    def analyze(
        self,
        ticker: str,
        company_name: str,
        current_price: float,
        research_context: str,
        valuation_context: str,
        portfolio_context: str,
        db_session: Optional[Session] = None
    ) -> Tuple[CIODecision, Optional[Decision]]:
        """
        Synthesizes research, valuation, and portfolio context into a final CIO Decision.
        """
        user_prompt = f"""Target Asset: {company_name} ({ticker})
Current Price: {current_price}

=== RESEARCH TEAM REPORT ===
{research_context}

=== VALUATION TEAM REPORT ===
{valuation_context}

=== PORTFOLIO RISK CONTEXT ===
{portfolio_context}

Based on the above reports, please provide your final CIO recommendation.
"""

        # Call the LLM to get structured data
        response = self.adapter.generate(
            system_prompt=self.SYSTEM_PROMPT,
            user_prompt=user_prompt,
            response_schema=CIODecision
        )

        # Handle parsed object or fallback parsing
        if response.parsed_object and isinstance(response.parsed_object, CIODecision):
            cio_output = response.parsed_object
        else:
            try:
                data = json.loads(response.content)
                cio_output = CIODecision(**data)
            except Exception:
                # Fallback for mock or complete parsing failure, triggering a safe state
                cio_output = CIODecision(
                    ticker=ticker,
                    company=company_name,
                    decision="NEED_MORE_RESEARCH",
                    current_price=current_price,
                    confidence=0.0,
                    unknowns=["Parsing error. Failed to generate a valid CIO recommendation."],
                    sources=["System"]
                )

        decision_record = None

        # Persist the results and log the agent run
        if db_session:
            company = db_session.query(Company).filter_by(ticker=ticker).first()
            if company:
                decision_record = Decision(
                    company_id=company.id,
                    decision=cio_output.decision,
                    confidence=cio_output.confidence,
                    investment_thesis=cio_output.investment_thesis,
                    evidence=cio_output.evidence,
                    counter_evidence=cio_output.counter_evidence,
                    fair_value=cio_output.fair_value,
                    expected_return=cio_output.expected_return,
                    downside=cio_output.downside,
                    recommended_weight=cio_output.recommended_weight,
                    recommended_quantity=cio_output.recommended_quantity,
                    entry_conditions=cio_output.entry_conditions,
                    exit_conditions=cio_output.exit_conditions,
                    monitoring_conditions=cio_output.monitoring_conditions,
                    unknowns=cio_output.unknowns,
                    sources=cio_output.sources,
                    raw_response=response.content
                )
                db_session.add(decision_record)

            # Log the agent run for cost and performance tracking
            agent_run = AgentRun(
                agent_name="CIOAgent",
                model=response.model,
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
                estimated_cost=response.estimated_cost,
                latency_ms=response.latency_ms,
                tool_calls=response.tool_calls
            )
            db_session.add(agent_run)
            db_session.commit()

            if decision_record:
                db_session.refresh(decision_record)

        return cio_output, decision_record
