import json
from typing import Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session

from pims.engine.llm import ModelAdapter
from pims.schemas.agent_io import ValuationOutput
from pims.database.models import Valuation, AgentRun, Company

class ValuationAgent:
    """
    Valuation Agent handles the qualitative interpretation of quantitative metrics.
    As per design, it DOES NOT calculate metrics like PER/PBR; those are supplied
    as inputs from the QuantEngine. It only interprets them based on context.
    """

    SYSTEM_PROMPT = """You are a highly skilled Valuation Analyst for an institutional-grade investment team.
Your task is to interpret the provided quantitative financial metrics (PER, PBR, ROE, etc.) and qualitative context.
You MUST NOT perform calculations. Focus purely on interpreting what the provided numbers mean in the context of:
1. Historical context (is the current multiple high/low historically?)
2. Peer context (how does it compare to industry peers?)
3. Market expectations (what growth rate or risk is baked into this price?)

Finally, provide a definitive classification on whether the asset appears undervalued.
You must return your analysis strictly adhering to the requested JSON schema.
"""

    def __init__(self, adapter: ModelAdapter):
        self.adapter = adapter

    def analyze(
        self,
        ticker: str,
        metrics: Dict[str, float],
        context_text: str,
        db_session: Optional[Session] = None
    ) -> Tuple[ValuationOutput, Optional[Valuation]]:
        """
        Interprets quantitative metrics based on qualitative context using the LLM adapter.
        Optionally persists the interpretation to the database.

        Args:
            ticker: The stock ticker.
            metrics: A dictionary of pre-calculated metrics (e.g. {'per': 15.0, 'pbr': 2.0})
            context_text: Qualitative context describing historical/peer norms.
            db_session: Optional DB session to save results.
        """

        # Format the metrics clearly so the LLM doesn't try to calculate them
        metrics_str = "\n".join([f"- {k.upper()}: {v}" for k, v in metrics.items()])

        user_prompt = f"""Analyze the valuation for {ticker}.

PRE-CALCULATED METRICS:
{metrics_str}

CONTEXT (Historical & Peers):
{context_text}
"""

        # Call the LLM to get structured data
        response = self.adapter.generate(
            system_prompt=self.SYSTEM_PROMPT,
            user_prompt=user_prompt,
            response_schema=ValuationOutput
        )

        # Handle parsed object or fallback parsing
        if response.parsed_object and isinstance(response.parsed_object, ValuationOutput):
            valuation_output = response.parsed_object
        else:
            try:
                data = json.loads(response.content)
                valuation_output = ValuationOutput(**data)
            except Exception:
                # Fallback for mock or complete parsing failure
                valuation_output = ValuationOutput(
                    is_undervalued="NEUTRAL",
                    historical_context="Parsing error in historical context.",
                    peer_context="Parsing error in peer context.",
                    market_expectations="Parsing error in market expectations."
                )

        valuation_record = None

        # If DB session is provided, persist the results and log the agent run
        if db_session:
            company = db_session.query(Company).filter_by(ticker=ticker).first()
            if company:
                valuation_record = Valuation(
                    company_id=company.id,
                    per=metrics.get('per'),
                    pbr=metrics.get('pbr'),
                    roe=metrics.get('roe'),
                    current_price=metrics.get('current_price'),
                    is_undervalued=valuation_output.is_undervalued,
                    historical_context=valuation_output.historical_context,
                    peer_context=valuation_output.peer_context,
                    market_expectations=valuation_output.market_expectations,
                    raw_response=response.content
                )
                db_session.add(valuation_record)

            # Log the agent run for cost and performance tracking
            agent_run = AgentRun(
                agent_name="ValuationAgent",
                model=response.model,
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
                estimated_cost=response.estimated_cost,
                latency_ms=response.latency_ms,
                tool_calls=response.tool_calls
            )
            db_session.add(agent_run)
            db_session.commit()

            if valuation_record:
                db_session.refresh(valuation_record)

        return valuation_output, valuation_record
