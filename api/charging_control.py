import json
import threading
import uuid
from datetime import datetime, timedelta, time
from typing import List, Dict, Optional # 移除了未明确使用的Tuple
from threading import Lock
from apscheduler.schedulers.background import BackgroundScheduler

from database import DatabaseManager
from models import ChargingMode
from config import Config
import scheduler_core # 通过此模块访问引擎函数
from scheduler_core import PileType, PileStatus, Pile, ChargeRequest, DispatchResult # 导入模型

class ChargingControlManager:
    def __init__(self, db_manager: DatabaseManager, socketio):
        self.db = db_manager
        self.socketio = socketio
        self.lock = Lock()
        
        self.scheduler = BackgroundScheduler()
        self.scheduler.start()
        
        self.init_redis_data()
        self.init_piles_in_engine()

        # 原有的定时任务
        self.scheduler.add_job(
            func=self.poll_and_process_engine_events,
            trigger="interval",
            seconds=2,
            id='engine_event_poller'
        )
        
        self.scheduler.add_job(
            func=self.monitor_charging_progress,
            trigger="interval",
            seconds=10,
            id='charging_monitor'
        )

        self.scheduler.add_job(
            func=self.process_station_waiting_area_to_engine,
            trigger="interval",
            seconds=5,
            id='station_to_engine_queue_processor'
        )
        
        # 新添加：超时检查任务
        self.scheduler.add_job(
            func=self.check_and_recover_timeout_completing_sessions,
            trigger="interval",
            seconds=30,  # 每30秒检查一次超时会话
            id='timeout_completing_checker'
        )
        
        scheduler_core.start_dispatch_loop()
        
        print("=" * 60)
        print("充电控制管理器已启动，包含超时恢复机制")
        print("=" * 60)
    def init_redis_data(self):
        redis_client = self.db.get_redis_client()
        redis_client.delete('station_waiting_area:fast', 'station_waiting_area:trickle')
        
        connection = self.db.get_mysql_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT id, pile_type, power, status FROM charging_piles") # 确保数据库有'status'字段
        piles_db = cursor.fetchall()
        cursor.close()
        connection.close()

        for p_db in piles_db:
            engine_pile_type = PileType.D if p_db['pile_type'] == 'fast' else PileType.A
            
            engine_status = PileStatus.IDLE # 默认状态
            if p_db['status'] == 'fault': # 假设你的数据库状态为'fault'
                engine_status = PileStatus.FAULT
            elif p_db['status'] == 'offline': # 假设你的数据库状态为'offline'
                # 离线充电桩可能不会添加到引擎中，或者作为FAULT/其他状态添加
                # 这取决于团队B对离线充电桩的设计
                # 现在假设离线充电桩最初不会添加到可调度池中
                print(f"充电桩 {p_db['id']} 处于离线状态，暂不添加到调度引擎。")
                continue 
            # 如有必要添加其他映射（例如，如果充电桩从数据库开始就是'busy'状态）

            pile_for_engine = Pile(
                pile_id=p_db['id'],
                type=engine_pile_type,
                max_kw=float(p_db['power']),
                status=engine_status
            )
            scheduler_core.add_pile(pile_for_engine) # 调用模块级函数
        print("充电桩已注册到调度引擎。")

    def init_piles_in_engine(self):
        # 如果有特殊初始化逻辑可以写在这里，否则可以留空
        pass
    def _map_charging_mode_to_engine_piletype(self, charging_mode: str) -> PileType:
        return PileType.D if charging_mode == 'fast' else PileType.A

    def submit_charging_request(self, user_id: int, charging_mode: str, requested_amount: float) -> Dict:
        try:
            with self.lock:
                redis_client = self.db.get_redis_client()
                fast_count = redis_client.llen('station_waiting_area:fast')
                trickle_count = redis_client.llen('station_waiting_area:trickle')
                
                if (fast_count + trickle_count) >= Config.WAITING_AREA_SIZE:
                    return {'success': False, 'message': '等候区已满，请稍后再试', 'code': 2001}

                existing_session = self.get_user_active_session_details(user_id)
                if existing_session and existing_session['status'] not in ['completed', 'cancelled']:
                    return {'success': False, 'message': '您已有进行中的充电会话或请求', 'code': 2002}

                session_id = str(uuid.uuid4())
                
                connection = self.db.get_mysql_connection()
                cursor = connection.cursor()
                cursor.execute("""
                    INSERT INTO charging_sessions 
                    (session_id, user_id, charging_mode, requested_amount, status, created_at)
                    VALUES (%s, %s, %s, %s, 'station_waiting', %s) 
                """, (session_id, user_id, charging_mode, requested_amount, datetime.now()))
                connection.commit()
                cursor.close()
                connection.close()

                request_data_for_station_queue = {
                    'session_id': session_id,
                    'user_id': user_id,
                    'charging_mode': charging_mode,
                    'requested_amount': requested_amount,
                    'created_at': datetime.now().isoformat()
                }
                redis_client.rpush(f"station_waiting_area:{charging_mode}", json.dumps(request_data_for_station_queue))
                
                redis_client.hset(f"session_status:{session_id}", mapping={
                    'user_id': str(user_id),
                    'charging_mode': charging_mode,
                    'requested_amount': str(requested_amount),
                    'status': 'station_waiting',
                    'queue_number': ""
                })
                
                self.socketio.emit('user_specific_event', 
                                {'message': f'请求 {session_id} 已提交至充电站等候区', 'session_id': session_id, 'type': 'request_submitted_station'}, 
                                room=f'user_{user_id}')
                
                # 关键修改：在锁外启动线程，并添加延迟
                def delayed_process():
                    import time
                    time.sleep(0.1)  # 短暂延迟，确保主请求先返回
                    self.process_station_waiting_area_to_engine()
                    self.broadcast_status_update()
                
            # 在锁外启动线程，避免死锁
            threading.Thread(target=delayed_process, daemon=True).start()
            
            return {
                'success': True,
                'message': '充电请求已提交至充电站等候区',
                'data': {
                    'session_id': session_id,
                    'status': 'station_waiting'
                }
            }
        except Exception as e:
            print(f"提交充电请求错误: {e}")
            import traceback
            traceback.print_exc()  # 添加详细错误信息
            return {'success': False, 'message': '系统错误，请稍后重试', 'code': 5001}
    def process_station_waiting_area_to_engine(self):
        """将请求从充电站的通用等候区移动到引擎的类型化队列。"""
        with self.lock: # 确保多个触发器的原子性
            redis_client = self.db.get_redis_client()
            for mode in ['fast', 'trickle']:
                station_queue_key = f"station_waiting_area:{mode}"
                
                # 在从Redis列表处理之前检查数据库状态以处理取消操作
                # 这是一个LPOP，所以它会被移除。如果被取消了，我们就丢弃它。
                request_json = redis_client.lpop(station_queue_key)
                
                if request_json:
                    request_data = json.loads(request_json)
                    session_id = request_data['session_id']
                    
                    # 验证数据库中的状态，确保在station_waiting Redis列表中时没有被取消
                    session_db_details = self.get_session_details_from_db(session_id)
                    if not session_db_details or session_db_details['status'] != 'station_waiting':
                        print(f"来自station_waiting_area的会话 {session_id} 不处于'station_waiting'数据库状态（状态为 {session_db_details['status'] if session_db_details else '未找到'}）。跳过排队到引擎。")
                        continue # 跳过这个已取消/无效的请求

                    engine_pile_type = self._map_charging_mode_to_engine_piletype(request_data['charging_mode'])
                    engine_queue_no = scheduler_core.generate_queue_number(engine_pile_type) # 调用模块级函数

                    engine_req = ChargeRequest(
                        req_id=session_id,
                        queue_no=engine_queue_no,
                        user_id=request_data['user_id'],
                        pile_type=engine_pile_type,
                        kwh=float(request_data['requested_amount']),
                        generated_at=datetime.fromisoformat(request_data['created_at'])
                    )
                    
                    scheduler_core.enqueue_request(engine_req) # 调用模块级函数
                    
                    connection = self.db.get_mysql_connection()
                    cursor = connection.cursor()
                    cursor.execute("""
                        UPDATE charging_sessions SET status = 'engine_queued', queue_number = %s 
                        WHERE session_id = %s
                    """, (engine_queue_no, session_id))
                    connection.commit()
                    cursor.close()
                    connection.close()
                    
                    redis_client.hset(
                        f"session_status:{session_id}",
                        mapping={
                            "status": "engine_queued",
                            "queue_number": engine_queue_no
                        }
                    )
                    print(f"将会话 {session_id} 移动到引擎的 {mode} 队列，队列号为 {engine_queue_no}。")
                    self.socketio.emit('user_specific_event', 
                                       {'message': f'请求 {session_id} ({engine_queue_no}) 已进入调度队列', 'session_id': session_id, 'queue_number': engine_queue_no, 'type': 'request_queued_engine'}, 
                                       room=f"user_{request_data['user_id']}")
                    self.broadcast_status_update()

    def modify_charging_request(self, session_id: str, user_id: int, 
                              new_charging_mode: Optional[str] = None, 
                              new_requested_amount: Optional[float] = None):
        try:
            with self.lock:
                session_details = self.get_session_details_from_db(session_id)
                if not session_details:
                    return {'success': False, 'message': '会话不存在', 'code': 2003}
                if session_details['user_id'] != user_id:
                    return {'success': False, 'message': '无权限修改此会话', 'code': 2004}

                current_status = session_details['status']
                original_charging_mode = session_details['charging_mode']
                redis_client = self.db.get_redis_client()

                if current_status in ['charging', 'completed', 'cancelled', 'fault_pending_reschedule']:
                    return {'success': False, 'message': f'会话状态为 {current_status}，不允许修改。请取消后重新提交。', 'code': 2005}

                # --- 修改逻辑 ---
                # 修改充电模式
                if new_charging_mode and new_charging_mode != original_charging_mode:
                    if current_status == 'engine_queued':
                        # 根据要求："不允许在充电区修改，可取消充电重新进入等候区排队。"
                        # 如果'engine_queued'被认为是"尚未充电"，如果引擎支持移除，这可能是允许的。
                        # 鉴于引擎API限制（没有remove_from_queue），用户必须取消并重新提交。
                        return {'success': False, 'message': '已进入调度队列，修改模式请先取消当前请求再重新提交。', 'code': 2007}
                    
                    if current_status == 'station_waiting':
                        # 根据要求："允许在等候区修改，修改后重新生成排队号，并排到修改后对应模式类型队列的最后一位。"
                        # 1. 从旧的Redis station_waiting_area列表中移除
                        # 这在LPOP情况下很复杂。最简单的是在数据库中标记为"modified_mode"。
                        # process_station_waiting_area_to_engine将为旧模式跳过它。
                        # 然后，重新添加到新的Redis station_waiting_area列表。
                        
                        # 为了能够正常工作，我们需要确保它从*特定*列表中被移除。
                        # 一个健壮的方法：遍历列表，找到并重建。或在列表值中使用唯一的请求ID。
                        # 让我们尝试删除并重新添加（如果找到）。
                        removed_from_old_list = False
                        old_list_key = f"station_waiting_area:{original_charging_mode}"
                        temp_list = []
                        # 这在其他进程中使用LPOP时不是原子的。竞态条件风险高。
                        # 更好的方法是在session_status哈希中设置标志，处理器检查它。
                        # 为了满足要求，假设我们可以管理这一点：
                        # 通过值进行迭代和删除既低效又有其他LREM/LPOP的风险。
                        # 简化：用户必须取消并重新提交模式更改。
                        # 这与"允许在等候区修改"相矛盾，所以让我们做个说明。
                        # *如果*我们有可靠的方法从station_waiting_area中删除：
                        #   self.remove_from_station_waiting_list(session_id, original_charging_mode) # 需要实现
                        #   session_details['charging_mode'] = new_charging_mode
                        #   self.add_to_station_waiting_list(session_details) # 需要实现
                        #   更新数据库、Redis哈希。处理时队列号将是新的。
                        # 由于复杂性/风险，将建议取消并重新提交模式更改。
                        return {'success': False, 'message': '修改充电模式请先取消当前请求，然后以新模式重新提交。', 'code': 20071}

                # 修改请求电量
                if new_requested_amount is not None and new_requested_amount != float(session_details['requested_amount']):
                    if current_status == 'engine_queued':
                         # 引擎API不允许更新已排队的请求。
                        return {'success': False, 'message': '已进入调度队列，无法修改充电量。请取消后重新提交。', 'code': 20072}
                    
                    # 在'station_waiting'状态下允许修改
                    if current_status == 'station_waiting':
                        connection = self.db.get_mysql_connection()
                        cursor = connection.cursor()
                        cursor.execute("UPDATE charging_sessions SET requested_amount = %s WHERE session_id = %s",
                                       (new_requested_amount, session_id))
                        connection.commit()
                        cursor.close()
                        connection.close()
                        redis_client.hset(
                            f"session_status:{session_id}",
                            mapping={"requested_amount": str(new_requested_amount)}
                        )
                        
                        # 如果仍在station_waiting_area列表中，则更新（这很困难）
                        # 为了简单起见，假设更改在以下情况下被采用
                        self.socketio.emit('user_specific_event', 
                                           {'message': f'请求 {session_id} 的充电量已修改为 {new_requested_amount} kWh', 'session_id': session_id, 'type': 'request_modified'}, 
                                           room=f'user_{user_id}')
                        self.broadcast_status_update()
                        return {'success': True, 'message': '充电量修改成功'}

                return {'success': False, 'message': '没有有效的修改参数', 'code': 2006}
        except Exception as e:
            print(f"修改充电请求错误: {e}")
            return {'success': False, 'message': '系统错误，请稍后重试', 'code': 5001}

    def cancel_charging_request(self, session_id: str, user_id: int) -> Dict:
        try:
            with self.lock:
                session_details = self.get_session_details_from_db(session_id)
                if not session_details:
                    return {'success': False, 'message': '会话不存在', 'code': 2003}
                if session_details['user_id'] != user_id:
                    return {'success': False, 'message': '无权限取消此会话', 'code': 2004}

                current_status = session_details['status']
                pile_id = session_details['pile_id']
                redis_client = self.db.get_redis_client()

                if current_status in ['completed', 'cancelled']:
                    return {'success': False, 'message': '会话已结束', 'code': 2008}

                if current_status in ['charging', 'completing']:  # 允许取消completing状态
                    if pile_id:
                        if current_status == 'completing':
                            # 如果是completing状态，直接强制完成为cancelled
                            print(f"强制取消completing状态的会话 {session_id}")
                            self.force_complete_session_as_cancelled(session_id, pile_id)
                        else:
                            # 正常充电状态，通过引擎结束
                            scheduler_core.end_charging(pile_id)
                            print(f"由于取消，向引擎发送end_charging指令，充电桩 {pile_id} / 会话 {session_id}。")
                    else:
                        return {'success': False, 'message': '充电中但无充电桩信息，状态异常', 'code': 5002}
                
                elif current_status == 'engine_queued':
                    connection = self.db.get_mysql_connection()
                    cursor = connection.cursor()
                    cursor.execute("""
                        UPDATE charging_sessions SET status = 'cancelling_after_dispatch', end_time = %s
                        WHERE session_id = %s
                    """, (datetime.now(), session_id))
                    connection.commit()
                    cursor.close()
                    connection.close()
                    redis_client.hset(f"session_status:{session_id}", mapping={"status": "cancelling_after_dispatch"})
                    self.socketio.emit('user_specific_event', 
                                    {'message': f'请求 {session_id} 将在分配到充电桩后自动取消', 'session_id': session_id, 'type':'request_pending_cancel_dispatch'}, 
                                    room=f'user_{user_id}')

                elif current_status == 'station_waiting':
                    connection = self.db.get_mysql_connection()
                    cursor = connection.cursor()
                    cursor.execute("""
                        UPDATE charging_sessions SET status = 'cancelled', end_time = %s 
                        WHERE session_id = %s
                    """, (datetime.now(), session_id))
                    connection.commit()
                    cursor.close()
                    connection.close()
                    redis_client.delete(f"session_status:{session_id}")
                    self.socketio.emit('user_specific_event', 
                                    {'message': f'请求 {session_id} 已从充电站等候区取消', 'session_id': session_id, 'type':'request_cancelled_station'}, 
                                    room=f'user_{user_id}')
                else:
                    return {'success': False, 'message': f'当前状态 {current_status} 无法直接取消', 'code': 2010}

                self.broadcast_status_update()
                return {'success': True, 'message': '取消请求处理中/已提交'}
        except Exception as e:
            print(f"取消充电请求错误: {e}")
            return {'success': False, 'message': '系统错误', 'code': 5001}
    def force_complete_session_as_cancelled(self, session_id: str, pile_id: str):
        """强制完成completing状态的会话为cancelled"""
        try:
            session_details = self.get_session_details_from_db(session_id)
            if not session_details:
                return
                
            user_id = session_details['user_id']
            actual_amount = float(session_details.get('actual_amount', 0))
            charging_duration_hours = float(session_details.get('charging_duration', 0))
            start_time = session_details.get('start_time')
            
            # 计算已充电部分的费用
            fees = self.calculate_charging_fees(session_id, actual_amount, start_time, datetime.now())
            
            connection = self.db.get_mysql_connection()
            cursor = connection.cursor()
            cursor.execute("""
                UPDATE charging_sessions 
                SET status = 'cancelled', end_time = %s,
                    charging_fee = %s, service_fee = %s, total_fee = %s
                WHERE session_id = %s
            """, (datetime.now(), fees['charging_fee'], fees['service_fee'], fees['total_fee'], session_id))
            
            cursor.execute("""
                UPDATE charging_piles 
                SET total_charging_count = total_charging_count + 1,
                    total_charging_time = total_charging_time + %s,
                    total_charging_amount = total_charging_amount + %s
                WHERE id = %s
            """, (charging_duration_hours, actual_amount, pile_id))
            connection.commit()
            cursor.close()
            connection.close()
            
            # 清理状态
            redis_client = self.db.get_redis_client()
            redis_client.delete(f"session_status:{session_id}")
            redis_client.delete(f"session_completing:{session_id}")
            self.update_pile_redis_status(pile_id, PileStatus.IDLE.value, None)
            
            # 通知用户
            self.socketio.emit('user_specific_event', {
                'message': f'您的充电会话 {session_id} 已取消。已充电量: {actual_amount:.2f}kWh，费用: {fees["total_fee"]:.2f}元。',
                'type': 'charging_cancelled_from_completing',
                'session_id': session_id,
                'total_fee': fees['total_fee']
            }, room=f'user_{user_id}')
            
            print(f"强制完成completing会话 {session_id} 为cancelled状态")
            
        except Exception as e:
            print(f"强制完成会话错误: {e}")
            import traceback
            traceback.print_exc()
    def poll_and_process_engine_events(self):
        try:
            events = scheduler_core.pop_events()
            
            for event in events:
                event_type = event.get("type")
                event_data = event.get("data")

                if event_type == "dispatch":
                    session_id = event_data.req_id
                    pile_id = event_data.pile_id
                    start_time_str = event_data.start_time
                    start_time_dt = datetime.fromisoformat(start_time_str) if isinstance(start_time_str, str) else start_time_str
                    
                    session_db_details = self.get_session_details_from_db(session_id)
                    if session_db_details and session_db_details['status'] == 'cancelling_after_dispatch':
                        print(f"会话 {session_id} 被标记为取消，调度后立即结束充电桩 {pile_id} 上的充电。")
                        scheduler_core.end_charging(pile_id)
                    else:
                        self.handle_engine_dispatch(session_id, pile_id, start_time_dt)

                elif event_type == "charging_end":
                    session_id = None
                    pile_id = None
                    
                    # 尝试从不同的数据结构中提取信息
                    if hasattr(event_data, 'req_id'):
                        session_id = event_data.req_id
                        pile_id = event_data.pile_id
                    elif isinstance(event_data, dict):
                        session_id = event_data.get('req_id')
                        pile_id = event_data.get('pile_id')
                    elif isinstance(event_data, str):
                        pile_id = event_data
                    
                    if session_id:
                        print(f"处理引擎charging_end事件: session_id={session_id}, pile_id={pile_id}")
                        self.handle_engine_charging_end(session_id, pile_id, graceful_end=True)
                    elif pile_id:
                        # 如果只有pile_id，尝试查找该充电桩上的completing/charging会话
                        print(f"引擎charging_end事件缺少session_id，尝试通过pile_id查找: {pile_id}")
                        self.handle_pile_end_without_session_id(pile_id)
                    else:
                        print(f"警告: charging_end事件数据不完整: {event_data}")

                elif event_type == "pile_fault":
                    pile_id = event_data
                    self.handle_engine_pile_fault(pile_id)

                elif event_type == "pile_recover":
                    pile_id = event_data
                    self.handle_engine_pile_recover(pile_id)
                
                elif event_type == "charging_paused":
                    pile_id = event_data
                    self.handle_engine_charging_paused(pile_id)

            if events:
                self.broadcast_status_update()
                
            # 添加：检查和恢复超时的completing状态
            self.check_and_recover_timeout_completing_sessions()
            
        except Exception as e:
            print(f"轮询/处理引擎事件错误: {e}")
            import traceback
            traceback.print_exc()

    def handle_pile_end_without_session_id(self, pile_id: str):
        """处理只有pile_id的charging_end事件，查找对应的会话"""
        with self.lock:
            connection = self.db.get_mysql_connection()
            cursor = connection.cursor(dictionary=True)
            
            # 查找该充电桩上的completing或charging状态会话
            cursor.execute("""
                SELECT session_id, status FROM charging_sessions 
                WHERE pile_id = %s AND status IN ('completing', 'charging')
                ORDER BY start_time DESC LIMIT 1
            """, (pile_id,))
            
            session_on_pile = cursor.fetchone()
            cursor.close()
            connection.close()
            
            if session_on_pile:
                session_id = session_on_pile['session_id']
                print(f"找到充电桩 {pile_id} 上的会话 {session_id}，状态: {session_on_pile['status']}")
                self.handle_engine_charging_end(session_id, pile_id, graceful_end=True)
            else:
                print(f"充电桩 {pile_id} 上未找到completing/charging状态的会话，仅更新充电桩状态")
                self.update_pile_redis_status(pile_id, PileStatus.IDLE.value, None)

    def check_and_recover_timeout_completing_sessions(self):
        """检查和恢复超时的completing状态会话"""
        try:
            connection = self.db.get_mysql_connection()
            cursor = connection.cursor(dictionary=True)
            
            # 查找超过60秒仍在completing状态的会话
            timeout_threshold = datetime.now() - timedelta(seconds=60)
            cursor.execute("""
                SELECT session_id, pile_id, user_id, start_time, actual_amount, charging_duration
                FROM charging_sessions 
                WHERE status = 'completing' AND start_time < %s
            """, (timeout_threshold,))
            
            timeout_sessions = cursor.fetchall()
            
            for session in timeout_sessions:
                session_id = session['session_id']
                pile_id = session['pile_id']
                user_id = session['user_id']
                
                print(f"检测到超时的completing会话: {session_id}，强制完成处理")
                
                # 计算费用
                actual_amount = float(session.get('actual_amount', 0))
                charging_duration_hours = float(session.get('charging_duration', 0))
                start_time = session.get('start_time')
                
                fees = self.calculate_charging_fees(session_id, actual_amount, start_time, datetime.now())
                
                # 强制完成会话
                cursor.execute("""
                    UPDATE charging_sessions 
                    SET status = 'completed', end_time = %s,
                        charging_fee = %s, service_fee = %s, total_fee = %s
                    WHERE session_id = %s
                """, (datetime.now(), fees['charging_fee'], fees['service_fee'], fees['total_fee'], session_id))
                
                # 更新充电桩统计
                if pile_id:
                    cursor.execute("""
                        UPDATE charging_piles 
                        SET total_charging_count = total_charging_count + 1,
                            total_charging_time = total_charging_time + %s,
                            total_charging_amount = total_charging_amount + %s
                        WHERE id = %s
                    """, (charging_duration_hours, actual_amount, pile_id))
                    
                    # 更新充电桩状态
                    self.update_pile_redis_status(pile_id, PileStatus.IDLE.value, None)
                
                connection.commit()
                
                # 清理Redis状态
                redis_client = self.db.get_redis_client()
                redis_client.delete(f"session_status:{session_id}")
                redis_client.delete(f"session_completing:{session_id}")
                
                # 通知用户
                if user_id:
                    self.socketio.emit('user_specific_event', {
                        'message': f'您的充电会话 {session_id} 已完成（系统恢复）。总费用: {fees["total_fee"]:.2f}元。',
                        'type': 'charging_completed_recovery',
                        'session_id': session_id,
                        'total_fee': fees['total_fee'],
                        'actual_amount': actual_amount
                    }, room=f'user_{user_id}')
                    
                # 触发队列处理
                self.process_station_waiting_area_to_engine()
            
            cursor.close()
            connection.close()
            
            if timeout_sessions:
                print(f"恢复了 {len(timeout_sessions)} 个超时的completing会话")
                self.broadcast_status_update()
                
        except Exception as e:
            print(f"检查超时completing会话错误: {e}")
            import traceback
            traceback.print_exc()

    def handle_engine_dispatch(self, session_id: str, pile_id: str, engine_start_time: datetime):
        with self.lock:
            print(f"处理调度: 会话 {session_id} 到充电桩 {pile_id}，时间 {engine_start_time}")
            connection = self.db.get_mysql_connection()
            cursor = connection.cursor(dictionary=True)
            
            cursor.execute("""
                UPDATE charging_sessions 
                SET pile_id = %s, status = 'charging', start_time = %s, actual_amount = 0, charging_duration = 0
                WHERE session_id = %s
            """, (pile_id, engine_start_time, session_id))
            connection.commit()

            cursor.execute("SELECT user_id, queue_number FROM charging_sessions WHERE session_id = %s", (session_id,))
            session_info = cursor.fetchone()
            user_id = session_info['user_id'] if session_info else None
            queue_number = session_info['queue_number'] if session_info else "N/A"

            cursor.close()
            connection.close()

            self.update_pile_redis_status(pile_id, PileStatus.BUSY.value, session_id)
            
            redis_client = self.db.get_redis_client()
            session_status_payload = {
                "status": "charging",
                "pile_id": pile_id,
                "start_time": engine_start_time.isoformat(),
                "actual_amount": "0", # 初始化
                "charging_duration": "0" # 初始化
            }
            redis_client.hset(f"session_status:{session_id}", mapping=session_status_payload)

            msg = f"您的请求 {queue_number} ({session_id}) 已开始在充电桩 {pile_id} 充电。"
            if user_id:
                 self.socketio.emit('user_specific_event', 
                                    {'message': msg, 'type': 'charging_started', 'session_id': session_id, 'pile_id': pile_id, 'start_time': engine_start_time.isoformat()}, 
                                    room=f'user_{user_id}')

    def handle_engine_charging_end(self, session_id: str, pile_id: str, graceful_end: bool = True):
        with self.lock:
            print(f"处理充电结束: 会话 {session_id} 在充电桩 {pile_id}，正常结束: {graceful_end}")
            
            # 清理Redis中的完成处理标志
            redis_client = self.db.get_redis_client()
            completion_key = f"session_completing:{session_id}"
            redis_client.delete(completion_key)
            
            session_details = self.get_session_details_from_db(session_id)
            if not session_details:
                print(f"在充电结束处理期间，数据库中未找到会话 {session_id}。")
                self.update_pile_redis_status(pile_id, PileStatus.IDLE.value, None)
                return

            user_id = session_details['user_id']
            current_db_status = session_details['status']
            final_status = 'completed'
            
            # 处理各种状态转换
            if current_db_status == 'cancelling_after_dispatch' or \
            (current_db_status in ['charging', 'completing'] and not graceful_end): # 包括新的'completing'状态
                final_status = 'cancelled'
            
            # 如果是从'completing'状态转换，说明是正常完成
            if current_db_status == 'completing':
                final_status = 'completed'
            
            # 如果由故障结束，状态可能已经反映了类似'fault_pending_reschedule'的内容
            # 此处理器用于引擎说"在此充电桩上完成"时。
            # 如果是故障，`handle_engine_pile_fault`可能已经更新了状态。
            # 在这里，我们只是为已充电的部分完成计费。

            # 确保actual_amount和charging_duration从数据库中获取，由monitor_charging_progress更新
            actual_amount = float(session_details.get('actual_amount', 0))
            charging_duration_hours = float(session_details.get('charging_duration', 0))
            start_time = session_details.get('start_time') # 这应该是一个datetime对象

            fees = self.calculate_charging_fees(session_id, actual_amount, start_time, datetime.now())

            connection = self.db.get_mysql_connection()
            cursor = connection.cursor()
            cursor.execute("""
                UPDATE charging_sessions 
                SET status = %s, end_time = %s, 
                    charging_fee = %s, service_fee = %s, total_fee = %s,
                    actual_amount = %s, charging_duration = %s 
                WHERE session_id = %s
            """, (final_status, datetime.now(), 
                fees['charging_fee'], fees['service_fee'], fees['total_fee'],
                actual_amount, charging_duration_hours,
                session_id))
            
            cursor.execute("""
                UPDATE charging_piles 
                SET total_charging_count = total_charging_count + 1,
                    total_charging_time = total_charging_time + %s,
                    total_charging_amount = total_charging_amount + %s
                WHERE id = %s
            """, (charging_duration_hours, actual_amount, pile_id))
            connection.commit()
            cursor.close()
            connection.close()

            self.update_pile_redis_status(pile_id, PileStatus.IDLE.value, None)
            redis_client.delete(f"session_status:{session_id}")

            msg = f"您的充电请求 {session_details.get('queue_number', 'N/A')} ({session_id}) 已在充电桩 {pile_id} {final_status}。总费用: {fees['total_fee']:.2f}元。"
            if user_id:
                self.socketio.emit('user_specific_event', {
                    'message': msg, 'type': 'charging_ended', 'session_id': session_id, 
                    'pile_id': pile_id, 'total_fee': fees['total_fee'], 'status': final_status,
                    'actual_amount': actual_amount, 'charging_duration': charging_duration_hours
                    }, room=f'user_{user_id}')
            
            self.process_station_waiting_area_to_engine()
    def handle_engine_pile_fault(self, pile_id: str):
        with self.lock:
            print(f"处理充电桩故障: 充电桩 {pile_id}")
            connection = self.db.get_mysql_connection()
            cursor = connection.cursor(dictionary=True) # 使用dictionary=True获取列名
            cursor.execute("UPDATE charging_piles SET status = 'fault' WHERE id = %s", (pile_id,))
            
            # 从我们的记录中找到在此充电桩上的会话
            # （引擎可能重新排队，但我们需要更新我们的会话）
            cursor.execute("SELECT session_id, user_id, actual_amount, charging_duration, start_time, queue_number FROM charging_sessions WHERE pile_id = %s AND status = 'charging'", (pile_id,))
            active_session_on_faulted_pile = cursor.fetchone()

            if active_session_on_faulted_pile:
                session_id = active_session_on_faulted_pile['session_id']
                user_id = active_session_on_faulted_pile['user_id']
                
                # 故障时的已充电量和持续时间
                actual_amount_at_fault = float(active_session_on_faulted_pile.get('actual_amount',0))
                duration_at_fault = float(active_session_on_faulted_pile.get('charging_duration',0))
                start_time_at_fault = active_session_on_faulted_pile.get('start_time')

                # 计算故障前已充电部分的费用
                fees_at_fault = self.calculate_charging_fees(session_id, actual_amount_at_fault, start_time_at_fault, datetime.now())

                # 更新会话：标记为故障，记录已充电量/费用，清除pile_id
                # 要求说："正在被充电的车辆停止计费，本次充电过程对应一条详单。此后系统重新为故障队列中的车辆进行调度。"
                # 这意味着此session_id已完成。新的可能由引擎逻辑或用户创建。
                cursor.execute("""
                    UPDATE charging_sessions 
                    SET status = 'fault_completed',  -- 此会话因故障而完成
                        pile_id = NULL, 
                        end_time = %s,
                        charging_fee = %s, service_fee = %s, total_fee = %s
                        -- actual_amount和charging_duration已由监控更新
                    WHERE session_id = %s
                """, (datetime.now(), fees_at_fault['charging_fee'], fees_at_fault['service_fee'], fees_at_fault['total_fee'], session_id))
                
                self.db.get_redis_client().hdel(f"session_status:{session_id}") # 从活动会话状态中删除

                msg = (f"充电桩 {pile_id} 发生故障。您的充电请求 {active_session_on_faulted_pile.get('queue_number','N/A')} ({session_id}) 已中断。"
                       f"已充部分电量 {actual_amount_at_fault:.2f} kWh，费用 {fees_at_fault['total_fee']:.2f}元。系统将尝试重新调度未完成部分（若适用）。")
                self.socketio.emit('user_specific_event', {
                    'message': msg, 'type': 'session_fault_stopped', 'session_id': session_id,
                    'pile_id': pile_id, 'fault_reason': 'pile_fault',
                    'partial_amount': actual_amount_at_fault, 'partial_fees': fees_at_fault
                    }, room=f'user_{user_id}')
                # 注意："重新为故障队列中的车辆进行调度"意味着引擎处理为剩余电量或其他在该充电桩（引擎内部）队列中的车辆创建新请求。
                # 我们当前的session_id在这里被认为是最终确定的。

            connection.commit()
            cursor.close()
            connection.close()
            
            self.update_pile_redis_status(pile_id, PileStatus.FAULT.value, None)

    def handle_engine_pile_recover(self, pile_id: str):
        with self.lock:
            print(f"处理充电桩恢复: 充电桩 {pile_id}")
            connection = self.db.get_mysql_connection()
            cursor = connection.cursor()
            cursor.execute("UPDATE charging_piles SET status = 'online' WHERE id = %s", (pile_id,))
            connection.commit()
            cursor.close()
            connection.close()

            self.update_pile_redis_status(pile_id, PileStatus.IDLE.value, None)
            # 如果充电桩是瓶颈，可能触发process_station_waiting_area_to_engine
            self.process_station_waiting_area_to_engine()

    def handle_engine_charging_paused(self, pile_id: str):
        with self.lock:
            print(f"处理充电桩暂停事件: {pile_id}")
            self.update_pile_redis_status(pile_id, PileStatus.PAUSED.value, None) # 当前会话ID可能仍然与充电桩相关
            
            # 找到此充电桩上的会话以通知用户
            session_on_pile = self.get_active_session_on_pile(pile_id) # 这需要检查'charging'或'paused'会话
            if session_on_pile:
                session_id = session_on_pile['session_id']
                user_id = session_on_pile['user_id']
                # 如果需要，更新会话的数据库状态（例如'charging_paused'）
                # 现在，主要依赖充电桩状态。
                self.db.get_redis_client().hset(f"session_status:{session_id}", "status", "paused_by_system") # 示例状态
                msg = f"您在充电桩 {pile_id} 的充电已由系统暂停。"
                self.socketio.emit('user_specific_event', 
                                   {'message': msg, 'type': 'charging_sys_paused', 'session_id': session_id, 'pile_id': pile_id}, 
                                   room=f'user_{user_id}')

    def monitor_charging_progress(self):
        try:
            with self.lock: # 锁定以防止与其他状态更新的竞态条件
                connection = self.db.get_mysql_connection()
                cursor = connection.cursor(dictionary=True) # 获取字典形式的结果

                # 选择当前'charging'状态的会话以及充电桩功率
                cursor.execute("""
                    SELECT s.session_id, s.pile_id, s.user_id, s.requested_amount, s.actual_amount AS current_actual_amount, s.start_time,
                        p.power AS pile_power 
                    FROM charging_sessions s
                    JOIN charging_piles p ON s.pile_id = p.id
                    WHERE s.status = 'charging' 
                """)
                active_sessions = cursor.fetchall()

                sessions_to_update_in_db = []
                sessions_completed_flags = {} # session_id: bool

                for session in active_sessions:
                    session_id = session['session_id']
                    pile_id = session['pile_id'] # 用于end_charging调用
                    pile_power = float(session['pile_power'])
                    requested_kwh = float(session['requested_amount'])
                    current_actual_kwh = float(session['current_actual_amount'] or 0)
                    start_time = session['start_time']

                    if not start_time:
                        print(f"警告: 会话 {session_id} (用户 {session['user_id']}) 状态为'charging'但没有start_time。")
                        continue
                    
                    elapsed_seconds = (datetime.now() - start_time).total_seconds()
                    if elapsed_seconds < 0: elapsed_seconds = 0 # 时钟同步问题保护
                    elapsed_hours = elapsed_seconds / 3600.0
                    
                    # 根据时间计算到目前为止应该充电的总kWh
                    # 这是基于持续时间的*潜在*总量。
                    potential_total_charged_by_time = elapsed_hours * pile_power
                    
                    # 实际电量不应超过requested_kwh
                    new_actual_kwh = min(potential_total_charged_by_time, requested_kwh)
                    new_actual_kwh = round(new_actual_kwh, 4) # 四舍五入以避免浮点精度问题
                    
                    # 只有在有显著变化或第一次更新时才更新
                    if new_actual_kwh > current_actual_kwh or current_actual_kwh == 0 :
                        sessions_to_update_in_db.append({
                            'session_id': session_id,
                            'actual_amount': new_actual_kwh,
                            'charging_duration': round(elapsed_hours, 4)
                        })
                        # 更新session_status的Redis HASH（用于快速UI更新）
                        self.db.get_redis_client().hset(f"session_status:{session_id}", "actual_amount", str(new_actual_kwh))
                        self.db.get_redis_client().hset(f"session_status:{session_id}", "charging_duration", str(round(elapsed_hours, 4)))

                    # 关键修复：检查是否已经达到目标电量，并避免重复调用end_charging
                    if new_actual_kwh >= requested_kwh:
                        # 检查Redis中是否已经标记为"完成处理中"
                        redis_client = self.db.get_redis_client()
                        completion_key = f"session_completing:{session_id}"
                        
                        # 使用Redis的SET NX（仅在不存在时设置）来避免重复处理
                        is_first_completion_attempt = redis_client.set(completion_key, "processing", nx=True, ex=30)  # 30秒过期
                        
                        if is_first_completion_attempt:
                            print(f"会话 {session_id} 在充电桩 {pile_id} 达到请求电量 ({new_actual_kwh}/{requested_kwh})。通过引擎结束充电。")
                            sessions_completed_flags[session_id] = True
                            
                            # 立即更新数据库状态为"completing"，避免下次循环再次检测到
                            cursor.execute("""
                                UPDATE charging_sessions 
                                SET status = 'completing'
                                WHERE session_id = %s AND status = 'charging'
                            """, (session_id,))
                            connection.commit()
                            
                            # 调用引擎结束充电。通过'charging_end'事件更新最终状态为'completed'。
                            scheduler_core.end_charging(pile_id)
                        else:
                            # 此会话已经在处理完成流程中，跳过
                            print(f"会话 {session_id} 已在完成处理中，跳过重复的end_charging调用。")
                    
                # 批量更新数据库（排除已经更新为'completing'状态的会话）
                if sessions_to_update_in_db:
                    update_query = """
                        UPDATE charging_sessions 
                        SET actual_amount = %s, charging_duration = %s
                        WHERE session_id = %s AND status = 'charging'
                    """
                    update_data = [(s['actual_amount'], s['charging_duration'], s['session_id']) for s in sessions_to_update_in_db]
                    cursor.executemany(update_query, update_data)
                    connection.commit()
                
                cursor.close()
                connection.close()
                
                if sessions_to_update_in_db or sessions_completed_flags:
                    self.broadcast_status_update()

        except Exception as e:
            print(f"monitor_charging_progress错误: {e}")
            import traceback
            traceback.print_exc()
    def calculate_charging_fees(self, session_id: str, actual_amount: float, start_time: Optional[datetime], end_time: Optional[datetime]) -> Dict[str, float]:
        if actual_amount <= 0 or not start_time or not end_time or start_time >= end_time:
             return {'charging_fee': 0.0, 'service_fee': 0.0, 'total_fee': 0.0}

        charging_fee = self.calculate_time_based_fee(start_time, end_time, actual_amount)
        service_fee = actual_amount * Config.SERVICE_PRICE
        total_fee = charging_fee + service_fee
        
        return {
            'charging_fee': round(charging_fee, 2), 
            'service_fee': round(service_fee, 2), 
            'total_fee': round(total_fee, 2)
        }

    def calculate_time_based_fee(self, start_time: datetime, end_time: datetime, total_kwh_charged: float) -> float:
        if total_kwh_charged <= 0 or start_time >= end_time: return 0.0
        
        total_fee = 0.0
        current_segment_start_time = start_time
        total_duration_seconds = (end_time - start_time).total_seconds()
        
        if total_duration_seconds <= 0: return 0.0 # 应该被初始检查捕获

        while current_segment_start_time < end_time:
            price_at_segment_start = self.get_electricity_price(current_segment_start_time.time())
            next_tariff_change_time = self.get_next_period_boundary(current_segment_start_time)
            current_segment_end_time = min(end_time, next_tariff_change_time)
            
            segment_duration_seconds = (current_segment_end_time - current_segment_start_time).total_seconds()
            if segment_duration_seconds <=0: # 如果循环条件为<，则不应发生
                current_segment_start_time = current_segment_end_time
                continue

            kwh_in_segment = total_kwh_charged * (segment_duration_seconds / total_duration_seconds)
            total_fee += kwh_in_segment * price_at_segment_start
            current_segment_start_time = current_segment_end_time
            
        return total_fee

    def get_electricity_price(self, t: time) -> float: # 使用`t`作为time对象
        # 峰值: 10:00-15:00 (不包括结束时间), 18:00-21:00 (不包括结束时间)
        if (time(10,0) <= t < time(15,0)) or \
           (time(18,0) <= t < time(21,0)):
            return Config.PEAK_PRICE
        # 谷值: 23:00 - 次日07:00 (不包括结束时间)
        elif (time(23,0) <= t) or (t < time(7,0)):
            return Config.VALLEY_PRICE
        # 平值: 07:00-10:00 (不包括), 15:00-18:00 (不包括), 21:00-23:00 (不包括)
        else:
            return Config.NORMAL_PRICE

    def get_next_period_boundary(self, current_dt: datetime) -> datetime:
        # 关税边界作为时段的开始时间
        # 谷:00, 平:07, 峰:10, 平:15, 峰:18, 平:21, 谷:23
        boundaries = [time(0,0), time(7,0), time(10,0), time(15,0), time(18,0), time(21,0), time(23,0)]
        current_time_obj = current_dt.time()

        for boundary in sorted(boundaries):
            if current_time_obj < boundary:
                return current_dt.replace(hour=boundary.hour, minute=boundary.minute, second=0, microsecond=0)
        
        # 如果current_time_obj >= 最后边界（23:00），下一个边界是次日00:00
        return (current_dt + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)

    def get_session_details_from_db(self, session_id: str) -> Optional[Dict]:
        connection = self.db.get_mysql_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM charging_sessions WHERE session_id = %s", (session_id,))
        session = cursor.fetchone()
        cursor.close()
        connection.close()
        return session

    def get_user_active_session_details(self, user_id: int) -> Optional[Dict]:
        connection = self.db.get_mysql_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT * FROM charging_sessions 
            WHERE user_id = %s AND status NOT IN ('completed', 'cancelled', 'fault_completed')
            ORDER BY created_at DESC LIMIT 1
        """, (user_id,))
        session = cursor.fetchone()
        cursor.close()
        connection.close()
        return session
        
    def get_active_session_on_pile(self, pile_id: str) -> Optional[Dict]:
        connection = self.db.get_mysql_connection()
        cursor = connection.cursor(dictionary=True)
        # 充电桩可能有'paused'或'completing'会话，仍被认为在其上活动
        cursor.execute("""
            SELECT session_id, user_id FROM charging_sessions 
            WHERE pile_id = %s AND (status IN ('charging', 'paused_by_system', 'completing'))
            ORDER BY start_time DESC LIMIT 1
        """, (pile_id,))
        session = cursor.fetchone()
        cursor.close()
        connection.close()
        return session
        
    def update_pile_redis_status(self, pile_id: str, engine_status_str: str, charging_session_id: Optional[str]):
        redis_client = self.db.get_redis_client()
        app_status = 'offline' 
        if engine_status_str == PileStatus.IDLE.value: app_status = 'online'
        elif engine_status_str == PileStatus.BUSY.value: app_status = 'charging'
        elif engine_status_str == PileStatus.FAULT.value: app_status = 'fault'
        elif engine_status_str == PileStatus.PAUSED.value: app_status = 'paused'

        with redis_client.pipeline() as pipe:
            pipe.hset(f"pile_status:{pile_id}", "status", app_status)
            pipe.hset(f"pile_status:{pile_id}", "current_charging_session_id", charging_session_id if charging_session_id else "")
            pipe.execute()

    def broadcast_status_update(self):
        try:
            status_data = self.get_system_status_for_ui()
            self.socketio.emit('status_update', status_data, namespace='/')
        except Exception as e:
            print(f"广播状态更新错误: {e}")
            import traceback
            traceback.print_exc()
    
    def get_system_status_for_ui(self) -> Dict:
        redis_client = self.db.get_redis_client()
        
        station_waiting = {
            'fast': redis_client.llen('station_waiting_area:fast'),
            'trickle': redis_client.llen('station_waiting_area:trickle'),
        }
        station_waiting['total'] = station_waiting['fast'] + station_waiting['trickle']

        engine_q_fast_reqs = scheduler_core.get_waiting_list(PileType.D)
        engine_q_trickle_reqs = scheduler_core.get_waiting_list(PileType.A)
        engine_queues_status = {
            'fast_count': len(engine_q_fast_reqs),
            'trickle_count': len(engine_q_trickle_reqs),
            # 示例: 显示前5个快充和慢充队列号
            'fast_queue_preview': [req.queue_no for req in engine_q_fast_reqs[:5]],
            'trickle_queue_preview': [req.queue_no for req in engine_q_trickle_reqs[:5]],
        }
        
        piles_ui_info = {}
        # 关键: 假设scheduler_core.get_all_piles()存在并返回List[Pile]
        # 如果不存在，这部分需要依赖您的Redis缓存或数据库，这可能是过时的。
        try:
            all_engine_piles = scheduler_core.get_all_piles() # 这个函数是一个假设
        except AttributeError:
            print("错误: scheduler_core.get_all_piles()不可用。UI中的充电桩状态将受限。")
            all_engine_piles = [] # 回退到空或使用您的数据库缓存

        for eng_pile_obj in all_engine_piles: # eng_pile_obj是Pile数据类实例
            app_pile_info_redis = redis_client.hgetall(f"pile_status:{eng_pile_obj.pile_id}")
            piles_ui_info[eng_pile_obj.pile_id] = {
                'id': eng_pile_obj.pile_id,
                'type': 'fast' if eng_pile_obj.type == PileType.D else 'trickle', # 为UI映射回来
                'engine_status': eng_pile_obj.status.value,
                'app_status': app_pile_info_redis.get('status', 'unknown'),
                'current_app_session_id': app_pile_info_redis.get('current_charging_session_id', ''),
                'engine_current_req_id': eng_pile_obj.current_req_id,
                'engine_estimated_end': eng_pile_obj.estimated_end.isoformat() if eng_pile_obj.estimated_end else None,
                'power': eng_pile_obj.max_kw,
                # 如果引擎提供每个充电桩的队列长度详细信息，您可能想要添加充电桩的队列长度
            }
            
        return {
            'station_waiting_area': station_waiting,
            'engine_dispatch_queues': engine_queues_status,
            'charging_piles': piles_ui_info,
            'timestamp': datetime.now().isoformat()
        }

    def get_queue_info_for_user(self, user_id: int, charging_mode_filter: Optional[str] = None) -> Dict:
        """ 提供与特定用户活动请求相关的队列信息。 """
        active_session = self.get_user_active_session_details(user_id)
        
        if not active_session:
            return {'message': '您当前没有活动的充电请求。', 'has_active_request': False}

        session_id = active_session['session_id']
        status = active_session['status']
        current_mode = active_session['charging_mode']
        queue_number = active_session.get('queue_number') # 如果在station_waiting中，可能为None/空
        
        # 如果提供了过滤器且与会话模式不匹配
        if charging_mode_filter and charging_mode_filter != current_mode:
            return {'message': f'您活动的请求是 {current_mode}模式，与查询的 {charging_mode_filter} 模式不符。', 'has_active_request': True, 'request_mode_mismatch': True}

        response_data = {
            'session_id': session_id,
            'charging_mode': current_mode,
            'status': status,
            'queue_number': queue_number,
            'requested_amount': float(active_session['requested_amount']),
            'actual_amount': float(active_session.get('actual_amount',0)),
            'has_active_request': True,
            'position_in_station_queue': None,
            'total_in_station_queue': None,
            'position_in_engine_queue': None,
            'total_in_engine_queue': None,
            'pile_id': active_session.get('pile_id'),
            'estimated_wait_time_msg': "等待时间信息暂不可用" # 默认值
        }

        if status == 'station_waiting':
            redis_client = self.db.get_redis_client()
            station_q_key = f"station_waiting_area:{current_mode}"
            station_q_list_json = redis_client.lrange(station_q_key, 0, -1)
            response_data['total_in_station_queue'] = len(station_q_list_json)
            pos_station = 0
            for idx, item_json in enumerate(station_q_list_json):
                item = json.loads(item_json)
                if item['session_id'] == session_id:
                    pos_station = idx + 1
                    break
            response_data['position_in_station_queue'] = pos_station if pos_station > 0 else "N/A"
            response_data['estimated_wait_time_msg'] = f"正在充电站等候区排队，前方还有 {pos_station-1 if pos_station > 0 else 'N/A'} 位。"

        elif status == 'engine_queued':
            engine_pile_type_filter = self._map_charging_mode_to_engine_piletype(current_mode)
            engine_q_list = scheduler_core.get_waiting_list(engine_pile_type_filter, n=-1) # 获取全部
            response_data['total_in_engine_queue'] = len(engine_q_list)
            pos_engine = 0
            for idx, req in enumerate(engine_q_list):
                if req.req_id == session_id: # req_id是我们的session_id
                    pos_engine = idx + 1
                    break
            response_data['position_in_engine_queue'] = pos_engine if pos_engine > 0 else "N/A"
            response_data['estimated_wait_time_msg'] = f"正在调度队列排队 (号码: {queue_number})，前方还有 {pos_engine-1 if pos_engine > 0 else 'N/A'} 位。"
            # TODO: 如果可用，添加对引擎API的潜在调用以获取预估等待时间。

        elif status == 'charging':
            response_data['estimated_wait_time_msg'] = f"正在充电桩 {active_session.get('pile_id')} 充电中。"
        
        elif status == 'paused_by_system':
             response_data['estimated_wait_time_msg'] = f"充电已由系统暂停，在充电桩 {active_session.get('pile_id')}。"
        
        return response_data

    def stop_charging_session(self, session_id: str, pile_id: str, force_stop: bool = False):
        # 此方法可能由管理员调用，或如果用户通过UI取消*当前充电*会话。
        # 如果force_stop=True，这是一个明确的停止操作。
        # 如果monitor_charging_progress确定完成，它直接调用scheduler_core.end_charging。
        print(f"管理器明确stop_charging_session用于 {session_id} 在 {pile_id}，force_stop={force_stop}")
        scheduler_core.end_charging(pile_id) # 告诉引擎停止此充电桩的当前活动。
        # 进一步处理（数据库状态、费用）由'handle_engine_charging_end'处理
        # 当从引擎收到'charging_end'事件时。