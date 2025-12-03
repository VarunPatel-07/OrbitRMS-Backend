from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from Database.Database import SessionLocal
from SqlModels import Models


def ping_maintenance_mode_scheduler():
    print("🔄 Scheduler job triggered!")
    print("⏰ Pinging Maintenance Scheduler")

    current_date = datetime.now(ZoneInfo("UTC"))

    db: Session = SessionLocal()

    try:

        scheduled_log = (
            db.query(Models.MaintenanceLog)
            .filter(
                Models.MaintenanceLog.started_at <= current_date,
                Models.MaintenanceLog.ended_at > current_date,
                Models.MaintenanceLog.status == "scheduled",
            )
            .all()
        )

        for log in scheduled_log:
            log.status = "active"

            maintenance_mode = db.query(Models.MaintenanceMode).first()

            if maintenance_mode:
                maintenance_mode.is_active = True
                maintenance_mode.updated_at = current_date
                maintenance_mode.updated_by = log.started_by
                maintenance_mode.message = log.message
                print(f"maintenance mode Is Now Activated")

        active_logs = db.query(Models.MaintenanceLog).filter(
            Models.MaintenanceLog.status == "active", Models.MaintenanceLog.ended_at <= current_date
        )

        for log in active_logs:
            log.status = "completed"
            maintenance_mode = db.query(Models.MaintenanceMode).first()

            if maintenance_mode:
                maintenance_mode.is_active = False
                maintenance_mode.updated_at = current_date
                maintenance_mode.updated_by = log.ended_by

                print(f"maintenance mode Is Now DeActivated")

        db.commit()

    except Exception as e:
        print(f"❌ Error in Scheduler: {e}")
        db.rollback()
    finally:
        db.close()

    print(f"[{current_date}] Maintenance check completed.")
