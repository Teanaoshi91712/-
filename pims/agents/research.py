import json
from typing import Optional, Tuple
from sqlalchemy.orm import Session

from pims.engine.llm import ModelAdapter
from pims.schemas.agent_io import ResearchOutput
from pims.database.models import Research, AgentRun, Company

class ResearchAgent:
    """
    Research Agent is responsible for analyzing qualitative data (news, IR, reports)
    and strictly separating Facts, Interpretations, Hypotheses, Unknowns, and Sources.
    """

    SYSTEM_PROMPT = """You are a highly skilled Research Agent for an institutional-grade investment team.
Your sole purpose is to analyze the provided text and strictly extract information into the following distinct categories:
- FACT: Objectively verifiable data points explicitly stated in the text.
- INTERPRETATION: Logical conclusions or subjective analysis derived directly from the facts.
- HYPOTHESIS: Forward-looking predictions or "what if" scenarios based on current interpretations.
- UNKNOWN: Critical pieces of information that are missing or ambiguous in the text, but are necessary for a complete analysis.
- SOURCE: The explicitly stated or implied source(s) of this information within the text. If not stated, mark as "UNKNOWN".

Do not perform numerical calculations (e.g., DCF, CAGR). Focus purely on qualitative and factual extraction.
You must return the response adhering strictly to the JSON schema provided.
"""

    def __init__(self, adapter: ModelAdapter):
        self.adapter = adapter

    def analyze(
        self,
        ticker: str,
        raw_text: str,
        db_session: Optional[Session] = None
    ) -> Tuple[ResearchOutput, Optional[Research]]:
        """
        Analyzes raw text using the LLM adapter and optionally persists it to the database.
        Returns the parsed Pydantic schema and the database entity (if persisted).
        """
        user_prompt = f"Analyze the following information for ticker {ticker}:\n\n{raw_text}"

        # Call the LLM to get structured data
        response = self.adapter.generate(
            system_prompt=self.SYSTEM_PROMPT,
            user_prompt=user_prompt,
            response_schema=ResearchOutput
        )

        # Handle parsed object or fallback parsing (especially useful if MockAdapter was used)
        if response.parsed_object and isinstance(response.parsed_object, ResearchOutput):
            research_output = response.parsed_object
        else:
            try:
                data = json.loads(response.content)
                research_output = ResearchOutput(**data)
            except Exception:
                # Fallback for mock or complete parsing failure
                research_output = ResearchOutput(
                    facts=["Could not parse facts"],
                    interpretations=["Could not parse interpretations"],
                    hypotheses=[],
                    unknowns=["Parsing error"],
                    sources=["System"]
                )

        research_record = None

        # If DB session is provided, persist the results and log the agent run
        if db_session:
            company = db_session.query(Company).filter_by(ticker=ticker).first()
            if company:
                # Store the structured output and the raw response, fulfilling architecture feedback
                research_record = Research(
                    company_id=company.id,
                    facts=research_output.facts,
                    interpretations=research_output.interpretations,
                    hypotheses=research_output.hypotheses,
                    unknowns=research_output.unknowns,
                    raw_response=response.content,
                    source=research_output.sources[0] if research_output.sources else "UNKNOWN",
                    confidence=1.0  # Ideally determined by LLM, but defaulting to 1.0 for simplicity here
                )
                db_session.add(research_record)

            # Log the agent run for cost and performance tracking
            agent_run = AgentRun(
                agent_name="ResearchAgent",
                model=response.model,
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
                estimated_cost=response.estimated_cost,
                latency_ms=response.latency_ms,
                tool_calls=response.tool_calls
            )
            db_session.add(agent_run)
            db_session.commit()

            if research_record:
                db_session.refresh(research_record)

        return research_output, research_record
