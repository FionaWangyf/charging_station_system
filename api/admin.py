from flask import Blueprint, request, jsonify
from flask import current_app
from datetime import datetime
import scheduler_core
from scheduler_core import PileStatus

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/api/admin/piles', methods=['GET'])
def get_piles():
    '''获取充电桩状态'''
    return jsonify({
        'success': True,
        'message': '获取充电桩状态',
        'data': {
            'piles': []
        }
    })

@admin_bp.route('/api/admin/piles/<pile_id>/control', methods=['POST'])
def control_pile(pile_id):
    '''控制充电桩（启动/关闭）'''
    data = request.json
    action = data.get('action')  # 'start' or 'stop'
    
    return jsonify({
        'success': True,
        'message': f'充电桩{pile_id}已{action}',
        'data': {
            'pile_id': pile_id,
            'status': 'online' if action == 'start' else 'offline'
        }
    })

@admin_bp.route('/api/admin/reports', methods=['GET'])
def get_reports():
    '''获取报表数据'''
    return jsonify({
        'success': True,
        'message': '获取报表数据',
        'data': {
            'reports': []
        }
    })

@admin_bp.route('/api/admin/system/config', methods=['GET', 'POST'])
def system_config():
    '''系统配置管理'''
    if request.method == 'GET':
        return jsonify({
            'success': True,
            'data': {
                'fast_charging_pile_num': 2,
                'trickle_charging_pile_num': 3,
                'waiting_area_size': 6,
                'charging_queue_len': 2
            }
        })
    else:
        # 更新配置
        return jsonify({
            'success': True,
            'message': '配置更新成功'
        })

@admin_bp.route('/api/admin/force_sync_states', methods=['POST'])
def force_sync_states():
    """管理员接口：强制同步引擎与应用状态"""
    charging_manager = current_app.extensions['charging_manager']
    try:
        # 执行状态同步
        charging_manager.force_sync_engine_pile_states()
        # 强制检查超时会话
        charging_manager.check_and_recover_timeout_completing_sessions()
        # 获取同步后的状态
        system_status = charging_manager.get_system_status_for_ui() if hasattr(charging_manager, 'get_system_status_for_ui') else {}
        return jsonify({
            'success': True,
            'message': '状态同步完成',
            'system_status': system_status
        })
    except Exception as e:
        print(f"强制状态同步失败: {e}")
        return jsonify({
            'success': False,
            'message': f'状态同步失败: {str(e)}'
        }), 500

@admin_bp.route('/api/admin/reset_pile_state', methods=['POST'])
def reset_pile_state():
    """管理员接口：重置指定充电桩状态"""
    data = request.get_json()
    pile_id = data.get('pile_id')
    if not pile_id:
        return jsonify({'success': False, 'message': '缺少pile_id参数'}), 400
    charging_manager = current_app.extensions['charging_manager']
    try:
        # 强制结束充电桩上的活动
        scheduler_core.end_charging(pile_id)
        # 更新应用状态
        charging_manager.update_pile_redis_status(pile_id, PileStatus.IDLE.value, None)
        # 检查并完成该充电桩上的所有会话
        connection = charging_manager.db.get_mysql_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT session_id, user_id, actual_amount, charging_duration, start_time
            FROM charging_sessions 
            WHERE pile_id = %s AND status IN ('charging', 'completing')
        """, (pile_id,))
        active_sessions = cursor.fetchall()
        for session in active_sessions:
            session_id = session['session_id']
            user_id = session['user_id']
            actual_amount = float(session.get('actual_amount', 0))
            charging_duration = float(session.get('charging_duration', 0))
            start_time = session.get('start_time')
            # 计算费用并完成会话
            fees = charging_manager.calculate_charging_fees(session_id, actual_amount, start_time, datetime.now())
            cursor.execute("""
                UPDATE charging_sessions 
                SET status = 'completed', end_time = %s,
                    charging_fee = %s, service_fee = %s, total_fee = %s
                WHERE session_id = %s
            """, (datetime.now(), fees['charging_fee'], fees['service_fee'], fees['total_fee'], session_id))
            # 清理Redis
            redis_client = charging_manager.db.get_redis_client()
            redis_client.delete(f"session_status:{session_id}")
            redis_client.delete(f"session_completing:{session_id}")
            # 通知用户
            charging_manager.socketio.emit('user_specific_event', {
                'message': f'您的充电会话 {session_id} 已完成（管理员重置）。总费用: {fees["total_fee"]:.2f}元。',
                'type': 'charging_completed_admin_reset',
                'session_id': session_id,
                'total_fee': fees['total_fee']
            }, room=f'user_{user_id}')
        connection.commit()
        cursor.close()
        connection.close()
        charging_manager.broadcast_status_update()
        return jsonify({
            'success': True,
            'message': f'充电桩 {pile_id} 状态已重置',
            'completed_sessions': len(active_sessions)
        })
    except Exception as e:
        print(f"重置充电桩状态失败: {e}")
        return jsonify({
            'success': False,
            'message': f'重置失败: {str(e)}'
        }), 500
    
@admin_bp.route('/api/admin/db_pool_status', methods=['GET'])
def get_db_pool_status():
    """获取数据库连接池状态"""
    charging_manager = current_app.extensions['charging_manager']
    try:
        pool_status = charging_manager.db.get_pool_status()
        return jsonify({
            'success': True,
            'data': pool_status
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取连接池状态失败: {str(e)}'
        }), 500