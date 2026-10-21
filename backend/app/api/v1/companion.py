"""Owner-scoped companion configuration, using existing client identity."""
import sqlite3
from fastapi import APIRouter, Depends
from app.api.dependencies import get_client_id
from app.db.connection import get_db
from app.services.companion_service import CompanionPreferences, load_preferences, save_preferences

router = APIRouter(tags=["Companion"])


@router.get("/companion-preferences", response_model=CompanionPreferences)
def get_preferences(client_id: str = Depends(get_client_id), db: sqlite3.Connection = Depends(get_db)):
    return load_preferences(db, client_id)


@router.put("/companion-preferences", response_model=CompanionPreferences)
def put_preferences(payload: CompanionPreferences, client_id: str = Depends(get_client_id), db: sqlite3.Connection = Depends(get_db)):
    return save_preferences(db, client_id, payload)
