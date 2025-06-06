from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class PileType(str, Enum):
    D = "D"   # 直流
    A = "A"   # 交流


class PileStatus(str, Enum):
    IDLE  = "IDLE"
    BUSY  = "BUSY"
    FAULT = "FAULT"
    PAUSED = "PAUSED"


@dataclass
class Pile:
    pile_id: str
    type: PileType
    max_kw: float
    status: PileStatus = PileStatus.IDLE
    current_req_id: Optional[str] = None
    estimated_end: Optional[datetime] = None


@dataclass
class ChargeRequest:
    req_id: str
    queue_no: str
    user_id: str
    pile_type: PileType
    kwh: float
    generated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class DispatchResult:
    req_id: str
    pile_id: str
    queue_no: str
    start_time: datetime
    estimated_end: datetime
