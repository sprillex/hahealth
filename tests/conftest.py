import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import Base, get_db
import os

@pytest.fixture(scope="module")
def db_session_factory(request):
    """
    Creates a new database for the test module and returns a SessionLocal factory.
    Scope is module: one DB per test file.
    """
    db_filename = f"./test_{request.module.__name__}.db"
    db_url = f"sqlite:///{db_filename}"

    engine = create_engine(
        db_url, connect_args={"check_same_thread": False}
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Create tables
    Base.metadata.create_all(bind=engine)

    yield SessionLocal

    # Teardown
    Base.metadata.drop_all(bind=engine)
    engine.dispose()

    if os.path.exists(db_filename):
        os.remove(db_filename)

@pytest.fixture(scope="module")
def client(db_session_factory):
    """
    TestClient that uses the module-scoped database.
    """
    def override():
        try:
            db = db_session_factory()
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override

    client = TestClient(app)
    yield client

    app.dependency_overrides.pop(get_db, None)

@pytest.fixture(scope="function")
def session(db_session_factory):
    """
    Provides a new database session for a test function.
    Rollback is not implemented here (data persists in module DB),
    so tests depend on previous state or must clean up if needed.
    """
    db = db_session_factory()
    try:
        yield db
    finally:
        db.close()
