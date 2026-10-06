from sqlalchemy.orm import Session
from pims.database.models import Decision, TradePlan, Company

class TradePlanner:
    """
    TradePlanner is a Python-only rule engine that takes a CIO Decision
    and creates a concrete, executable TradePlan. It does not use LLMs,
    ensuring deterministic translation of decisions to orders.
    """

    @staticmethod
    def generate_plan(db_session: Session, decision_id: int) -> TradePlan:
        """
        Generates a TradePlan based on a CIO Decision ID.
        """
        decision = db_session.query(Decision).filter(Decision.id == decision_id).first()
        if not decision:
            raise ValueError(f"Decision with ID {decision_id} not found.")

        company = db_session.query(Company).filter(Company.id == decision.company_id).first()
        if not company:
            raise ValueError("Associated company not found.")

        # Do not generate trade plans for non-actionable decisions
        if decision.decision in ["HOLD", "WATCH", "NO_ACTION", "NEED_MORE_RESEARCH"]:
            status = "CANCELLED" # Effectively no trade needed
            reason = f"Decision was {decision.decision}. No active trading required."
        else:
            status = "PENDING"
            reason = f"CIO confidence: {decision.confidence}. " + \
                     (decision.investment_thesis[0] if decision.investment_thesis else "No thesis provided.")

        entry_range = None
        if decision.entry_conditions:
            entry_range = ", ".join(decision.entry_conditions)

        plan = TradePlan(
            ticker=company.ticker,
            decision=decision.decision,
            recommended_weight=decision.recommended_weight,
            recommended_quantity=decision.recommended_quantity,
            entry_range=entry_range,
            preferred_order_type="LIMIT" if entry_range else "MARKET",
            reason=reason,
            status=status
        )

        db_session.add(plan)
        db_session.commit()
        db_session.refresh(plan)

        return plan
