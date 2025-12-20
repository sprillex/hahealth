from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, time, timedelta, timezone
import pytest
from app.main import app
from app.database import get_db, Base
from app import models, services
from unittest.mock import patch

# Setup In-Memory DB for Tests
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture
def test_db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    yield db
    db.close()
    Base.metadata.drop_all(bind=engine)

def test_compliance_fix_verification(test_db):
    """
    Verifies that a dose taken at 8PM Detroit time (01:00 UTC next day)
    is included in the report for the day it was taken locally.
    """
    # Setup
    user = models.User(name="detroit_user", timezone="America/Detroit")
    test_db.add(user)
    test_db.commit()

    med = models.Medication(user_id=user.user_id, name="TestM", schedule_evening=True)
    test_db.add(med)
    test_db.commit()

    # Target Date: Dec 18, 2025
    target_date = datetime(2025, 12, 18).date()

    # Log Dose: 20:00 Detroit = 01:00 UTC (Dec 19)
    utc_log_time = datetime(2025, 12, 19, 1, 0, tzinfo=timezone.utc)

    log = models.MedDoseLog(user_id=user.user_id, med_id=med.med_id, timestamp_taken=utc_log_time)
    test_db.add(log)
    test_db.commit()

    # Mock 'now' to be Dec 19, 12:00 Detroit (so 'Yesterday' is Dec 18)
    mock_now_utc = datetime(2025, 12, 19, 17, 0, tzinfo=timezone.utc)

    with patch('app.services.datetime') as mock_datetime:
        mock_datetime.now.return_value = mock_now_utc
        mock_datetime.combine = datetime.combine # Keep original methods
        mock_datetime.min = datetime.min
        mock_datetime.max = datetime.max
        # Side effect for utcnow if used (service uses now(timezone.utc))

        service = services.HealthLogService()
        report = service.calculate_compliance_report(test_db, user)

        # Check Compliance
        med_entry = next((m for m in report["medications"] if m["name"] == "TestM"), None)
        assert med_entry is not None

        # Ensure the dose is counted
        print(f"Report: {med_entry}")
        assert med_entry["taken"] >= 1
