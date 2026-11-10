from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database.session import get_db
from database.models import Tool

router = APIRouter(prefix="/tools", tags=["Tool Trust Registry & MCP"])

@router.get("")
def list_tools(db: Session = Depends(get_db)):
    tools = db.query(Tool).all()
    return [
        {
            "id": t.id,
            "name": t.name,
            "owner": t.owner,
            "version": t.version,
            "capabilities": t.capabilities,
            "trust_state": t.trust_state,
            "permissions": t.permissions,
            "last_verification": t.last_verification.isoformat() if t.last_verification else None
        } for t in tools
    ]

