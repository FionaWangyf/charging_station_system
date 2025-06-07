"""
调度 / 排队 / 故障处理  —— 纯业务逻辑，多线程安全。
"""
from __future__ import annotations
from datetime import datetime, timedelta
import threading
import time
from typing import List, Optional

from .models import (
    PileType,
    PileStatus,
    Pile,
    ChargeRequest,
    DispatchResult,
)
from . import store

# ------------- 排队号 ------------------------------------------------
def generate_queue_number(pile_type: str) -> str:
    today = datetime.utcnow().strftime("%Y%m%d")
    idx   = store.inc_counter(today, pile_type)
    return f"{pile_type}{today}{idx:06d}"


# ------------- 队列 --------------------------------------------------
def enqueue_request(req: ChargeRequest) -> None:
    store.push_queue(req)
    store.push_event({"type": "queue_update", "data": req.pile_type})


def fetch_next_request(ptype: str) -> Optional[ChargeRequest]:
    return store.pop_queue(ptype)


def get_waiting_list(ptype: str, n: int = 20) -> List[ChargeRequest]:
    return store.peek_queue(ptype, n)


# ------------- 调度 --------------------------------------------------
_assign_lock = threading.Lock()          # 确保调度 + 故障互斥


def _eta(pile: Pile, req: ChargeRequest) -> float:
    now = datetime.utcnow()
    remained = (
        max((pile.estimated_end - now).total_seconds(), 0)
        if pile.estimated_end
        else 0
    )
    this_job = req.kwh / pile.max_kw * 3600
    return remained + this_job


def assign_request(req: ChargeRequest) -> Optional[DispatchResult]:
    """
    最短完成时间算法：找 ETA 最小的空闲桩，原子更新状态并返回调度结果。
    """
    with _assign_lock:
        cands = [p for p in store.all_piles(req.pile_type) if p.status == PileStatus.IDLE]
        if not cands:
            return None

        chosen = min(cands, key=lambda p: _eta(p, req))
        now    = datetime.utcnow()
        finish = now + timedelta(hours=req.kwh / chosen.max_kw)

        # 更新桩状态
        chosen.status = PileStatus.BUSY
        chosen.current_req_id = req.req_id
        chosen.estimated_end  = finish

        result = DispatchResult(
            req_id=req.req_id,
            pile_id=chosen.pile_id,
            queue_no=req.queue_no,
            start_time=now,
            estimated_end=finish,
        )
        store.push_event({"type": "dispatch", "data": result})
        return result


def estimate_finish_time(pile_id: str) -> datetime:
    return store._piles[pile_id].estimated_end or datetime.utcnow()


# ------------- 故障 --------------------------------------------------
def mark_fault(pile_id: str) -> None:
    with _assign_lock:
        p = store._piles[pile_id]
        p.status = PileStatus.FAULT
        store.push_event({"type": "pile_fault", "data": pile_id})

        # 把正在充电的任务放回队列
        if p.current_req_id:
            req = ChargeRequest(
                req_id     = p.current_req_id,
                queue_no   = generate_queue_number(p.type),
                user_id    = "SYSTEM",
                pile_type  = p.type,
                kwh        = 0,
            )
            enqueue_request(req)
            p.current_req_id = None
            p.estimated_end  = None


def recover_pile(pile_id: str) -> None:
    p = store._piles[pile_id]
    p.status = PileStatus.IDLE
    store.push_event({"type": "pile_recover", "data": pile_id})


# ------------- 后台循环 ---------------------------------------------
_stop_flag = threading.Event()

def _loop(interval: float = 0.5) -> None:
    while not _stop_flag.is_set():
        for tp in (PileType.D.value, PileType.A.value):
            req = fetch_next_request(tp)
            if req:
                assign_request(req)
        time.sleep(interval)


_dispatch_thread: threading.Thread | None = None


def start_dispatch_loop() -> None:
    global _dispatch_thread
    if _dispatch_thread and _dispatch_thread.is_alive():
        return
    _dispatch_thread = threading.Thread(target=_loop, daemon=True, name="DispatchLoop")
    _dispatch_thread.start()


def stop_dispatch_loop(timeout: float = 2.0) -> None:
    _stop_flag.set()
    if _dispatch_thread:
        _dispatch_thread.join(timeout)

def pause_charging(pile_id: str) -> None:
    """将正在充电的桩设为暂停（PAUSED），不再调度"""
    with _assign_lock:
        pile = store._piles.get(pile_id)
        if not pile:
            return
        if pile.status == PileStatus.BUSY:
            pile.status = PileStatus.PAUSED
            store.push_event({"type": "charging_paused", "data": pile_id})


def end_charging(pile_id: str) -> None:
    """手动结束充电，置为 IDLE，清空任务"""
    with _assign_lock:
        pile = store._piles.get(pile_id)
        if not pile:
            return
        if pile.status in [PileStatus.BUSY, PileStatus.PAUSED]:
            pile.status = PileStatus.IDLE
            pile.current_req_id = None
            pile.estimated_end = None
            store.push_event({"type": "charging_end", "data": pile_id})

def get_all_piles() -> list:
    """
    返回所有充电桩对象的列表。
    """
    return list(store._piles.values())