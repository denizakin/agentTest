from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from web.deps import get_db
from db.coins_repo import CoinInstrumentsRepo

router = APIRouter(prefix="/coins", tags=["coins"])
repo = CoinInstrumentsRepo()


class CoinSummary(BaseModel):
    instrument_id: str
    name: Optional[str] = None
    market_cap_usd: Optional[float] = None
    volume_24h_usd: Optional[float] = None


@router.get("/top", response_model=List[CoinSummary])
def list_top_coins(session: Session = Depends(get_db)) -> List[CoinSummary]:
    """
    List instruments we have candlestick data for, derived from materialized view.

    Placeholder fields for market cap and volume are returned as None.
    """
    instruments = repo.list_instruments(session)
    return [CoinSummary(instrument_id=inst, name=inst) for inst in instruments]
