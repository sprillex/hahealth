from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, time, timedelta, timezone
import pytest
from app.database import get_db, Base
from app import models, services

# Setup In-Memory DB
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture
def test_db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    yield db
    db.close()
    Base.metadata.drop_all(bind=engine)

def test_log_dose_timezone_normalization(test_db):
    """
    Verifies that logging a dose with a non-UTC timezone (e.g., Detroit)
    results in the timestamp being stored converted to UTC.
    """
    # 1. Setup User and Medication
    user = models.User(name="test_tz_user", timezone="UTC")
    test_db.add(user)
    test_db.commit()

    med = models.Medication(user_id=user.user_id, name="TestM", schedule_evening=True, daily_doses=1, current_inventory=10, refills_remaining=0)
    test_db.add(med)
    test_db.commit()

    # 2. Define a Detroit timestamp
    # 20:00 Detroit (-05:00) -> 01:00 UTC (Next Day)
    detroit_tz = timezone(timedelta(hours=-5))
    dt_detroit = datetime(2025, 12, 18, 20, 0, 0, tzinfo=detroit_tz)

    # 3. Log Dose via Service
    service = services.MedicationService()
    log, alert = service.log_dose(test_db, user.user_id, "TestM", dt_detroit)

    assert log is not None

    # 4. Check Stored Timestamp
    # Depending on how SQLAlchemy+SQLite retrieves it:
    # It usually comes back as a naive datetime representing UTC, OR string.
    # We expect it to represent 01:00.

    print(f"Stored Timestamp: {log.timestamp_taken} (Type: {type(log.timestamp_taken)})")

    # The stored value should act like 01:00 (UTC)
    # If it's naive (default for SQLA/SQLite), it should be 01:00.
    # If it's aware, it should be 01:00+00:00.

    # Convert to UTC-aware if naive for comparison
    stored_dt = log.timestamp_taken
    if stored_dt.tzinfo is None:
        stored_dt = stored_dt.replace(tzinfo=timezone.utc)

    expected_dt = datetime(2025, 12, 19, 1, 0, 0, tzinfo=timezone.utc)

    assert stored_dt == expected_dt

    # 5. Check Inventory Decrement (Side check)
    assert med.current_inventory == 9
