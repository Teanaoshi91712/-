from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator

class CIODecision(BaseModel):
    """
    Schema for the CIO Agent's final output as requested in the design.
    """
    ticker: str = Field(..., description="Stock ticker symbol")
    company: str = Field(..., description="Company name")
    decision: str = Field(..., description="BUY, HOLD, WATCH, REDUCE, SELL, NO_ACTION, NEED_MORE_RESEARCH")
    investment_thesis: List[str] = Field(default_factory=list)
    evidence: List[str] = Field(default_factory=list)
    counter_evidence: List[str] = Field(default_factory=list)
    valuation: Dict[str, Any] = Field(default_factory=dict)

    current_price: float = Field(..., description="Current stock price")
    fair_value: Optional[float] = Field(None, description="Estimated fair value")
    expected_return: Optional[float] = Field(None, description="Expected return percentage")
    downside: Optional[float] = Field(None, description="Downside risk percentage")

    risk: Dict[str, Any] = Field(default_factory=dict)
    portfolio_impact: Dict[str, Any] = Field(default_factory=dict)
    recommended_weight: Optional[float] = Field(None, description="Recommended portfolio weight (e.g. 0.03 for 3%)")
    recommended_quantity: Optional[int] = Field(None, description="Recommended number of shares to trade")

    entry_conditions: List[str] = Field(default_factory=list)
    exit_conditions: List[str] = Field(default_factory=list)
    monitoring_conditions: List[str] = Field(default_factory=list)

    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence level between 0 and 1")
    unknowns: List[str] = Field(default_factory=list, description="Things that are unknown and need clarification")
    sources: List[str] = Field(..., description="Data sources used for the decision")

    @field_validator('decision')
    @classmethod
    def valid_decision(cls, v: str) -> str:
        valid_options = ["BUY", "HOLD", "WATCH", "REDUCE", "SELL", "NO_ACTION", "NEED_MORE_RESEARCH"]
        if v.upper() not in valid_options:
            raise ValueError(f"Decision must be one of {valid_options}")
        return v.upper()

class ResearchOutput(BaseModel):
    """
    Schema for the Research Agent's output.
    """
    facts: List[str] = Field(default_factory=list)
    interpretations: List[str] = Field(default_factory=list)
    hypotheses: List[str] = Field(default_factory=list)
    unknowns: List[str] = Field(default_factory=list)
    sources: List[str] = Field(default_factory=list)
