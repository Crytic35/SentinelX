from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database.session import get_db
from database.models import Merchant

router = APIRouter(prefix="/merchants", tags=["Merchant Security"])

class MerchantCreateRequest(BaseModel):
    id: str
    name: str
    country: str = "US"
    domain: str
    category: str
    trust_score: float = 95.0
    is_verified: bool = True

@router.get("")
def list_merchants(db: Session = Depends(get_db)):
    merchants = db.query(Merchant).all()
    return [
        {
            "id": m.id,
            "name": m.name,
            "country": m.country,
            "domain": m.domain,
            "category": m.category,
            "trust_score": m.trust_score,
            "is_verified": m.is_verified,
            "transaction_count": m.transaction_count
        } for m in merchants
    ]

@router.post("")
def add_or_update_merchant(req: MerchantCreateRequest, db: Session = Depends(get_db)):
    m = db.query(Merchant).filter(Merchant.id == req.id).first()
    if not m:
        m = Merchant(
            id=req.id,
            name=req.name,
            country=req.country,
            domain=req.domain,
            category=req.category,
            trust_score=req.trust_score,
            is_verified=req.is_verified
        )
        db.add(m)
    else:
        m.name = req.name
        m.country = req.country
        m.domain = req.domain
        m.category = req.category
        m.trust_score = req.trust_score
        m.is_verified = req.is_verified
    db.commit()
    return {"status": "SUCCESS", "merchant_id": m.id}

