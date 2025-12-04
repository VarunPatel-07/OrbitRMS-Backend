from Database.Database import SessionLocal
from sqlalchemy.orm import Session
from SqlModels import Models
from datetime import datetime
from zoneinfo import ZoneInfo


def add_leaves_balance_in_employee(
    organization_id: str, refill_quarterly: bool, max_number_of_leave: int, leave_type_id: str
):
    try:
        db: Session = SessionLocal()

        users = db.query(Models.User).filter(Models.User.organization_id == organization_id).all()

        initial_leave = 0

        if refill_quarterly:
            initial_leave = max_number_of_leave / 4
        else:
            initial_leave = max_number_of_leave

        for user in users:

            leave_balance = Models.LeaveBalance(
                leave_type_id=leave_type_id,
                user_id=user.id,
                available_leaves=initial_leave,
                last_refill_date=datetime.now(ZoneInfo("UTC")),
            )

            db.add(leave_balance)

        db.commit()

    except Exception as e:
        print(f"Critical Error: {str(e)}")

    finally:
        db.close()
