from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date, datetime
from app import database, models, schemas, auth

router = APIRouter(
    prefix="/api/v1/medical",
    tags=["medical"]
)

# Allergies
@router.post("/allergies", response_model=schemas.AllergyResponse)
def create_allergy(
    allergy: schemas.AllergyCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    db_allergy = models.Allergy(**allergy.model_dump(), user_id=current_user.user_id)
    db.add(db_allergy)
    db.commit()
    db.refresh(db_allergy)
    return db_allergy

@router.put("/allergies/{allergy_id}", response_model=schemas.AllergyResponse)
def update_allergy(
    allergy_id: int,
    allergy: schemas.AllergyCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    db_allergy = db.query(models.Allergy).filter(models.Allergy.allergy_id == allergy_id, models.Allergy.user_id == current_user.user_id).first()
    if not db_allergy:
        raise HTTPException(status_code=404, detail="Allergy not found")

    data = allergy.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(db_allergy, key, value)

    db.commit()
    db.refresh(db_allergy)
    return db_allergy

@router.delete("/allergies/{allergy_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_allergy(
    allergy_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    db_allergy = db.query(models.Allergy).filter(models.Allergy.allergy_id == allergy_id, models.Allergy.user_id == current_user.user_id).first()
    if not db_allergy:
        raise HTTPException(status_code=404, detail="Allergy not found")

    db.delete(db_allergy)
    db.commit()
    return None

@router.get("/allergies", response_model=List[schemas.AllergyResponse])
def get_allergies(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    return db.query(models.Allergy).filter(models.Allergy.user_id == current_user.user_id).all()

# Vaccinations
@router.post("/vaccinations", response_model=schemas.VaccinationResponse)
def log_vaccination(
    vac: schemas.VaccinationCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    # Check if this type already exists, if so, update or add new dose?
    # User might want history. We just log new entry.
    db_vac = models.Vaccination(**vac.model_dump(), user_id=current_user.user_id)
    db.add(db_vac)
    db.commit()
    db.refresh(db_vac)
    return db_vac

@router.get("/vaccinations", response_model=List[schemas.VaccinationResponse])
def get_vaccinations(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    vacs = db.query(models.Vaccination).filter(models.Vaccination.user_id == current_user.user_id).all()

    # Logic for status
    results = []
    today = date.today()

    # We need to process by type to find latest.
    # Group by type
    grouped = {}
    for v in vacs:
        if v.vaccine_type not in grouped:
            grouped[v.vaccine_type] = []
        grouped[v.vaccine_type].append(v)

    # Helper for status logic
    # This loop processes ALL records.
    # But "Reports page" needs current status.
    # The endpoint returns list of all logs.
    # I should add a separate endpoint for "Report Status" or enrich here?
    # I'll enrich here for simplicity, but only "Latest" usually matters for Overdue status.
    # But Shingles needs Dose 1 and Dose 2.

    # Actually, let's just return raw list here, and handle "Report" logic in a specific report endpoint or frontend.
    # But backend logic is requested: "Flu shall not be deemed overdue...".
    # I'll implement a report endpoint: `/api/v1/medical/reports/vaccinations`
    return vacs

@router.get("/reports/vaccinations")
def get_vaccination_report(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    vacs = db.query(models.Vaccination).filter(models.Vaccination.user_id == current_user.user_id).all()

    # Types: Influenza, Covid, Tdap, Shingles Dose 1, Shingles Dose 2

    report = []
    today = date.today()

    # 1. Influenza
    # "Not overdue if administered after August of previous year"
    flu_vacs = [v for v in vacs if "Influenza" in v.vaccine_type or "Flu" in v.vaccine_type]
    flu_status = "Overdue"
    last_flu = None

    if flu_vacs:
        last_flu = max(flu_vacs, key=lambda x: x.date_administered)
        # Check date
        # Cutoff: August 1st of Previous Year relative to Today
        # If today is Jan 2025, prev year is 2024. Cutoff Aug 1, 2024.
        # If today is Nov 2025, prev year is 2024? No, current season is from Aug 2025.
        # "After August of previous year" phrase is ambiguous.
        # Usually implies "Current Season".
        # If Today is Dec 2025. Current Season started Aug 2025.
        # If Last Dose was Sep 2025 -> Good.
        # If Last Dose was Jan 2025 (last season) -> Overdue for this season.

        # Logic: Calculate start of current flu season.
        # If today.month >= 8: Season start is Aug 1, today.year.
        # If today.month < 8: Season start is Aug 1, today.year - 1.

        season_start_year = today.year if today.month >= 8 else today.year - 1
        season_start = date(season_start_year, 8, 1)

        if last_flu.date_administered >= season_start:
            flu_status = "Up to Date"
        else:
            flu_status = "Overdue"

    report.append({
        "vaccine_type": "Influenza",
        "last_date": last_flu.date_administered if last_flu else None,
        "status": flu_status if last_flu else "No Record"
    })

    # 2. Tdap
    # Overdue if not administered in last 10 years.
    tdap_vacs = [v for v in vacs if "Tdap" in v.vaccine_type or "Tetanus" in v.vaccine_type]
    tdap_status = "Overdue"
    last_tdap = None
    next_due = None

    if tdap_vacs:
        last_tdap = max(tdap_vacs, key=lambda x: x.date_administered)
        # 10 years
        # Logic: last_date + 10 years > today?
        # Safe add 10 years
        try:
            due_date = last_tdap.date_administered.replace(year=last_tdap.date_administered.year + 10)
        except ValueError: # Leap year edge case
            due_date = last_tdap.date_administered + timedelta(days=365*10 + 2) # approx

        next_due = due_date
        if due_date >= today:
            tdap_status = "Up to Date"
        else:
            tdap_status = "Overdue"

    report.append({
        "vaccine_type": "Tdap (Tetanus)",
        "last_date": last_tdap.date_administered if last_tdap else None,
        "status": tdap_status if last_tdap else "No Record",
        "next_due": next_due
    })

    # 3. Covid (Rules not specified, assume log only)
    covid_vacs = [v for v in vacs if "Covid" in v.vaccine_type]
    last_covid = max(covid_vacs, key=lambda x: x.date_administered) if covid_vacs else None
    report.append({
        "vaccine_type": "Covid-19",
        "last_date": last_covid.date_administered if last_covid else None,
        "status": "Logged"
    })

    # 4. Shingles
    # Dose 1 and Dose 2
    shingles1 = next((v for v in vacs if "Shingles Dose 1" in v.vaccine_type), None)
    shingles2 = next((v for v in vacs if "Shingles Dose 2" in v.vaccine_type), None)

    report.append({
        "vaccine_type": "Shingles Dose 1",
        "last_date": shingles1.date_administered if shingles1 else None,
        "status": "Completed" if shingles1 else "Pending"
    })

    report.append({
        "vaccine_type": "Shingles Dose 2",
        "last_date": shingles2.date_administered if shingles2 else None,
        "status": "Completed" if shingles2 else "Pending"
    })

    return report
