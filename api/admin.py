from flask import Blueprint, request, jsonify, current_app
from datetime import datetime, timedelta
from models import PileStatus
import scheduler_core
from scheduler_core import PileStatus as EnginePileStatus, PileType
import json
from collections import defaultdict

admin_bp = Blueprint('admin', __name__)

# 1. 启动充电桩
@admin_bp.route('/api/admin/pile/start', methods=['POST'])
def start_pile():
    """启动指定充电桩"""
    data = request.get_json()
    pile_id = data.get('pile_id')
    
    if not pile_id:
        return jsonify({'success': False, 'message': '充电桩ID不能为空'}), 400
    
    try:
        charging_manager = current_app.extensions['charging_manager']
        
        # 检查充电桩是否存在
        with charging_manager.db.get_cursor() as (cursor, connection):
            cursor.execute("SELECT id, status, pile_type, power FROM charging_piles WHERE id = %s", (pile_id,))
            pile = cursor.fetchone()
            
            if not pile:
                return jsonify({'success': False, 'message': '充电桩不存在'}), 404
            
            current_status = pile['status']
            if current_status == 'online':
                return jsonify({'success': False, 'message': '充电桩已经在线'}), 400
            
            # 更新数据库状态
            cursor.execute("UPDATE charging_piles SET status = 'online' WHERE id = %s", (pile_id,))
            
            # 添加到调度引擎
            from scheduler_core import Pile
            engine_pile_type = PileType.D if pile['pile_type'] == 'fast' else PileType.A
            pile_for_engine = Pile(
                pile_id=pile['id'],
                type=engine_pile_type,
                max_kw=float(pile['power']),
                status=EnginePileStatus.IDLE
            )
            
            try:
                scheduler_core.add_pile(pile_for_engine)
            except Exception as e:
                print(f"添加充电桩到引擎失败: {e}")
            
            # 更新Redis状态
            charging_manager.update_pile_redis_status(pile_id, EnginePileStatus.IDLE.value, None)
            
            # 广播状态更新
            charging_manager.broadcast_status_update()
            
            return jsonify({
                'success': True, 
                'message': f'充电桩 {pile_id} 已启动',
                'pile_id': pile_id,
                'status': 'online'
            })
            
    except Exception as e:
        print(f"启动充电桩错误: {e}")
        return jsonify({'success': False, 'message': '系统错误'}), 500

# 2. 关闭充电桩
@admin_bp.route('/api/admin/pile/stop', methods=['POST'])
def stop_pile():
    """关闭指定充电桩"""
    data = request.get_json()
    pile_id = data.get('pile_id')
    force = data.get('force', False)  # 是否强制关闭（即使有正在充电的会话）
    
    if not pile_id:
        return jsonify({'success': False, 'message': '充电桩ID不能为空'}), 400
    
    try:
        charging_manager = current_app.extensions['charging_manager']
        
        # 检查充电桩状态
        with charging_manager.db.get_cursor() as (cursor, connection):
            cursor.execute("SELECT id, status FROM charging_piles WHERE id = %s", (pile_id,))
            pile = cursor.fetchone()
            
            if not pile:
                return jsonify({'success': False, 'message': '充电桩不存在'}), 404
            
            current_status = pile['status']
            if current_status == 'offline':
                return jsonify({'success': False, 'message': '充电桩已经离线'}), 400
            
            # 检查是否有正在充电的会话
            cursor.execute("""
                SELECT session_id, user_id, status FROM charging_sessions 
                WHERE pile_id = %s AND status IN ('charging', 'completing')
            """, (pile_id,))
            active_sessions = cursor.fetchall()
            
            if active_sessions and not force:
                session_info = []
                for session in active_sessions:
                    session_info.append({
                        'session_id': session['session_id'],
                        'user_id': session['user_id'],
                        'status': session['status']
                    })
                return jsonify({
                    'success': False, 
                    'message': '充电桩有正在进行的充电会话，请先完成或强制关闭',
                    'active_sessions': session_info
                }), 400
            
            # 如果强制关闭，先结束所有活跃会话
            if active_sessions and force:
                for session in active_sessions:
                    session_id = session['session_id']
                    print(f"强制关闭充电桩 {pile_id}，结束会话 {session_id}")
                    try:
                        scheduler_core.end_charging(pile_id)
                    except Exception as e:
                        print(f"结束充电时出错: {e}")
            
            # 更新数据库状态
            cursor.execute("UPDATE charging_piles SET status = 'offline' WHERE id = %s", (pile_id,))
            
            # 从调度引擎移除（如果支持的话）
            try:
                scheduler_core.remove_pile(pile_id)
            except AttributeError:
                print("调度引擎不支持移除充电桩操作")
            except Exception as e:
                print(f"从引擎移除充电桩失败: {e}")
            
            # 更新Redis状态
            charging_manager.update_pile_redis_status(pile_id, 'offline', None)
            
            # 广播状态更新
            charging_manager.broadcast_status_update()
            
            return jsonify({
                'success': True, 
                'message': f'充电桩 {pile_id} 已关闭',
                'pile_id': pile_id,
                'status': 'offline',
                'forced_stop_sessions': len(active_sessions) if force else 0
            })
            
    except Exception as e:
        print(f"关闭充电桩错误: {e}")
        return jsonify({'success': False, 'message': '系统错误'}), 500

# 3. 查看所有充电桩状态
@admin_bp.route('/api/admin/piles/status', methods=['GET'])
def get_all_piles_status():
    """获取所有充电桩的详细状态信息"""
    try:
        charging_manager = current_app.extensions['charging_manager']
        
        with charging_manager.db.get_cursor() as (cursor, connection):
            # 获取充电桩基本信息和统计数据
            cursor.execute("""
                SELECT 
                    id, pile_type, power, status, location_info,
                    total_charging_count, total_charging_time, total_charging_amount
                FROM charging_piles 
                ORDER BY id
            """)
            piles = cursor.fetchall()
            
            piles_status = []
            redis_client = charging_manager.db.get_redis_client()
            
            for pile in piles:
                pile_id = pile['id']
                
                # 获取Redis中的实时状态
                redis_status = redis_client.hgetall(f"pile_status:{pile_id}")
                current_session_id = redis_status.get('current_charging_session_id', '')
                
                # 获取当前充电会话信息
                current_session = None
                if current_session_id:
                    cursor.execute("""
                        SELECT session_id, user_id, requested_amount, actual_amount, 
                               start_time, charging_duration, status
                        FROM charging_sessions 
                        WHERE session_id = %s
                    """, (current_session_id,))
                    current_session = cursor.fetchone()
                
                # 获取引擎状态（如果可用）
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
                    'type': pile['pile_type'],
                    'power': float(pile['power']),
                    'db_status': pile['status'],
                    'redis_status': redis_status.get('status', 'unknown'),
                    'engine_status': engine_status,
                    'location_info': pile['location_info'] or '',
                    'statistics': {
                        'total_charging_count': pile['total_charging_count'],
                        'total_charging_time': float(pile['total_charging_time']),
                        'total_charging_amount': float(pile['total_charging_amount'])
                    },
                    'current_session': None,
                    'engine_info': {
                        'estimated_end': engine_estimated_end
                    }
                }
                
                if current_session:
                    pile_info['current_session'] = {
                        'session_id': current_session['session_id'],
                        'user_id': current_session['user_id'],
                        'requested_amount': float(current_session['requested_amount']),
                        'actual_amount': float(current_session.get('actual_amount', 0)),
                        'start_time': current_session['start_time'].isoformat() if current_session['start_time'] else None,
                        'charging_duration': float(current_session.get('charging_duration', 0)),
                        'status': current_session['status']
                    }
                
                piles_status.append(pile_info)
            
            return jsonify({
                'success': True,
                'data': piles_status,
                'total_piles': len(piles_status),
                'timestamp': datetime.now().isoformat()
            })
            
    except Exception as e:
        print(f"获取充电桩状态错误: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': '系统错误'}), 500

# 4. 查看等候车辆信息
@admin_bp.route('/api/admin/queue/info', methods=['GET'])
def get_queue_info():
    """获取所有等候队列中的车辆信息"""
    try:
        charging_manager = current_app.extensions['charging_manager']
        redis_client = charging_manager.db.get_redis_client()
        
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
            queue_items = redis_client.lrange(station_queue_key, 0, -1)
            
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
            fast_engine_queue = scheduler_core.get_waiting_list(PileType.D, n=-1)
            trickle_engine_queue = scheduler_core.get_waiting_list(PileType.A, n=-1)
            
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
        with charging_manager.db.get_cursor() as (cursor, connection):
            cursor.execute("""
                SELECT 
                    s.session_id, s.user_id, s.pile_id, s.requested_amount, 
                    s.actual_amount, s.start_time, s.charging_duration, s.status,
                    p.power as pile_power, p.pile_type
                FROM charging_sessions s
                JOIN charging_piles p ON s.pile_id = p.id
                WHERE s.status IN ('charging', 'completing', 'paused_by_system')
                ORDER BY s.start_time DESC
            """)
            charging_sessions = cursor.fetchall()
            
            for session in charging_sessions:
                session_info = {
                    'session_id': session['session_id'],
                    'user_id': session['user_id'],
                    'pile_id': session['pile_id'],
                    'pile_type': session['pile_type'],
                    'pile_power': float(session['pile_power']),
                    'requested_amount': float(session['requested_amount']),
                    'actual_amount': float(session.get('actual_amount', 0)),
                    'progress_percentage': (float(session.get('actual_amount', 0)) / float(session['requested_amount'])) * 100,
                    'start_time': session['start_time'].isoformat() if session['start_time'] else None,
                    'charging_duration_hours': float(session.get('charging_duration', 0)),
                    'status': session['status']
                }
                
                # 计算预估剩余时间
                if session['start_time'] and session['status'] == 'charging':
                    remaining_kwh = float(session['requested_amount']) - float(session.get('actual_amount', 0))
                    pile_power = float(session['pile_power'])
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
        
        return jsonify({
            'success': True,
            'data': queue_info,
            'summary': summary,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        print(f"获取队列信息错误: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': '系统错误'}), 500

# 报表统计@wtt
# 8. 系统概览统计
@admin_bp.route('/api/admin/overview', methods=['GET'])
def get_system_overview():
    """获取系统概览统计信息"""
    try:
        charging_manager = current_app.extensions['charging_manager']
        
        with charging_manager.db.get_cursor() as (cursor, connection):
            # 充电桩状态统计
            cursor.execute("""
                SELECT status, COUNT(*) as count 
                FROM charging_piles 
                GROUP BY status
            """)
            pile_status_stats = {row['status']: row['count'] for row in cursor.fetchall()}
            
            # 今日统计
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            tomorrow_start = today_start + timedelta(days=1)
            
            cursor.execute("""
                SELECT 
                    COUNT(*) as today_sessions,
                    SUM(actual_amount) as today_amount,
                    SUM(total_fee) as today_revenue
                FROM charging_sessions 
                WHERE start_time >= %s AND start_time < %s 
                    AND status IN ('completed', 'cancelled', 'fault_completed')
            """, (today_start, tomorrow_start))
            today_stats = cursor.fetchone()
            
            # 本月统计
            month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if month_start.month == 12:
                next_month_start = month_start.replace(year=month_start.year + 1, month=1)
            else:
                next_month_start = month_start.replace(month=month_start.month + 1)
            
            cursor.execute("""
                SELECT 
                    COUNT(*) as month_sessions,
                    SUM(actual_amount) as month_amount,
                    SUM(total_fee) as month_revenue
                FROM charging_sessions 
                WHERE start_time >= %s AND start_time < %s 
                    AND status IN ('completed', 'cancelled', 'fault_completed')
            """, (month_start, next_month_start))
            month_stats = cursor.fetchone()
            
            # 实时队列统计
            redis_client = charging_manager.db.get_redis_client()
            queue_stats = {
                'station_waiting_fast': redis_client.llen('station_waiting_area:fast'),
                'station_waiting_trickle': redis_client.llen('station_waiting_area:trickle'),
                'engine_fast_queue': 0,
                'engine_trickle_queue': 0
            }
            
            try:
                queue_stats['engine_fast_queue'] = len(scheduler_core.get_waiting_list(PileType.D))
                queue_stats['engine_trickle_queue'] = len(scheduler_core.get_waiting_list(PileType.A))
            except:
                pass
            
            # 正在充电的会话数
            cursor.execute("""
                SELECT COUNT(*) as active_charging
                FROM charging_sessions 
                WHERE status IN ('charging', 'completing')
            """)
            active_charging = cursor.fetchone()['active_charging']
            
            overview = {
                'pile_statistics': {
                    'total_piles': sum(pile_status_stats.values()),
                    'online_piles': pile_status_stats.get('online', 0),
                    'offline_piles': pile_status_stats.get('offline', 0),
                    'fault_piles': pile_status_stats.get('fault', 0),
                    'maintenance_piles': pile_status_stats.get('maintenance', 0)
                },
                'today_statistics': {
                    'sessions': today_stats['today_sessions'] or 0,
                    'amount_kwh': round(float(today_stats['today_amount'] or 0), 2),
                    'revenue': round(float(today_stats['today_revenue'] or 0), 2)
                },
                'month_statistics': {
                    'sessions': month_stats['month_sessions'] or 0,
                    'amount_kwh': round(float(month_stats['month_amount'] or 0), 2),
                    'revenue': round(float(month_stats['month_revenue'] or 0), 2)
                },
                'queue_statistics': {
                    'total_waiting': (queue_stats['station_waiting_fast'] + queue_stats['station_waiting_trickle'] + 
                                    queue_stats['engine_fast_queue'] + queue_stats['engine_trickle_queue']),
                    'station_waiting': queue_stats['station_waiting_fast'] + queue_stats['station_waiting_trickle'],
                    'engine_waiting': queue_stats['engine_fast_queue'] + queue_stats['engine_trickle_queue'],
                    'active_charging': active_charging,
                    'details': queue_stats
                }
            }
            
            return jsonify({
                'success': True,
                'data': overview,
                'timestamp': datetime.now().isoformat()
            })
            
    except Exception as e:
        print(f"获取系统概览错误: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': '系统错误'}), 500

# 9. 强制同步系统状态
@admin_bp.route('/api/admin/sync/force', methods=['POST'])
def force_sync_system():
    """强制同步系统状态（管理员维护功能）"""
    try:
        charging_manager = current_app.extensions['charging_manager']
        
        # 执行强制状态同步
        charging_manager.force_sync_engine_pile_states()
        
        # 检查超时会话
        charging_manager.check_and_recover_timeout_completing_sessions()
        
        # 处理等候区到引擎的转移
        charging_manager.process_station_waiting_area_to_engine()
        
        # 广播状态更新
        charging_manager.broadcast_status_update()
        
        return jsonify({
            'success': True,
            'message': '系统状态同步完成',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        print(f"强制同步系统状态错误: {e}")
        return jsonify({'success': False, 'message': '系统错误'}), 500