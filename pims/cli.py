import argparse
from datetime import datetime
from pims.database.core import SessionLocal
from pims.database.models import TradePlan, ExecutionResult

def prompt_execution_result(plan: TradePlan) -> bool:
    """
    Displays a pending trade plan to the user and asks for execution details.
    """
    print("\n" + "="*50)
    print("🚨 ACTION REQUIRED: PENDING TRADE PLAN 🚨")
    print("="*50)
    print(f"Ticker:        {plan.ticker}")
    print(f"Decision:      {plan.decision}")
    print(f"Quantity:      {plan.recommended_quantity}")
    print(f"Order Type:    {plan.preferred_order_type}")
    print(f"Entry Range:   {plan.entry_range}")
    print(f"Reason:        {plan.reason}")
    print("="*50)

    executed_input = input("Did you execute this order in your brokerage? (y/n): ").strip().lower()

    if executed_input == 'y':
        try:
            qty_input = int(input("Enter Executed Quantity: ").strip())
            price_input = float(input("Enter Executed Price: ").strip())
        except ValueError:
            print("Invalid input. Please enter numbers for quantity and price.")
            return False

        with SessionLocal() as db:
            result = ExecutionResult(
                trade_plan_id=plan.id,
                executed="True",
                executed_quantity=qty_input,
                executed_price=price_input,
                executed_at=datetime.utcnow(),
                recorded_by="HUMAN"
            )
            # Update the plan status
            db_plan = db.query(TradePlan).filter(TradePlan.id == plan.id).first()
            db_plan.status = "EXECUTED"

            db.add(result)
            db.commit()

        print("✅ Execution result recorded successfully.")
        return True

    elif executed_input == 'n':
        with SessionLocal() as db:
            db_plan = db.query(TradePlan).filter(TradePlan.id == plan.id).first()
            db_plan.status = "CANCELLED"
            db.commit()

        print("🚫 Trade plan marked as cancelled.")
        return True

    else:
        print("Invalid option.")
        return False

def main():
    print("Starting PIMS Human Execution Interface...")
    with SessionLocal() as db:
        pending_plans = db.query(TradePlan).filter(TradePlan.status == "PENDING").all()

    if not pending_plans:
        print("No pending trade plans to execute.")
        return

    print(f"Found {len(pending_plans)} pending trade plan(s).")

    for plan in pending_plans:
        success = False
        while not success:
            success = prompt_execution_result(plan)

if __name__ == "__main__":
    main()
