"""
scheduler_core/__init__.py

对外统一导出的函数 / 数据模型
"""

from .core import (
    # 队列
    generate_queue_number,
    enqueue_request,
    fetch_next_request,
    get_waiting_list,
    # 调度
    assign_request,
    estimate_finish_time,
    start_dispatch_loop,
    stop_dispatch_loop,
    # 故障
    mark_fault,
    recover_pile,
    #暂停
    pause_charging,
    end_charging,

    get_all_piles,
)
from .models import (
    PileType,
    PileStatus,
    Pile,
    ChargeRequest,
    DispatchResult,
)
# 关键：将 store.py 内 add_pile / pop_events 暴露给外部
from .store import add_pile, pop_events

__all__ = [
    # 队列
    "generate_queue_number",
    "enqueue_request",
    "fetch_next_request",
    "get_waiting_list",
    # 调度
    "assign_request",
    "estimate_finish_time",
    "start_dispatch_loop",
    "stop_dispatch_loop",
    # 故障
    "mark_fault",
    "recover_pile",
    # 事件（测试 / WebSocket）
    "pop_events",
    # 数据模型
    "PileType",
    "PileStatus",
    "Pile",
    "ChargeRequest",
    "DispatchResult",
    # 工具
    "add_pile",
    "pause_charging",
    "end_charging",

    "get_all_piles",
]
