#!/usr/bin/env python3
"""
测试调度引擎集成
"""
import sys
import os
sys.path.append('scheduler_core')

import scheduler_core
from scheduler_core import PileType, PileStatus, Pile, ChargeRequest
from datetime import datetime

def test_scheduler_basic():
    """测试调度引擎基本功能"""
    print("=" * 50)
    print("测试调度引擎基本功能")
    print("=" * 50)
    
    # 1. 创建充电桩
    fast_pile = Pile(
        pile_id="A",
        type=PileType.D,  # 快充
        max_kw=30.0,
        status=PileStatus.IDLE
    )
    
    slow_pile = Pile(
        pile_id="C", 
        type=PileType.A,  # 慢充
        max_kw=7.0,
        status=PileStatus.IDLE
    )
    
    # 2. 添加到调度引擎
    scheduler_core.add_pile(fast_pile)
    scheduler_core.add_pile(slow_pile)
    print(f"✅ 添加充电桩: {fast_pile.pile_id} (快充), {slow_pile.pile_id} (慢充)")
    
    # 3. 生成队列号
    fast_queue_no = scheduler_core.generate_queue_number(PileType.D.value)
    slow_queue_no = scheduler_core.generate_queue_number(PileType.A.value)
    print(f"✅ 生成队列号: 快充={fast_queue_no}, 慢充={slow_queue_no}")
    
    # 4. 创建充电请求
    fast_request = ChargeRequest(
        req_id="test_fast_001",
        queue_no=fast_queue_no,
        user_id="user_1",
        pile_type=PileType.D,
        kwh=25.0,
        generated_at=datetime.utcnow()
    )
    
    slow_request = ChargeRequest(
        req_id="test_slow_001", 
        queue_no=slow_queue_no,
        user_id="user_2",
        pile_type=PileType.A,
        kwh=15.0,
        generated_at=datetime.utcnow()
    )
    
    # 5. 加入队列
    scheduler_core.enqueue_request(fast_request)
    scheduler_core.enqueue_request(slow_request)
    print(f"✅ 充电请求已加入队列")
    
    # 6. 查看队列状态
    fast_queue = scheduler_core.get_waiting_list(PileType.D.value, n=10)
    slow_queue = scheduler_core.get_waiting_list(PileType.A.value, n=10) 
    print(f"✅ 快充队列长度: {len(fast_queue)}")
    print(f"✅ 慢充队列长度: {len(slow_queue)}")
    
    # 7. 测试调度
    fast_result = scheduler_core.assign_request(fast_request)
    slow_result = scheduler_core.assign_request(slow_request)
    
    if fast_result:
        print(f"✅ 快充调度成功: {fast_result.req_id} -> {fast_result.pile_id}")
    if slow_result:
        print(f"✅ 慢充调度成功: {slow_result.req_id} -> {slow_result.pile_id}")
    
    # 8. 查看所有充电桩状态
    all_piles = scheduler_core.get_all_piles()
    print(f"✅ 充电桩状态:")
    for pile in all_piles:
        print(f"   {pile.pile_id}: {pile.status.value}, 当前任务: {pile.current_req_id}")
    
    # 9. 查看事件
    events = scheduler_core.pop_events()
    print(f"✅ 产生的事件数量: {len(events)}")
    for event in events:
        print(f"   事件: {event['type']}")
    
    print("=" * 50)
    print("调度引擎测试完成！")
    print("=" * 50)

if __name__ == "__main__":
    test_scheduler_basic()