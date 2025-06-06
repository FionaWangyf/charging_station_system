"""
线程安全的『内存存储层』——如以后想换 Redis，只改这里即可。
"""
from __future__ import annotations
import threading
from collections import defaultdict, deque
from datetime import datetime
from typing import Dict, Deque, List

from .models import Pile, ChargeRequest, PileType

_lock = threading.RLock()

# —— 计数器 { (yyyyMMdd, pile_type) : int } ——
_counters: Dict[tuple[str, str], int] = defaultdict(int)

# —— 等候区 { pile_type : deque[ChargeRequest] } ——
_queues: Dict[str, Deque[ChargeRequest]] = {
    "D": deque(),
    "A": deque(),
}

# —— 充电桩 { pile_id : Pile } ——
_piles: Dict[str, Pile] = {}

# —— 事件队列 (供测试 / WS 转发) ——
_events: Deque[dict] = deque(maxlen=100)   # append & pop

# -------------------------------------------------
#                 计数器  +  队列
# -------------------------------------------------
def inc_counter(date_str: str, ptype: str) -> int:
    with _lock:
        _counters[(date_str, ptype)] += 1
        return _counters[(date_str, ptype)]


def push_queue(req: ChargeRequest) -> None:
    with _lock:
        _queues[req.pile_type].append(req)


def pop_queue(ptype: str) -> ChargeRequest | None:
    with _lock:
        if _queues[ptype]:
            return _queues[ptype].popleft()
        return None


def peek_queue(ptype: str, n: int) -> List[ChargeRequest]:
    with _lock:
        return list(_queues[ptype])[:n]


# -------------------------------------------------
#                 充电桩
# -------------------------------------------------
def add_pile(pile: Pile) -> None:
    with _lock:
        _piles[pile.pile_id] = pile


def all_piles(ptype: str) -> List[Pile]:
    with _lock:
        return [p for p in _piles.values() if p.type == ptype]


# -------------------------------------------------
#                 事件总线 (内存)
# -------------------------------------------------
def push_event(event: dict) -> None:
    with _lock:
        _events.append(event)


def pop_events() -> List[dict]:
    with _lock:
        evts = list(_events)
        _events.clear()
        return evts
