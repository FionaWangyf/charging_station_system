from dataclasses import dataclass
from datetime import datetime, time
from typing import List, Optional, Dict
from enum import Enum

class ChargingMode(Enum):
    FAST = "fast"
    TRICKLE = "trickle"

class ChargingStatus(Enum):
    WAITING = "waiting"      # 等候区等待
    QUEUING = "queuing"      # 充电区排队
    CHARGING = "charging"    # 正在充电
    COMPLETED = "completed"  # 充电完成
    CANCELLED = "cancelled"  # 已取消
    FAULT = "fault"         # 故障

class PileStatus(Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    MAINTENANCE = "maintenance"
    FAULT = "fault"

@dataclass
class ChargingPile:
    id: str
    pile_type: ChargingMode
    power: float
    status: PileStatus
    location_info: str = ""
    total_charging_count: int = 0
    total_charging_time: float = 0.0
    total_charging_amount: float = 0.0

@dataclass
class ChargingSession:
    id: int
    session_id: str
    user_id: int
    pile_id: str
    queue_number: str
    charging_mode: ChargingMode
    requested_amount: float
    actual_amount: float = 0.0
    charging_duration: float = 0.0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    status: ChargingStatus = ChargingStatus.WAITING
    charging_fee: float = 0.0
    service_fee: float = 0.0
    total_fee: float = 0.0
    created_at: Optional[datetime] = None

@dataclass
class QueueInfo:
    queue_number: str
    user_id: int
    charging_mode: ChargingMode
    requested_amount: float
    waiting_time: float = 0.0
    estimated_wait_time: float = 0.0