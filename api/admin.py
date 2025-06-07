from flask import Blueprint, request, session, current_app
from datetime import datetime, timedelta
from utils.response import success_response, error_response, validation_error_response
from utils.validators import validate_required_fields
from functools import wraps

# 创建蓝图
admin_bp = Blueprint('admin', __name__)

def login_required(f):
    """登录验证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return error_response("请先登录", code=401, error_type="LOGIN_REQUIRED")
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """管理员权限验证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return error_response("请先登录", code=401, error_type="LOGIN_REQUIRED")
        
        user_type = session.get('user_type')
        if user_type != 'admin':
            return error_response("需要管理员权限", code=403, error_type="PERMISSION_DENIED")
        
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/test', methods=['GET'])
@admin_required
def test():
    """测试接口"""
    return success_response(data={'message': '管理员API正常运行'})

@admin_bp.route('/pile/start', methods=['POST'])
@admin_required
def start_pile():
    """启动指定充电桩"""
    try:
        data = request.get_json()
        if not data:
            return error_response("请求数据不能为空")
        
        pile_id = data.get('pile_id', '').strip()
        if not pile_id:
            return error_response("充电桩ID不能为空")
        
        from models.billing import ChargingPile
        from scheduler_core import PileType, PileStatus as EnginePileStatus, Pile
        import scheduler_core
        
        # 检查充电桩是否存在
        pile = ChargingPile.query.get(pile_id)
        if not pile:
            return error_response("充电桩不存在", code=404)
        
        if pile.status == 'available':
            return error_response("充电桩已经在线", code=400)
        
        # 更新数据库状态
        pile.status = 'available'
        
        # 添加到调度引擎
        # 根据scheduler_core定义：D=直流(快充), A=交流(慢充)
        engine_pile_type = PileType.D if pile.pile_type == 'fast' else PileType.A
        pile_for_engine = Pile(
            pile_id=pile.id,
            type=engine_pile_type,
            max_kw=float(pile.power_rating),
            status=EnginePileStatus.IDLE
        )
        
        try:
            scheduler_core.add_pile(pile_for_engine)
        except Exception as e:
            print(f"添加充电桩到引擎失败: {e}")
        
        # 更新Redis状态
        charging_service = current_app.extensions.get('charging_service')
        if charging_service:
            charging_service.update_pile_redis_status(pile_id, EnginePileStatus.IDLE.value, None)
            charging_service.broadcast_status_update()
        
        from models.user import db
        db.session.commit()
        
        return success_response(data={
            'pile_id': pile_id,
            'status': 'available'
        }, message=f'充电桩 {pile_id} 已启动')
    
    except Exception as e:
        from models.user import db
        db.session.rollback()
        print(f"启动充电桩错误: {e}")
        return error_response("系统错误", code=500)

@admin_bp.route('/pile/stop', methods=['POST'])
@admin_required
def stop_pile():
    """关闭指定充电桩"""
    try:
        data = request.get_json()
        if not data:
            return error_response("请求数据不能为空")
        
        pile_id = data.get('pile_id', '').strip()
        force = data.get('force', False)
        
        if not pile_id:
            return error_response("充电桩ID不能为空")
        
        from models.billing import ChargingPile
        from models.charging import ChargingSession, ChargingStatus
        from scheduler_core import PileType
        import scheduler_core
        
        # 检查充电桩状态
        pile = ChargingPile.query.get(pile_id)
        if not pile:
            return error_response("充电桩不存在", code=404)
        
        if pile.status == 'offline':
            return error_response("充电桩已经离线", code=400)
        
        # 检查是否有正在充电的会话
        active_sessions = ChargingSession.query.filter_by(pile_id=pile_id)\
            .filter(ChargingSession.status.in_([ChargingStatus.CHARGING, ChargingStatus.COMPLETING]))\
            .all()
        
        if active_sessions and not force:
            session_info = []
            for session in active_sessions:
                session_info.append({
                    'session_id': session.session_id,
                    'user_id': session.user_id,
                    'status': session.status.value
                })
            return error_response(
                "充电桩有正在进行的充电会话，请先完成或强制关闭",
                code=400
            )
        
        # 如果强制关闭，先结束所有活跃会话
        if active_sessions and force:
            for session in active_sessions:
                print(f"强制关闭充电桩 {pile_id}，结束会话 {session.session_id}")
                try:
                    scheduler_core.end_charging(pile_id)
                except Exception as e:
                    print(f"结束充电时出错: {e}")
        
        # 更新数据库状态
        pile.status = 'offline'
        
        # 从调度引擎移除
        try:
            scheduler_core.remove_pile(pile_id)
        except (AttributeError, Exception) as e:
            print(f"从引擎移除充电桩失败: {e}")
        
        # 更新Redis状态
        charging_service = current_app.extensions.get('charging_service')
        if charging_service:
            charging_service.update_pile_redis_status(pile_id, 'offline', None)
            charging_service.broadcast_status_update()
        
        from models.user import db
        db.session.commit()
        
        return success_response(data={
            'pile_id': pile_id,
            'status': 'offline',
            'forced_stop_sessions': len(active_sessions) if force else 0
        }, message=f'充电桩 {pile_id} 已关闭')
    
    except Exception as e:
        from models.user import db
        db.session.rollback()
        print(f"关闭充电桩错误: {e}")
        return error_response("系统错误", code=500)

@admin_bp.route('/piles/status', methods=['GET'])
@admin_required
def get_all_piles_status():
    """获取所有充电桩的详细状态信息"""
    try:
        from models.billing import ChargingPile
        from models.charging import ChargingSession, ChargingStatus
        from core import scheduler_core
        
        # 获取所有充电桩
        piles = ChargingPile.query.order_by(ChargingPile.id).all()
        
        piles_status = []
        charging_service = current_app.extensions.get('charging_service')
        
        for pile in piles:
            pile_id = pile.id
            
            # 获取Redis中的实时状态
            redis_status = {}
            if charging_service:
                redis_status = charging_service.redis_client.hgetall(f"pile_status:{pile_id}")
            
            current_session_id = redis_status.get('current_charging_session_id', '')
            
            # 获取当前充电会话信息
            current_session = None
            if current_session_id:
                current_session = ChargingSession.query.filter_by(session_id=current_session_id).first()
            
            # 获取引擎状态
            engine_status = None
            engine_estimated_end = None
            try:
                all_engine_piles = scheduler_core.get_all_piles()
                for engine_pile in all_engine_piles:
                    if engine_pile.pile_id == pile_id:
                        engine_status = engine_pile.status.value
                        engine_estimated_end = engine_pile.estimated_end.isoformat() if engine_pile.estimated_end else None
                        break
            except (AttributeError, Exception):
                pass
            
            pile_info = {
                'id': pile_id,
                'name': pile.name,
                'type': pile.pile_type,
                'power': float(pile.power_rating),
                'db_status': pile.status,
                'redis_status': redis_status.get('status', 'unknown'),
                'engine_status': engine_status,
                'location': pile.location or '',
                'statistics': {
                    'total_charges': pile.total_charges,
                    'total_power': float(pile.total_power),
                    'total_revenue': float(pile.total_revenue)
                },
                'current_session': None,
                'engine_info': {
                    'estimated_end': engine_estimated_end
                }
            }
            
            if current_session:
                pile_info['current_session'] = {
                    'session_id': current_session.session_id,
                    'user_id': current_session.user_id,
                    'requested_amount': float(current_session.requested_amount),
                    'actual_amount': float(current_session.actual_amount or 0),
                    'start_time': current_session.start_time.isoformat() if current_session.start_time else None,
                    'charging_duration': float(current_session.charging_duration or 0),
                    'status': current_session.status.value
                }
            
            piles_status.append(pile_info)
        
        return success_response(data={
            'piles': piles_status,
            'total_piles': len(piles_status),
            'timestamp': datetime.now().isoformat()
        }, message="获取充电桩状态成功")
    
    except Exception as e:
        print(f"获取充电桩状态错误: {e}")
        import traceback
        traceback.print_exc()
        return error_response("系统错误", code=500)

@admin_bp.route('/queue/info', methods=['GET'])
@admin_required
def get_queue_info():
    """获取所有等候队列中的车辆信息"""
    try:
        from scheduler_core import PileType
        import scheduler_core
        import json
        
        charging_service = current_app.extensions.get('charging_service')
        if not charging_service:
            return error_response("充电服务不可用", code=503)
        
        queue_info = {
            'station_waiting_area': {
                'fast': [],
                'trickle': []
            },
            'engine_dispatch_queues': {
                'fast': [],
                'trickle': []
            },
            'charging_sessions': []
        }
        
        # 1. 获取充电站等候区信息
        for mode in ['fast', 'trickle']:
            station_queue_key = f"station_waiting_area:{mode}"
            queue_items = charging_service.redis_client.lrange(station_queue_key, 0, -1)
            
            for idx, item_json in enumerate(queue_items):
                item = json.loads(item_json)
                queue_info['station_waiting_area'][mode].append({
                    'position': idx + 1,
                    'session_id': item['session_id'],
                    'user_id': item['user_id'],
                    'requested_amount': float(item['requested_amount']),
                    'created_at': item['created_at'],
                    'waiting_time_minutes': (datetime.now() - datetime.fromisoformat(item['created_at'])).total_seconds() / 60
                })
        
        # 2. 获取引擎调度队列信息
        try:
            fast_engine_queue = scheduler_core.get_waiting_list(PileType.D.value, n=-1)  # 使用.value
            trickle_engine_queue = scheduler_core.get_waiting_list(PileType.A.value, n=-1)  # 使用.value
            
            for idx, req in enumerate(fast_engine_queue):
                queue_info['engine_dispatch_queues']['fast'].append({
                    'position': idx + 1,
                    'queue_number': req.queue_no,
                    'session_id': req.req_id,
                    'user_id': req.user_id,
                    'requested_amount': float(req.kwh),
                    'generated_at': req.generated_at.isoformat() if req.generated_at else None,
                    'waiting_time_minutes': (datetime.now() - req.generated_at).total_seconds() / 60 if req.generated_at else 0
                })
            
            for idx, req in enumerate(trickle_engine_queue):
                queue_info['engine_dispatch_queues']['trickle'].append({
                    'position': idx + 1,
                    'queue_number': req.queue_no,
                    'session_id': req.req_id,
                    'user_id': req.user_id,
                    'requested_amount': float(req.kwh),
                    'generated_at': req.generated_at.isoformat() if req.generated_at else None,
                    'waiting_time_minutes': (datetime.now() - req.generated_at).total_seconds() / 60 if req.generated_at else 0
                })
        
        except (AttributeError, Exception) as e:
            print(f"获取引擎队列信息失败: {e}")
        
        # 3. 获取正在充电的会话信息
        from models.charging import ChargingSession, ChargingStatus
        from models.billing import ChargingPile
        from models.user import db
        
        charging_sessions = db.session.query(ChargingSession)\
            .join(ChargingPile, ChargingSession.pile_id == ChargingPile.id)\
            .filter(ChargingSession.status.in_([ChargingStatus.CHARGING, ChargingStatus.COMPLETING]))\
            .order_by(ChargingSession.start_time.desc()).all()
        
        for session in charging_sessions:
            session_info = {
                'session_id': session.session_id,
                'user_id': session.user_id,
                'pile_id': session.pile_id,
                'pile_type': session.pile.pile_type,
                'pile_power': float(session.pile.power_rating),
                'requested_amount': float(session.requested_amount),
                'actual_amount': float(session.actual_amount or 0),
                'progress_percentage': (float(session.actual_amount or 0) / float(session.requested_amount)) * 100,
                'start_time': session.start_time.isoformat() if session.start_time else None,
                'charging_duration_hours': float(session.charging_duration or 0),
                'status': session.status.value
            }
            
            # 计算预估剩余时间
            if session.start_time and session.status == ChargingStatus.CHARGING:
                remaining_kwh = float(session.requested_amount) - float(session.actual_amount or 0)
                pile_power = float(session.pile.power_rating)
                if pile_power > 0 and remaining_kwh > 0:
                    estimated_remaining_hours = remaining_kwh / pile_power
                    session_info['estimated_remaining_hours'] = round(estimated_remaining_hours, 2)
                else:
                    session_info['estimated_remaining_hours'] = 0
            
            queue_info['charging_sessions'].append(session_info)
        
        # 4. 汇总统计
        summary = {
            'total_waiting_station': len(queue_info['station_waiting_area']['fast']) + len(queue_info['station_waiting_area']['trickle']),
            'total_waiting_engine': len(queue_info['engine_dispatch_queues']['fast']) + len(queue_info['engine_dispatch_queues']['trickle']),
            'total_charging': len(queue_info['charging_sessions']),
            'fast_waiting_station': len(queue_info['station_waiting_area']['fast']),
            'fast_waiting_engine': len(queue_info['engine_dispatch_queues']['fast']),
            'trickle_waiting_station': len(queue_info['station_waiting_area']['trickle']),
            'trickle_waiting_engine': len(queue_info['engine_dispatch_queues']['trickle'])
        }
        
        return success_response(data={
            'queue_info': queue_info,
            'summary': summary,
            'timestamp': datetime.now().isoformat()
        }, message="获取队列信息成功")
    
    except Exception as e:
        print(f"获取队列信息错误: {e}")
        import traceback
        traceback.print_exc()
        return error_response("系统错误", code=500)

@admin_bp.route('/overview', methods=['GET'])
@admin_required
def get_system_overview():
    """获取系统概览统计信息"""
    try:
        from models.billing import ChargingPile
        from models.charging import ChargingSession, ChargingStatus
        from models.user import db, User
        from scheduler_core import PileType
        import scheduler_core
        
        # 充电桩状态统计
        pile_status_stats = db.session.query(
            ChargingPile.status,
            db.func.count(ChargingPile.id).label('count')
        ).group_by(ChargingPile.status).all()
        
        pile_status_counts = {row.status: row.count for row in pile_status_stats}
        
        # 今日统计
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow_start = today_start + timedelta(days=1)
        
        today_stats = db.session.query(
            db.func.count(ChargingSession.id).label('today_sessions'),
            db.func.sum(ChargingSession.actual_amount).label('today_amount'),
            db.func.sum(ChargingSession.total_fee).label('today_revenue')
        ).filter(
            ChargingSession.start_time >= today_start,
            ChargingSession.start_time < tomorrow_start,
            ChargingSession.status.in_([ChargingStatus.COMPLETED, ChargingStatus.CANCELLED, ChargingStatus.FAULT_COMPLETED])
        ).first()
        
        # 本月统计
        month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if month_start.month == 12:
            next_month_start = month_start.replace(year=month_start.year + 1, month=1)
        else:
            next_month_start = month_start.replace(month=month_start.month + 1)
        
        month_stats = db.session.query(
            db.func.count(ChargingSession.id).label('month_sessions'),
            db.func.sum(ChargingSession.actual_amount).label('month_amount'),
            db.func.sum(ChargingSession.total_fee).label('month_revenue')
        ).filter(
            ChargingSession.start_time >= month_start,
            ChargingSession.start_time < next_month_start,
            ChargingSession.status.in_([ChargingStatus.COMPLETED, ChargingStatus.CANCELLED, ChargingStatus.FAULT_COMPLETED])
        ).first()
        
        # 实时队列统计
        charging_service = current_app.extensions.get('charging_service')
        queue_stats = {
            'station_waiting_fast': 0,
            'station_waiting_trickle': 0,
            'engine_fast_queue': 0,
            'engine_trickle_queue': 0
        }
        
        if charging_service:
            queue_stats['station_waiting_fast'] = charging_service.redis_client.llen('station_waiting_area:fast')
            queue_stats['station_waiting_trickle'] = charging_service.redis_client.llen('station_waiting_area:trickle')
            
            try:
                queue_stats['engine_fast_queue'] = len(scheduler_core.get_waiting_list(PileType.D.value))  # 使用.value
                queue_stats['engine_trickle_queue'] = len(scheduler_core.get_waiting_list(PileType.A.value))  # 使用.value
            except:
                pass
        
        # 正在充电的会话数
        active_charging = ChargingSession.query.filter(
            ChargingSession.status.in_([ChargingStatus.CHARGING, ChargingStatus.COMPLETING])
        ).count()
        
        overview = {
            'pile_statistics': {
                'total_piles': sum(pile_status_counts.values()),
                'available_piles': pile_status_counts.get('available', 0),
                'offline_piles': pile_status_counts.get('offline', 0),
                'fault_piles': pile_status_counts.get('fault', 0),
                'maintenance_piles': pile_status_counts.get('maintenance', 0)
            },
            'today_statistics': {
                'sessions': today_stats.today_sessions or 0,
                'amount_kwh': round(float(today_stats.today_amount or 0), 2),
                'revenue': round(float(today_stats.today_revenue or 0), 2)
            },
            'month_statistics': {
                'sessions': month_stats.month_sessions or 0,
                'amount_kwh': round(float(month_stats.month_amount or 0), 2),
                'revenue': round(float(month_stats.month_revenue or 0), 2)
            },
            'queue_statistics': {
                'total_waiting': (queue_stats['station_waiting_fast'] + queue_stats['station_waiting_trickle'] + 
                                queue_stats['engine_fast_queue'] + queue_stats['engine_trickle_queue']),
                'station_waiting': queue_stats['station_waiting_fast'] + queue_stats['station_waiting_trickle'],
                'engine_waiting': queue_stats['engine_fast_queue'] + queue_stats['engine_trickle_queue']
            },
            'active_charging': active_charging
        }
        
        return success_response(data=overview, message="获取系统概览成功")
    
    except Exception as e:
        print(f"获取系统概览失败: {e}")