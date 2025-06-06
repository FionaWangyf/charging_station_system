from flask import Blueprint, request, jsonify, current_app

charging_bp = Blueprint('charging', __name__)

# 1. 用户提交充电请求
@charging_bp.route('/api/charging/request', methods=['POST'])
def charging_request():
    data = request.get_json()
    user_id = data.get('user_id')
    charging_mode = data.get('charging_mode')
    requested_amount = data.get('requested_amount')
    if not all([user_id, charging_mode, requested_amount]):
        return jsonify({'success': False, 'message': '参数缺失'}), 400
    charging_manager = current_app.extensions['charging_manager']
    result = charging_manager.submit_charging_request(user_id, charging_mode, float(requested_amount))
    return jsonify(result)

# 2. 用户修改充电请求
@charging_bp.route('/api/charging/request/modify', methods=['POST'])
def modify_charging_request():
    data = request.get_json()
    session_id = data.get('session_id')
    user_id = data.get('user_id')
    new_mode = data.get('charging_mode')
    new_amount = data.get('requested_amount')
    if not session_id or not user_id:
        return jsonify({'success': False, 'message': '参数缺失'}), 400
    charging_manager = current_app.extensions['charging_manager']
    result = charging_manager.modify_charging_request(
        session_id, user_id, new_charging_mode=new_mode, new_requested_amount=new_amount
    )
    return jsonify(result)

# 3. 用户取消充电请求
@charging_bp.route('/api/charging/request/cancel', methods=['POST'])
def cancel_charging_request():
    data = request.get_json()
    session_id = data.get('session_id')
    user_id = data.get('user_id')
    if not session_id or not user_id:
        return jsonify({'success': False, 'message': '参数缺失'}), 400
    charging_manager = current_app.extensions['charging_manager']
    result = charging_manager.cancel_charging_request(session_id, user_id)
    return jsonify(result)

# 4. 查询用户排队/充电状态
@charging_bp.route('/api/charging/status', methods=['GET'])
def charging_status():
    user_id = request.args.get('user_id', type=int)
    if not user_id:
        return jsonify({'success': False, 'message': '参数缺失'}), 400
    charging_manager = current_app.extensions['charging_manager']
    result = charging_manager.get_queue_info_for_user(user_id)
    return jsonify(result)

# 5. 查询全局充电桩与队列状态（前端大屏/管理用）
@charging_bp.route('/api/charging/system_status', methods=['GET'])
def system_status():
    charging_manager = current_app.extensions['charging_manager']
    result = charging_manager.get_system_status_for_ui()
    return jsonify(result)

# 6. 管理员/用户主动结束充电
@charging_bp.route('/api/charging/stop', methods=['POST'])
def stop_charging():
    data = request.get_json()
    session_id = data.get('session_id')
    pile_id = data.get('pile_id')
    if not session_id or not pile_id:
        return jsonify({'success': False, 'message': '参数缺失'}), 400
    charging_manager = current_app.extensions['charging_manager']
    charging_manager.stop_charging_session(session_id, pile_id, force_stop=True)
    return jsonify({'success': True, 'message': '已发送停止充电指令'})

# 7. 充电桩状态监控（WebSocket由charging_control自动推送，无需额外接口）

# 8. 充电桩手动暂停（可选，管理员用）
@charging_bp.route('/api/charging/pause', methods=['POST'])
def pause_charging():
    data = request.get_json()
    pile_id = data.get('pile_id')
    # charging_manager = current_app.extensions['charging_manager']
    # charging_manager.pause_charging_pile(pile_id)
    return jsonify({'success': False, 'message': '暂停功能待实现'})

# 9. 充电桩状态查询（单个桩）
@charging_bp.route('/api/charging/pile_status', methods=['GET'])
def pile_status():
    pile_id = request.args.get('pile_id')
    if not pile_id:
        return jsonify({'success': False, 'message': '参数缺失'}), 400
    charging_manager = current_app.extensions['charging_manager']
    status = charging_manager.get_system_status_for_ui().get('charging_piles', {}).get(pile_id)
    if not status:
        return jsonify({'success': False, 'message': '未找到该充电桩'}), 404
    return jsonify({'success': True, 'data': status})