import sys
import argparse
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app import models, auth

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_user(name, password, weight, height, unit_system):
    db = SessionLocal()
    try:
        existing_user = db.query(models.User).filter(models.User.name == name).first()
        if existing_user:
            print(f"User '{name}' already exists.")
            return

        weight_kg = weight
        height_cm = height

        if unit_system.upper() == "IMPERIAL":
            # Convert lbs to kg
            weight_kg = weight * 0.453592
            # Convert inches to cm
            height_cm = height * 2.54

        hashed_password = auth.get_password_hash(password)
        new_user = models.User(
            name=name,
            weight_kg=weight_kg,
            height_cm=height_cm,
            password_hash=hashed_password,
            unit_system=unit_system.upper()
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        print(f"User '{name}' created successfully with ID: {new_user.user_id}")
        if unit_system.upper() == "IMPERIAL":
             print(f"Stored as Metric: {weight_kg:.2f} kg, {height_cm:.2f} cm")
    finally:
        db.close()

def reset_password(user_id, new_password):
    db = SessionLocal()
    try:
        user = db.query(models.User).filter(models.User.user_id == user_id).first()
        if not user:
            print(f"User ID {user_id} not found.")
            return

        user.password_hash = auth.get_password_hash(new_password)
        db.commit()
        print(f"Password reset for user {user.name} (ID: {user_id}).")
    finally:
        db.close()

def create_api_key(user_id, name):
    db = SessionLocal()
    try:
        user = db.query(models.User).filter(models.User.user_id == user_id).first()
        if not user:
            print(f"User ID {user_id} not found.")
            return

        raw_key = auth.generate_api_key()
        hashed_key = auth.hash_api_key(raw_key)

        new_key = models.APIKey(
            user_id=user_id,
            name=name,
            hashed_key=hashed_key,
            is_active=True
        )
        db.add(new_key)
        db.commit()
        print(f"API Key created for user {user.name}.")
        print(f"Key Name: {name}")
        print(f"SECRET KEY (SAVE THIS NOW, IT WILL NOT BE SHOWN AGAIN): {raw_key}")
    finally:
        db.close()

def revoke_api_key(key_id):
    db = SessionLocal()
    try:
        key = db.query(models.APIKey).filter(models.APIKey.key_id == key_id).first()
        if not key:
            print(f"Key ID {key_id} not found.")
            return

        key.is_active = False
        db.commit()
        print(f"API Key ID {key_id} revoked.")
    finally:
        db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Health App Admin CLI")
    subparsers = parser.add_subparsers(dest="command")

    # Create User
    parser_user = subparsers.add_parser("create-user")
    parser_user.add_argument("--name", type=str, required=True)
    parser_user.add_argument("--password", type=str, required=True)
    parser_user.add_argument("--weight", type=float, required=True, help="Weight (kg or lbs)")
    parser_user.add_argument("--height", type=float, required=True, help="Height (cm or in)")
    parser_user.add_argument("--unit-system", type=str, choices=["metric", "imperial"], default="metric", help="Unit system (metric/imperial)")

    # Reset Password
    parser_reset = subparsers.add_parser("reset-password")
    parser_reset.add_argument("--user-id", type=int, required=True)
    parser_reset.add_argument("--password", type=str, required=True)

    # Create API Key
    parser_create = subparsers.add_parser("create-apikey")
    parser_create.add_argument("--user-id", type=int, required=True)
    parser_create.add_argument("--name", type=str, required=True)

    # Revoke API Key
    parser_revoke = subparsers.add_parser("revoke-apikey")
    parser_revoke.add_argument("--key-id", type=int, required=True)

    args = parser.parse_args()

    if args.command == "create-user":
        create_user(args.name, args.password, args.weight, args.height, args.unit_system)
    elif args.command == "reset-password":
        reset_password(args.user_id, args.password)
    elif args.command == "create-apikey":
        create_api_key(args.user_id, args.name)
    elif args.command == "revoke-apikey":
        revoke_api_key(args.key_id)
    else:
        parser.print_help()
