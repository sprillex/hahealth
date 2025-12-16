from app import auth, models, database
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient
from app.main import app

def test_repro():
    # 1. Setup DB
    db = database.SessionLocal()

    username = "repro_user"
    password = "secure_password_123"

    # Cleanup
    existing = db.query(models.User).filter(models.User.name == username).first()
    if existing:
        db.delete(existing)
        db.commit()

    # 2. Create User (mimic CLI)
    print(f"Creating user {username}...")
    hashed = auth.get_password_hash(password)
    print(f"Hash generated: {hashed}")

    user = models.User(
        name=username,
        password_hash=hashed,
        weight_kg=70,
        height_cm=170,
        unit_system="METRIC"
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    print(f"User created with ID {user.user_id}")

    # 3. Verify Password directly
    print("Verifying password directly...")
    is_valid = auth.verify_password(password, user.password_hash)
    print(f"Direct Verification result: {is_valid}")

    if not is_valid:
        print("FAIL: Direct verification failed!")

    # 4. Verify via API
    print("Verifying via API...")
    client = TestClient(app)
    response = client.post(
        "/auth/token",
        data={"username": username, "password": password}
    )
    print(f"API Response Status: {response.status_code}")
    print(f"API Response Body: {response.json()}")

    if response.status_code == 200:
        print("SUCCESS: Login worked")
    else:
        print("FAIL: Login failed")

if __name__ == "__main__":
    test_repro()
