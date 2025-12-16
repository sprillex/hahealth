from fastapi import FastAPI
from app import database, models
from app.routers import auth, users, medication, health, webhook, prescribers

# Create DB tables
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="Comprehensive Health Tracker")

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(medication.router)
app.include_router(prescribers.router)
app.include_router(health.router)
app.include_router(webhook.router)

@app.get("/")
def read_root():
    return {"message": "Welcome to the Health Tracker API"}
