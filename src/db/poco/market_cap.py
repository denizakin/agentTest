from __future__ import annotations

from sqlalchemy import Column, DateTime, Index, Numeric, String

from db.base import Base


class MarketCap(Base):
    __tablename__ = "cmc_market_caps"

    # Snapshot time of the CMC fetch (UTC).
    snapshot_ts = Column(DateTime(timezone=True), primary_key=True)
    # Asset symbol, e.g., BTC or ETH.
    symbol = Column(String(30), primary_key=True)
    # Market cap in USD at snapshot time.
    market_cap_usd = Column(Numeric(30, 4), nullable=False)

    __table_args__ = (Index("ix_cmc_market_caps_symbol", "symbol"),)
