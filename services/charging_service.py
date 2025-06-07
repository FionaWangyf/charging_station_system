import json
import threading
import uuid
import redis
from datetime import datetime, timedelta, time
from typing import List, Dict, Optional
from threading import Lock
from apscheduler.schedulers.background import BackgroundScheduler

from models.user import db
from models.charging import ChargingSession, ChargingMode, ChargingStatus
from models.billing import ChargingPile
from config import get_config
import scheduler_core
from scheduler_core import PileType, PileStatus, Pile, ChargeRequest

class ChargingService:
    """充电服务类 - 整合C模块的核心逻辑"""
    
    def __init__(self, app=None, socketio=None):
        self.app = app
        self.socketio = socketio
        self.lock = Lock()
        self.config = get_config()
        
        # Redis客户端
        self.redis_client = redis.Redis(
            host=self.config.REDIS_HOST,
            port=self.config.REDIS_PORT,
            db=self.config.REDIS_DB,
            password=self.config.REDIS_PASSWORD,
            decode_responses=True
        )
        
        # 调度器
        self.scheduler = BackgroundScheduler()
        self.scheduler.start()
        
        # 如果传入了app，立即初始化；否则等待延迟初始化
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """初始化应用"""
        self.app = app
        
        with app.app_context():
            # 初始化
            self.init_redis_data()
            self.init_piles_in_engine()
            self.startup_state_sync()
            
            # 定时任务
            self._setup_scheduled_jobs()
            
            # 启动调度引擎
            scheduler_core.start_dispatch_loop()
            
            print("=" * 60)
            print("充电服务已启动")
            print("=" * 60)
    
    def _setup_scheduled_jobs(self):
        """设置定时任务"""
        def _with_app_context(func):
            def wrapper(*args, **kwargs):
                with self.app.app_context():
                    return func(*args, **kwargs)
            return wrapper

        jobs = [
            {
                "id": "engine_event_poller",
                "func": _with_app_context(self.poll_and_process_engine_events),
                "trigger": "interval",
                "seconds": 2
            },
            {
                "id": "charging_monitor",
                "func": self.monitor_charging_progress,
                "trigger": "interval",
                "seconds": 10,
                "misfire_grace_time": 5
            },
            {
                "id": "station_to_engine_queue_processor",
                "func": self.process_station_waiting_area_to_engine,
                "trigger": "interval",
                "seconds": 5,
                "misfire_grace_time": 3
            },
            {
                "id": "timeout_completing_checker",
                "func": self.check_and_recover_timeout_completing_sessions,
                "trigger": "interval",
                "seconds": 60,
                "misfire_grace_time": 10
            }
        ]
        
        for job in jobs:
            if self.scheduler.get_job(job["id"]):
                self.scheduler.remove_job(job["id"])
            self.scheduler.add_job(**job)
    
    def init_redis_data(self):
        """初始化Redis数据"""
        self.redis_client.delete('station_waiting_area:fast', 'station_waiting_area:trickle')
        
        # 从数据库获取充电桩数据并注册到引擎
        piles = ChargingPile.query.all()
        
        for pile_db in piles:
            if pile_db.status == 'offline':
                print(f"充电桩 {pile_db.id} 处于离线状态，暂不添加到调度引擎。")
                continue
            
            # 根据scheduler_core定义：D=直流(快充), A=交流(慢充)
            engine_pile_type = PileType.D if pile_db.pile_type == 'fast' else PileType.A
            engine_status = PileStatus.IDLE
            
            if pile_db.status == 'fault':
                engine_status = PileStatus.FAULT
            
            pile_for_engine = Pile(
                pile_id=pile_db.id,
                type=engine_pile_type,
                max_kw=float(pile_db.power_rating),
                status=engine_status
            )
            scheduler_core.add_pile(pile_for_engine)
        
        print("充电桩已注册到调度引擎。")
    
    def init_piles_in_engine(self):
        """初始化引擎中的充电桩"""
        pass
    
    def startup_state_sync(self):
        """启动时的状态同步"""
        try:
            print("执行启动状态同步...")
            
            # 处理所有completing状态的会话
            completing_sessions = ChargingSession.query.filter_by(
                status=ChargingStatus.COMPLETING
            ).all()
            
            for session in completing_sessions:
                print(f"启动时发现completing会话: {session.session_id}，强制完成")
                
                fees = self.calculate_charging_fees(
                    session.session_id,
                    float(session.actual_amount or 0),
                    session.start_time,
                    datetime.now()
                )
                
                session.status = ChargingStatus.COMPLETED
                session.end_time = datetime.now()
                session.charging_fee = fees['charging_fee']
                session.service_fee = fees['service_fee']
                session.total_fee = fees['total_fee']
                
                # 清理Redis
                self.redis_client.delete(f"session_status:{session.session_id}")
                self.redis_client.delete(f"session_completing:{session.session_id}")
                
                if session.pile_id:
                    try:
                        scheduler_core.end_charging(session.pile_id)
                    except:
                        pass
                    self.update_pile_redis_status(session.pile_id, PileStatus.IDLE.value, None)
            
            db.session.commit()
            
            # 强制同步所有充电桩状态
            import time
            time.sleep(1)
            self.force_sync_engine_pile_states()
            
            if completing_sessions:
                print(f"启动时完成了 {len(completing_sessions)} 个completing会话")
            print("启动状态同步完成")
            
        except Exception as e:
            db.session.rollback()
            print(f"启动状态同步出错: {e}")
            import traceback
            traceback.print_exc()
    
    def submit_charging_request(self, user_id: int, charging_mode: str, requested_amount: float) -> Dict:
        """提交充电请求"""
        try:
            with self.lock:
                # 检查等候区容量
                fast_count = self.redis_client.llen('station_waiting_area:fast')
                trickle_count = self.redis_client.llen('station_waiting_area:trickle')
                
                if (fast_count + trickle_count) >= self.config.WAITING_AREA_SIZE:
                    return {'success': False, 'message': '等候区已满，请稍后再试', 'code': 2001}
                
                # 检查用户是否有活跃会话
                existing_session = self.get_user_active_session_details(user_id)
                if existing_session and existing_session.status not in [ChargingStatus.COMPLETED, ChargingStatus.CANCELLED]:
                    return {'success': False, 'message': '您已有进行中的充电会话或请求', 'code': 2002}
                
                # 创建新会话
                session_id = str(uuid.uuid4())
                
                new_session = ChargingSession(
                    session_id=session_id,
                    user_id=user_id,
                    charging_mode=ChargingMode(charging_mode),
                    requested_amount=requested_amount,
                    status=ChargingStatus.STATION_WAITING
                )
                
                db.session.add(new_session)
                db.session.commit()
                
                # 添加到Redis队列
                request_data = {
                    'session_id': session_id,
                    'user_id': user_id,
                    'charging_mode': charging_mode,
                    'requested_amount': requested_amount,
                    'created_at': datetime.now().isoformat()
                }
                self.redis_client.rpush(f"station_waiting_area:{charging_mode}", json.dumps(request_data))
                
                # 更新Redis状态
                self.redis_client.hset(f"session_status:{session_id}", mapping={
                    'user_id': str(user_id),
                    'charging_mode': charging_mode,
                    'requested_amount': str(requested_amount),
                    'status': 'station_waiting',
                    'queue_number': ""
                })
                
                # WebSocket通知
                if self.socketio:
                    self.socketio.emit('user_specific_event', 
                                    {'message': f'请求 {session_id} 已提交至充电站等候区', 
                                     'session_id': session_id, 
                                     'type': 'request_submitted_station'}, 
                                    room=f'user_{user_id}')
                
                # 异步处理队列
                def delayed_process():
                    import time
                    time.sleep(0.1)
                    self.process_station_waiting_area_to_engine()
                    self.broadcast_status_update()
                
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
            db.session.rollback()
            print(f"提交充电请求错误: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'message': '系统错误，请稍后重试', 'code': 5001}
    
    def get_user_active_session_details(self, user_id: int) -> Optional[ChargingSession]:
        """获取用户活跃会话详情"""
        return ChargingSession.query.filter_by(user_id=user_id)\
            .filter(~ChargingSession.status.in_([ChargingStatus.COMPLETED, ChargingStatus.CANCELLED, ChargingStatus.FAULT_COMPLETED]))\
            .order_by(ChargingSession.created_at.desc()).first()
    
    def process_station_waiting_area_to_engine(self):
        """将请求从充电站等候区移动到引擎队列"""
        with self.lock:
            for mode in ['fast', 'trickle']:
                station_queue_key = f"station_waiting_area:{mode}"
                request_json = self.redis_client.lpop(station_queue_key)
                
                if request_json:
                    request_data = json.loads(request_json)
                    session_id = request_data['session_id']
                    
                    # 验证数据库状态
                    session = ChargingSession.query.filter_by(session_id=session_id).first()
                    if not session or session.status != ChargingStatus.STATION_WAITING:
                        print(f"会话 {session_id} 状态不符合预期，跳过处理")
                        continue
                    
                    # 生成队列号并添加到引擎
                    engine_pile_type = self._map_charging_mode_to_engine_piletype(request_data['charging_mode'])
                    engine_queue_no = scheduler_core.generate_queue_number(engine_pile_type.value)  # 使用.value获取字符串
                    
                    engine_req = ChargeRequest(
                        req_id=session_id,
                        queue_no=engine_queue_no,
                        user_id=request_data['user_id'],
                        pile_type=engine_pile_type,
                        kwh=float(request_data['requested_amount']),
                        generated_at=datetime.fromisoformat(request_data['created_at'])
                    )
                    
                    scheduler_core.enqueue_request(engine_req)
                    
                    # 更新数据库
                    session.status = ChargingStatus.ENGINE_QUEUED
                    session.queue_number = engine_queue_no
                    db.session.commit()
                    
                    # 更新Redis
                    self.redis_client.hset(f"session_status:{session_id}", mapping={
                        "status": "engine_queued",
                        "queue_number": engine_queue_no
                    })
                    
                    print(f"将会话 {session_id} 移动到引擎的 {mode} 队列，队列号为 {engine_queue_no}")
                    
                    # WebSocket通知
                    if self.socketio:
                        self.socketio.emit('user_specific_event', 
                                         {'message': f'请求 {session_id} ({engine_queue_no}) 已进入调度队列', 
                                          'session_id': session_id, 
                                          'queue_number': engine_queue_no, 
                                          'type': 'request_queued_engine'}, 
                                         room=f"user_{request_data['user_id']}")
                    
                    self.broadcast_status_update()
    
    def _map_charging_mode_to_engine_piletype(self, charging_mode: str) -> PileType:
        """映射充电模式到引擎桩类型"""
        # 根据scheduler_core的定义：D=直流(快充), A=交流(慢充)
        return PileType.D if charging_mode == 'fast' else PileType.A
    
    def poll_and_process_engine_events(self):
        """轮询和处理引擎事件"""
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
                    
                    session = ChargingSession.query.filter_by(session_id=session_id).first()
                    if session and session.status == ChargingStatus.CANCELLING_AFTER_DISPATCH:
                        print(f"会话 {session_id} 被标记为取消，调度后立即结束")
                        scheduler_core.end_charging(pile_id)
                    else:
                        self.handle_engine_dispatch(session_id, pile_id, start_time_dt)
                
                elif event_type == "charging_end":
                    session_id = None
                    pile_id = None
                    
                    if hasattr(event_data, 'req_id'):
                        session_id = event_data.req_id
                        pile_id = event_data.pile_id
                    elif isinstance(event_data, dict):
                        session_id = event_data.get('req_id')
                        pile_id = event_data.get('pile_id')
                    elif isinstance(event_data, str):
                        pile_id = event_data
                    
                    if session_id:
                        self.handle_engine_charging_end(session_id, pile_id, graceful_end=True)
                    elif pile_id:
                        self.handle_pile_end_without_session_id(pile_id)
                
                elif event_type == "pile_fault":
                    pile_id = event_data
                    self.handle_engine_pile_fault(pile_id)
                
                elif event_type == "pile_recover":
                    pile_id = event_data
                    self.handle_engine_pile_recover(pile_id)
            
            if events:
                self.broadcast_status_update()
            
            self.check_and_recover_timeout_completing_sessions()
            
        except Exception as e:
            print(f"轮询引擎事件错误: {e}")
            import traceback
            traceback.print_exc()
    
    def handle_engine_dispatch(self, session_id: str, pile_id: str, engine_start_time: datetime):
        """处理引擎调度事件"""
        with self.lock:
            print(f"处理调度: 会话 {session_id} 到充电桩 {pile_id}")
            
            session = ChargingSession.query.filter_by(session_id=session_id).first()
            if session:
                session.pile_id = pile_id
                session.status = ChargingStatus.CHARGING
                session.start_time = engine_start_time
                session.actual_amount = 0
                session.charging_duration = 0
                db.session.commit()
                
                self.update_pile_redis_status(pile_id, PileStatus.BUSY.value, session_id)
                
                # 更新Redis状态
                self.redis_client.hset(f"session_status:{session_id}", mapping={
                    "status": "charging",
                    "pile_id": pile_id,
                    "start_time": engine_start_time.isoformat(),
                    "actual_amount": "0",
                    "charging_duration": "0"
                })
                
                # WebSocket通知
                if self.socketio:
                    msg = f"您的请求 {session.queue_number} ({session_id}) 已开始在充电桩 {pile_id} 充电。"
                    self.socketio.emit('user_specific_event', 
                                     {'message': msg, 
                                      'type': 'charging_started', 
                                      'session_id': session_id, 
                                      'pile_id': pile_id, 
                                      'start_time': engine_start_time.isoformat()}, 
                                     room=f'user_{session.user_id}')
    
    def monitor_charging_progress(self):
        """监控充电进度"""
        try:
            with self.lock:
                active_sessions = db.session.query(ChargingSession)\
                    .join(ChargingPile, ChargingSession.pile_id == ChargingPile.id)\
                    .filter(ChargingSession.status == ChargingStatus.CHARGING)\
                    .all()
                
                sessions_to_update = []
                
                for session in active_sessions:
                    if not session.start_time:
                        continue
                    
                    elapsed_seconds = (datetime.now() - session.start_time).total_seconds()
                    elapsed_hours = max(0, elapsed_seconds / 3600.0)
                    
                    # 获取充电桩功率
                    pile_power = float(session.pile.power_rating)
                    
                    # 计算实际充电量
                    potential_total_charged = elapsed_hours * pile_power
                    new_actual_kwh = min(potential_total_charged, float(session.requested_amount))
                    new_actual_kwh = round(new_actual_kwh, 4)
                    
                    if new_actual_kwh > float(session.actual_amount or 0):
                        session.actual_amount = new_actual_kwh
                        session.charging_duration = round(elapsed_hours, 4)
                        sessions_to_update.append(session)
                        
                        # 更新Redis
                        self.redis_client.hset(f"session_status:{session.session_id}", 
                                             "actual_amount", str(new_actual_kwh))
                        self.redis_client.hset(f"session_status:{session.session_id}", 
                                             "charging_duration", str(round(elapsed_hours, 4)))
                    
                    # 检查是否达到请求电量
                    if new_actual_kwh >= float(session.requested_amount):
                        completion_key = f"session_completing:{session.session_id}"
                        
                        is_first_completion = self.redis_client.set(completion_key, "processing", nx=True, ex=30)
                        
                        if is_first_completion:
                            print(f"会话 {session.session_id} 达到请求电量，通过引擎结束充电")
                            
                            session.status = ChargingStatus.COMPLETING
                            
                            try:
                                scheduler_core.end_charging(session.pile_id)
                                print(f"已向引擎发送end_charging指令: {session.pile_id}")
                            except Exception as engine_error:
                                print(f"向引擎发送end_charging指令失败: {engine_error}")
                                self.redis_client.set(f"force_complete:{session.session_id}", "true", ex=60)
                
                if sessions_to_update:
                    db.session.commit()
                    self.broadcast_status_update()
                    
        except Exception as e:
            db.session.rollback()
            print(f"监控充电进度错误: {e}")
            import traceback
            traceback.print_exc()
    
    def handle_engine_charging_end(self, session_id: str, pile_id: str, graceful_end: bool = True):
        """处理引擎充电结束事件"""
        with self.lock:
            print(f"处理充电结束: 会话 {session_id} 在充电桩 {pile_id}")
            
            # 清理Redis完成标志
            completion_key = f"session_completing:{session_id}"
            self.redis_client.delete(completion_key)
            
            session = ChargingSession.query.filter_by(session_id=session_id).first()
            if not session:
                print(f"未找到会话 {session_id}")
                self.update_pile_redis_status(pile_id, PileStatus.IDLE.value, None)
                return
            
            # 确定最终状态
            current_status = session.status
            final_status = ChargingStatus.COMPLETED
            
            if current_status == ChargingStatus.CANCELLING_AFTER_DISPATCH or not graceful_end:
                final_status = ChargingStatus.CANCELLED
            
            # 计算费用
            actual_amount = float(session.actual_amount or 0)
            charging_duration_hours = float(session.charging_duration or 0)
            
            fees = self.calculate_charging_fees(
                session_id, 
                actual_amount, 
                session.start_time, 
                datetime.now()
            )
            
            # 更新会话
            session.status = final_status
            session.end_time = datetime.now()
            session.charging_fee = fees['charging_fee']
            session.service_fee = fees['service_fee']
            session.total_fee = fees['total_fee']
            session.actual_amount = actual_amount
            session.charging_duration = charging_duration_hours
            
            # 更新充电桩统计
            if session.pile:
                session.pile.total_charges += 1
                session.pile.total_power += actual_amount
                session.pile.total_revenue += fees['total_fee']
            
            db.session.commit()
            
            # 更新状态
            self.update_pile_redis_status(pile_id, PileStatus.IDLE.value, None)
            self.redis_client.delete(f"session_status:{session_id}")
            
            # WebSocket通知
            if self.socketio:
                msg = f"您的充电请求 {session.queue_number} ({session_id}) 已在充电桩 {pile_id} {final_status.value}。总费用: {fees['total_fee']:.2f}元。"
                self.socketio.emit('user_specific_event', {
                    'message': msg, 
                    'type': 'charging_ended', 
                    'session_id': session_id,
                    'pile_id': pile_id, 
                    'total_fee': fees['total_fee'], 
                    'status': final_status.value,
                    'actual_amount': actual_amount, 
                    'charging_duration': charging_duration_hours
                }, room=f'user_{session.user_id}')
            
            # 触发下一轮处理
            self.process_station_waiting_area_to_engine()
    
    def handle_pile_end_without_session_id(self, pile_id: str):
        """处理只有pile_id的充电结束事件"""
        with self.lock:
            session = ChargingSession.query.filter_by(pile_id=pile_id)\
                .filter(ChargingSession.status.in_([ChargingStatus.COMPLETING, ChargingStatus.CHARGING]))\
                .order_by(ChargingSession.start_time.desc()).first()
            
            if session:
                print(f"找到充电桩 {pile_id} 上的会话 {session.session_id}")
                self.handle_engine_charging_end(session.session_id, pile_id, graceful_end=True)
            else:
                print(f"充电桩 {pile_id} 上未找到活跃会话，仅更新充电桩状态")
                self.update_pile_redis_status(pile_id, PileStatus.IDLE.value, None)
    
    def handle_engine_pile_fault(self, pile_id: str):
        """处理充电桩故障事件"""
        with self.lock:
            print(f"处理充电桩故障: 充电桩 {pile_id}")
            
            # 更新充电桩状态
            pile = ChargingPile.query.get(pile_id)
            if pile:
                pile.status = 'fault'
            
            # 处理该充电桩上的活跃会话
            active_session = ChargingSession.query.filter_by(pile_id=pile_id)\
                .filter_by(status=ChargingStatus.CHARGING).first()
            
            if active_session:
                actual_amount = float(active_session.actual_amount or 0)
                fees = self.calculate_charging_fees(
                    active_session.session_id,
                    actual_amount,
                    active_session.start_time,
                    datetime.now()
                )
                
                active_session.status = ChargingStatus.FAULT_COMPLETED
                active_session.pile_id = None
                active_session.end_time = datetime.now()
                active_session.charging_fee = fees['charging_fee']
                active_session.service_fee = fees['service_fee']
                active_session.total_fee = fees['total_fee']
                
                # 清理Redis
                self.redis_client.delete(f"session_status:{active_session.session_id}")
                
                # WebSocket通知
                if self.socketio:
                    msg = f"充电桩 {pile_id} 发生故障。您的充电请求已中断。已充电量 {actual_amount:.2f} kWh，费用 {fees['total_fee']:.2f}元。"
                    self.socketio.emit('user_specific_event', {
                        'message': msg, 
                        'type': 'session_fault_stopped',
                        'session_id': active_session.session_id,
                        'pile_id': pile_id, 
                        'partial_amount': actual_amount, 
                        'partial_fees': fees
                    }, room=f'user_{active_session.user_id}')
            
            db.session.commit()
            self.update_pile_redis_status(pile_id, PileStatus.FAULT.value, None)
    
    def handle_engine_pile_recover(self, pile_id: str):
        """处理充电桩恢复事件"""
        with self.lock:
            print(f"处理充电桩恢复: 充电桩 {pile_id}")
            
            pile = ChargingPile.query.get(pile_id)
            if pile:
                pile.status = 'available'
                db.session.commit()
            
            self.update_pile_redis_status(pile_id, PileStatus.IDLE.value, None)
            self.process_station_waiting_area_to_engine()
    
    def check_and_recover_timeout_completing_sessions(self):
        """检查和恢复超时的completing状态会话"""
        lock_key = "timeout_check_lock"
        
        if not self.redis_client.set(lock_key, "processing", nx=True, ex=15):
            return
        
        try:
            timeout_threshold = datetime.now() - timedelta(seconds=60)
            
            timeout_sessions = ChargingSession.query.filter(
                ChargingSession.status == ChargingStatus.COMPLETING,
                ChargingSession.start_time < timeout_threshold
            ).all()
            
            if not timeout_sessions:
                return
            
            print(f"发现 {len(timeout_sessions)} 个超时的completing会话，开始恢复...")
            
            recovered_count = 0
            for session in timeout_sessions:
                # 双重检查状态
                if session.status != ChargingStatus.COMPLETING:
                    continue
                
                print(f"恢复超时会话: {session.session_id}")
                
                actual_amount = float(session.actual_amount or 0)
                fees = self.calculate_charging_fees(
                    session.session_id,
                    actual_amount,
                    session.start_time,
                    datetime.now()
                )
                
                session.status = ChargingStatus.COMPLETED
                session.end_time = datetime.now()
                session.charging_fee = fees['charging_fee']
                session.service_fee = fees['service_fee']
                session.total_fee = fees['total_fee']
                
                recovered_count += 1
                
                # 更新充电桩统计
                if session.pile:
                    session.pile.total_charges += 1
                    session.pile.total_power += actual_amount
                    session.pile.total_revenue += fees['total_fee']
                    
                    try:
                        scheduler_core.end_charging(session.pile_id)
                    except:
                        pass
                    
                    self.update_pile_redis_status(session.pile_id, PileStatus.IDLE.value, None)
                
                # 清理Redis
                self.redis_client.delete(f"session_status:{session.session_id}")
                self.redis_client.delete(f"session_completing:{session.session_id}")
                
                # 通知用户
                if self.socketio:
                    self.socketio.emit('user_specific_event', {
                        'message': f'您的充电会话已完成。总费用: {fees["total_fee"]:.2f}元。',
                        'type': 'charging_completed_recovery',
                        'session_id': session.session_id,
                        'total_fee': fees['total_fee'],
                        'actual_amount': actual_amount
                    }, room=f'user_{session.user_id}')
            
            if recovered_count > 0:
                db.session.commit()
                print(f"成功恢复了 {recovered_count} 个超时会话")
                self.broadcast_status_update()
                self.process_station_waiting_area_to_engine()
            
        except Exception as e:
            db.session.rollback()
            print(f"检查超时completing会话错误: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.redis_client.delete(lock_key)
    
    def force_sync_engine_pile_states(self):
        """强制同步引擎与应用的充电桩状态"""
        try:
            print("开始强制同步引擎充电桩状态...")
            
            try:
                all_engine_piles = scheduler_core.get_all_piles()
            except AttributeError:
                print("警告: scheduler_core.get_all_piles()不可用，跳过强制同步")
                return
            
            for pile in all_engine_piles:
                pile_id = pile.pile_id
                engine_status = pile.status
                current_req_id = pile.current_req_id
                
                if engine_status == PileStatus.BUSY and current_req_id:
                    active_session = ChargingSession.query.filter_by(
                        session_id=current_req_id,
                        status=ChargingStatus.CHARGING
                    ).first()
                    
                    if not active_session:
                        print(f"检测到状态不一致: 充电桩 {pile_id} 引擎状态为BUSY但无活跃会话，强制释放")
                        scheduler_core.end_charging(pile_id)
                        self.update_pile_redis_status(pile_id, PileStatus.IDLE.value, None)
                    else:
                        print(f"充电桩 {pile_id} 状态正常: 引擎BUSY且有活跃会话 {current_req_id}")
                
                elif engine_status == PileStatus.IDLE:
                    self.update_pile_redis_status(pile_id, PileStatus.IDLE.value, None)
                    print(f"同步充电桩 {pile_id} 状态为IDLE")
            
            print("强制同步完成")
            
        except Exception as e:
            print(f"强制同步引擎状态时出错: {e}")
            import traceback
            traceback.print_exc()
    
    def calculate_charging_fees(self, session_id: str, actual_amount: float, 
                               start_time: Optional[datetime], end_time: Optional[datetime]) -> Dict[str, float]:
        """计算充电费用"""
        if actual_amount <= 0 or not start_time or not end_time or start_time >= end_time:
            return {'charging_fee': 0.0, 'service_fee': 0.0, 'total_fee': 0.0}
        
        # 使用现有的计费服务
        from services.billing_service import BillingService
        billing_result = BillingService.calculate_billing(start_time, end_time, actual_amount)
        
        return {
            'charging_fee': billing_result['electricity_fee'],
            'service_fee': billing_result['service_fee'],
            'total_fee': billing_result['total_fee']
        }
    
    def update_pile_redis_status(self, pile_id: str, engine_status_str: str, charging_session_id: Optional[str]):
        """更新充电桩Redis状态"""
        app_status = 'offline'
        if engine_status_str == PileStatus.IDLE.value:
            app_status = 'available'
        elif engine_status_str == PileStatus.BUSY.value:
            app_status = 'occupied'
        elif engine_status_str == PileStatus.FAULT.value:
            app_status = 'fault'
        elif engine_status_str == PileStatus.PAUSED.value:
            app_status = 'maintenance'
        
        with self.redis_client.pipeline() as pipe:
            pipe.hset(f"pile_status:{pile_id}", "status", app_status)
            pipe.hset(f"pile_status:{pile_id}", "current_charging_session_id", 
                     charging_session_id if charging_session_id else "")
            pipe.execute()
    
    def broadcast_status_update(self):
        """广播状态更新"""
        try:
            broadcast_lock_key = "broadcast_lock"
            
            if self.redis_client.exists(broadcast_lock_key):
                return
            
            self.redis_client.set(broadcast_lock_key, "1", ex=1)
            
            if self.socketio:
                status_data = self.get_system_status_for_ui()
                self.socketio.emit('status_update', status_data, namespace='/')
            
        except Exception as e:
            print(f"广播状态更新错误: {e}")
    
    def get_system_status_for_ui(self) -> Dict:
        """获取系统状态用于UI显示"""
        station_waiting = {
            'fast': self.redis_client.llen('station_waiting_area:fast'),
            'trickle': self.redis_client.llen('station_waiting_area:trickle'),
        }
        station_waiting['total'] = station_waiting['fast'] + station_waiting['trickle']
        
        try:
            engine_q_fast_reqs = scheduler_core.get_waiting_list(PileType.D.value)  # 使用.value
            engine_q_trickle_reqs = scheduler_core.get_waiting_list(PileType.A.value)  # 使用.value
        except:
            engine_q_fast_reqs = []
            engine_q_trickle_reqs = []
        
        engine_queues_status = {
            'fast_count': len(engine_q_fast_reqs),
            'trickle_count': len(engine_q_trickle_reqs),
            'fast_queue_preview': [req.queue_no for req in engine_q_fast_reqs[:5]],
            'trickle_queue_preview': [req.queue_no for req in engine_q_trickle_reqs[:5]],
        }
        
        piles_ui_info = {}
        try:
            all_engine_piles = scheduler_core.get_all_piles()
        except AttributeError:
            all_engine_piles = []
        
        for eng_pile_obj in all_engine_piles:
            app_pile_info_redis = self.redis_client.hgetall(f"pile_status:{eng_pile_obj.pile_id}")
            piles_ui_info[eng_pile_obj.pile_id] = {
                'id': eng_pile_obj.pile_id,
                'type': 'fast' if eng_pile_obj.type == PileType.D else 'trickle',  # 根据调度引擎类型映射
                'engine_status': eng_pile_obj.status.value,
                'app_status': app_pile_info_redis.get('status', 'unknown'),
                'current_app_session_id': app_pile_info_redis.get('current_charging_session_id', ''),
                'engine_current_req_id': eng_pile_obj.current_req_id,
                'engine_estimated_end': eng_pile_obj.estimated_end.isoformat() if eng_pile_obj.estimated_end else None,
                'power': eng_pile_obj.max_kw,
            }
        
        return {
            'station_waiting_area': station_waiting,
            'engine_dispatch_queues': engine_queues_status,
            'charging_piles': piles_ui_info,
            'timestamp': datetime.now().isoformat()
        }
    
    def get_queue_info_for_user(self, user_id: int, charging_mode_filter: Optional[str] = None) -> Dict:
        """获取用户队列信息"""
        active_session = self.get_user_active_session_details(user_id)
        
        if not active_session:
            return {'message': '您当前没有活动的充电请求。', 'has_active_request': False}
        
        session_id = active_session.session_id
        status = active_session.status.value
        current_mode = active_session.charging_mode.value
        queue_number = active_session.queue_number
        
        if charging_mode_filter and charging_mode_filter != current_mode:
            return {
                'message': f'您活动的请求是 {current_mode}模式，与查询的 {charging_mode_filter} 模式不符。', 
                'has_active_request': True, 
                'request_mode_mismatch': True
            }
        
        response_data = {
            'session_id': session_id,
            'charging_mode': current_mode,
            'status': status,
            'queue_number': queue_number,
            'requested_amount': float(active_session.requested_amount),
            'actual_amount': float(active_session.actual_amount or 0),
            'has_active_request': True,
            'position_in_station_queue': None,
            'total_in_station_queue': None,
            'position_in_engine_queue': None,
            'total_in_engine_queue': None,
            'pile_id': active_session.pile_id,
            'estimated_wait_time_msg': "等待时间信息暂不可用"
        }
        
        if status == 'station_waiting':
            station_q_key = f"station_waiting_area:{current_mode}"
            station_q_list_json = self.redis_client.lrange(station_q_key, 0, -1)
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
            try:
                engine_q_list = scheduler_core.get_waiting_list(engine_pile_type_filter.value, n=-1)  # 使用.value
                response_data['total_in_engine_queue'] = len(engine_q_list)
                
                pos_engine = 0
                for idx, req in enumerate(engine_q_list):
                    if req.req_id == session_id:
                        pos_engine = idx + 1
                        break
                
                response_data['position_in_engine_queue'] = pos_engine if pos_engine > 0 else "N/A"
                response_data['estimated_wait_time_msg'] = f"正在调度队列排队 (号码: {queue_number})，前方还有 {pos_engine-1 if pos_engine > 0 else 'N/A'} 位。"
            except:
                response_data['estimated_wait_time_msg'] = f"正在调度队列排队 (号码: {queue_number})。"
        
        elif status == 'charging':
            response_data['estimated_wait_time_msg'] = f"正在充电桩 {active_session.pile_id} 充电中。"
        
        return response_data