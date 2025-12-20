from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, time, timedelta, timezone
import pytest
from app.database import get_db, Base
from app import models, services
from unittest.mock import patch

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

def test_explicit_window_compliance(test_db):
    """
    Verifies that providing an explicit dose_window overrides the time-based calculation
    for compliance matching.
    """
    # 1. Setup User and Medication
    user = models.User(name="window_user", timezone="America/Detroit")
    # Windows: M=6, A=12, E=17, B=21
    test_db.add(user)
    test_db.commit()

    # Medication scheduled for Evening (E)
    med = models.Medication(user_id=user.user_id, name="TestMed", schedule_evening=True, daily_doses=1, current_inventory=10, refills_remaining=0)
    test_db.add(med)
    test_db.commit()

    # 2. Log a Dose with Explicit Window 'E'
    # But take it at 10 AM (Morning Window)
    # If explicit logic works, this counts as Evening compliance.
    # If explicit logic fails, it calculates as Morning (Mismatch).

    # 10 AM Detroit = 15:00 UTC
    dose_time = datetime(2025, 12, 18, 15, 0, 0, tzinfo=timezone.utc)

    service = services.MedicationService()
    log, _ = service.log_dose(test_db, user.user_id, "TestMed", dose_time, dose_window="E")

    assert log.dose_window == "E"

    # 3. Calculate Compliance
    # Mock 'now' to be next day
    mock_now_utc = datetime(2025, 12, 19, 12, 0, tzinfo=timezone.utc)

    with patch('app.services.datetime') as mock_datetime:
        mock_datetime.now.return_value = mock_now_utc
        mock_datetime.combine = datetime.combine
        mock_datetime.min = datetime.min
        mock_datetime.max = datetime.max

        report_service = services.HealthLogService()
        report = report_service.calculate_compliance_report(test_db, user)

        med_entry = next((m for m in report["medications"] if m["name"] == "TestMed"), None)

        # Should be compliant because we forced "E" window even though time was Morning
        assert med_entry["taken"] == 1

def test_explicit_window_fallback(test_db):
    """
    Verifies that if explicit window is missing, it falls back to time calculation.
    """
    user = models.User(name="fallback_user", timezone="UTC")
    test_db.add(user)
    test_db.commit()

    med = models.Medication(user_id=user.user_id, name="TestMed", schedule_morning=True, current_inventory=10, refills_remaining=0)
    test_db.add(med)
    test_db.commit()

    # Log at 07:00 (Morning) without explicit window
    dose_time = datetime(2025, 12, 18, 7, 0, 0, tzinfo=timezone.utc)

    service = services.MedicationService()
    service.log_dose(test_db, user.user_id, "TestMed", dose_time, dose_window=None)

    # Mock report
    mock_now_utc = datetime(2025, 12, 19, 12, 0, tzinfo=timezone.utc)
    with patch('app.services.datetime') as mock_datetime:
        mock_datetime.now.return_value = mock_now_utc
        mock_datetime.combine = datetime.combine
        mock_datetime.min = datetime.min
        mock_datetime.max = datetime.max

        report_service = services.HealthLogService()
        report = report_service.calculate_compliance_report(test_db, user)

        med_entry = next((m for m in report["medications"] if m["name"] == "TestMed"), None)
        assert med_entry["taken"] == 1
