from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.openapi.docs import get_swagger_ui_html
from app import database, models
from app.routers import auth, users, medication, health, webhook, prescribers, admin, nutrition
import os

# Create DB tables
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(
    title="Comprehensive Health Tracker",
    docs_url=None
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(medication.router)
app.include_router(prescribers.router)
app.include_router(health.router)
app.include_router(webhook.router)
app.include_router(admin.router)
app.include_router(nutrition.router)

# Mount Static Files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=app.title + " - Swagger UI",
        oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-themes@3.0.0/themes/3.x/theme-monokai.css"
    )

@app.get("/")
async def read_index():
    return FileResponse('app/static/index.html')
