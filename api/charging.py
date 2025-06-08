from flask import Blueprint, request, session, current_app
from utils.response import success_response, error_response, validation_error_response
from utils.validators import validate_required_fields
from functools import wraps

# 创建蓝图
charging_bp = Blueprint('charging', __name__)

def login_required(f):
    """登录验证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return error_response("请先登录", code=401, error_type="LOGIN_REQUIRED")
        return f(*args, **kwargs)
    return decorated_function

@charging_bp.route('/test', methods=['GET'])
def test():
    """测试接口"""
    return success_response(data={'message': '充电API正常运行'})

@charging_bp.route('/request', methods=['POST'])
@login_required
def submit_charging_request():
    """用户提交充电请求"""
    
    try:
        # 添加充电服务状态检查
        charging_service = current_app.extensions.get('charging_service')
        if not charging_service:
            return error_response("充电服务不可用", code=503)
        
        # 检查初始化状态
        if not hasattr(charging_service, '_initialized') or not charging_service._initialized:
            return error_response("充电服务正在初始化中，请稍后重试", code=503)
        
        user_id = session.get('user_id')
        data = request.get_json()
        
        if not data:
            return error_response("请求数据不能为空")
        
        # 验证必要字段
        required_fields = ['charging_mode', 'requested_amount']
        errors = validate_required_fields(data, required_fields)
        
        if errors:
            return validation_error_response(errors)
        
        charging_mode = data.get('charging_mode', '').strip()
        requested_amount = data.get('requested_amount')
        
        # 验证充电模式
        if charging_mode not in ['fast', 'trickle']:
            errors['charging_mode'] = "充电模式必须是 'fast' 或 'trickle'"
        
        # 验证充电量
        try:
            requested_amount = float(requested_amount)
            if requested_amount <= 0:
                errors['requested_amount'] = "充电量必须大于0"
            elif requested_amount > 200:  # 假设最大200kWh
                errors['requested_amount'] = "充电量不能超过200kWh"
        except (ValueError, TypeError):
            errors['requested_amount'] = "充电量必须是有效数字"
        
        if errors:
            return validation_error_response(errors)
        
        # 获取充电服务实例
        charging_service = current_app.extensions.get('charging_service')
        if not charging_service:
            return error_response("充电服务不可用", code=503)
        
        # 提交充电请求
        result = charging_service.submit_charging_request(user_id, charging_mode, requested_amount)
        
        if result.get('success'):
            return success_response(
                data=result.get('data'),
                message=result.get('message'),
                code=201
            )
        else:
            return error_response(
                message=result.get('message', '充电请求失败'),
                code=result.get('code', 400)
            )
    
    except Exception as e:
        print(f"提交充电请求错误: {e}")
        return error_response("系统错误，请稍后重试", code=500)

@charging_bp.route('/request/modify', methods=['PUT'])
@login_required
def modify_charging_request():
    """修改充电请求"""
    try:
        user_id = session.get('user_id')
        data = request.get_json()
        
        if not data:
            return error_response("请求数据不能为空")
        
        session_id = data.get('session_id', '').strip()
        if not session_id:
            return error_response("会话ID不能为空")
        
        new_charging_mode = data.get('charging_mode')
        new_requested_amount = data.get('requested_amount')
        
        # 验证修改参数
        errors = {}
        
        if new_charging_mode is not None:
            new_charging_mode = new_charging_mode.strip()
            if new_charging_mode not in ['fast', 'trickle']:
                errors['charging_mode'] = "充电模式必须是 'fast' 或 'trickle'"
        
        if new_requested_amount is not None:
            try:
                new_requested_amount = float(new_requested_amount)
                if new_requested_amount <= 0:
                    errors['requested_amount'] = "充电量必须大于0"
                elif new_requested_amount > 200:
                    errors['requested_amount'] = "充电量不能超过200kWh"
            except (ValueError, TypeError):
                errors['requested_amount'] = "充电量必须是有效数字"
        
        if errors:
            return validation_error_response(errors)
        
        # 获取充电服务实例
        charging_service = current_app.extensions.get('charging_service')
        if not charging_service:
            return error_response("充电服务不可用", code=503)
        
        # 修改充电请求
        result = charging_service.modify_charging_request(
            session_id, 
            user_id, 
            new_charging_mode=new_charging_mode,
            new_requested_amount=new_requested_amount
        )
        
        if result.get('success'):
            return success_response(
                data=result.get('data'),
                message=result.get('message')
            )
        else:
            return error_response(
                message=result.get('message', '修改请求失败'),
                code=result.get('code', 400)
            )
    
    except Exception as e:
        print(f"修改充电请求错误: {e}")
        return error_response("系统错误，请稍后重试", code=500)

@charging_bp.route('/request/cancel', methods=['POST'])
@login_required
def cancel_charging_request():
    """取消充电请求"""
    try:
        user_id = session.get('user_id')
        data = request.get_json()
        
        if not data:
            return error_response("请求数据不能为空")
        
        session_id = data.get('session_id', '').strip()
        if not session_id:
            return error_response("会话ID不能为空")
        
        # 获取充电服务实例
        charging_service = current_app.extensions.get('charging_service')
        if not charging_service:
            return error_response("充电服务不可用", code=503)
        
        # 取消充电请求
        result = charging_service.cancel_charging_request(session_id, user_id)
        
        if result.get('success'):
            return success_response(
                data=result.get('data'),
                message=result.get('message')
            )
        else:
            return error_response(
                message=result.get('message', '取消请求失败'),
                code=result.get('code', 400)
            )
    
    except Exception as e:
        print(f"取消充电请求错误: {e}")
        return error_response("系统错误，请稍后重试", code=500)

@charging_bp.route('/status', methods=['GET'])
@login_required
def get_charging_status():
    """查询用户充电状态"""
    try:
        user_id = session.get('user_id')
        charging_mode_filter = request.args.get('charging_mode')
        
        # 获取充电服务实例
        charging_service = current_app.extensions.get('charging_service')
        if not charging_service:
            return error_response("充电服务不可用", code=503)
        
        # 获取队列信息
        result = charging_service.get_queue_info_for_user(user_id, charging_mode_filter)
        
        return success_response(
            data=result,
            message="获取充电状态成功"
        )
    
    except Exception as e:
        print(f"获取充电状态错误: {e}")
        return error_response("系统错误，请稍后重试", code=500)

@charging_bp.route('/system-status', methods=['GET'])
def get_system_status():
    """获取系统充电状态（公开接口）"""
    try:
        # 获取充电服务实例
        charging_service = current_app.extensions.get('charging_service')
        if not charging_service:
            return error_response("充电服务不可用", code=503)
        
        # 获取系统状态
        result = charging_service.get_system_status_for_ui()
        
        return success_response(
            data=result,
            message="获取系统状态成功"
        )
    
    except Exception as e:
        print(f"获取系统状态错误: {e}")
        return error_response("系统错误，请稍后重试", code=500)

@charging_bp.route('/pile-status/<pile_id>', methods=['GET'])
def get_pile_status(pile_id):
    """获取单个充电桩状态"""
    try:
        # 获取充电服务实例
        charging_service = current_app.extensions.get('charging_service')
        if not charging_service:
            return error_response("充电服务不可用", code=503)
        
        # 获取系统状态
        system_status = charging_service.get_system_status_for_ui()
        pile_status = system_status.get('charging_piles', {}).get(pile_id)
        
        if not pile_status:
            return error_response("未找到该充电桩", code=404)
        
        return success_response(
            data=pile_status,
            message="获取充电桩状态成功"
        )
    
    except Exception as e:
        print(f"获取充电桩状态错误: {e}")
        return error_response("系统错误，请稍后重试", code=500)

@charging_bp.route('/sessions', methods=['GET'])
@login_required
def get_user_charging_sessions():
    """获取用户充电会话列表"""
    try:
        user_id = session.get('user_id')
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        status_filter = request.args.get('status')
        
        # 限制每页数量
        per_page = min(per_page, 50)
        
        from models.charging import ChargingSession, ChargingStatus
        
        # 构建查询
        query = ChargingSession.query.filter_by(user_id=user_id)
        
        # 状态过滤
        if status_filter:
            try:
                status_enum = ChargingStatus(status_filter)
                query = query.filter_by(status=status_enum)
            except ValueError:
                return error_response("无效的状态值")
        
        # 按创建时间倒序排列
        query = query.order_by(ChargingSession.created_at.desc())
        
        # 分页查询
        pagination = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        
        sessions = pagination.items
        
        # 计算汇总信息
        total_sessions = pagination.total
        completed_sessions = ChargingSession.query.filter_by(
            user_id=user_id, 
            status=ChargingStatus.COMPLETED
        ).count()
        
        return success_response(data={
            'sessions': [session.to_dict() for session in sessions],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': pagination.total,
                'pages': pagination.pages,
                'has_prev': pagination.has_prev,
                'has_next': pagination.has_next
            },
            'summary': {
                'total_sessions': total_sessions,
                'completed_sessions': completed_sessions
            }
        }, message="获取充电会话列表成功")
    
    except Exception as e:
        print(f"获取用户充电会话错误: {e}")
        return error_response("系统错误，请稍后重试", code=500)

@charging_bp.route('/sessions/<session_id>', methods=['GET'])
@login_required
def get_charging_session_detail(session_id):
    """获取充电会话详情"""
    try:
        user_id = session.get('user_id')
        
        from models.charging import ChargingSession
        
        # 查询会话详情
        charging_session = ChargingSession.query.filter_by(
            session_id=session_id,
            user_id=user_id
        ).first()
        
        if not charging_session:
            return error_response("充电会话不存在或无权访问", code=404)
        
        return success_response(
            data=charging_session.to_detail_dict(),
            message="获取充电会话详情成功"
        )
    
    except Exception as e:
        print(f"获取充电会话详情错误: {e}")
        return error_response("系统错误，请稍后重试", code=500)

@charging_bp.route('/queue-position', methods=['GET'])
@login_required
def get_queue_position():
    """获取用户在队列中的位置信息"""
    try:
        user_id = session.get('user_id')
        
        # 获取充电服务实例
        charging_service = current_app.extensions.get('charging_service')
        if not charging_service:
            return error_response("充电服务不可用", code=503)
        
        # 获取详细的队列位置信息
        result = charging_service.get_queue_info_for_user(user_id)
        
        return success_response(
            data=result,
            message="获取队列位置成功"
        )
    
    except Exception as e:
        print(f"获取队列位置错误: {e}")
        return error_response("系统错误，请稍后重试", code=500)

@charging_bp.route('/estimate-time', methods=['GET'])
@login_required
def estimate_charging_time():
    """估算充电时间"""
    try:
        user_id = session.get('user_id')
        charging_mode = request.args.get('charging_mode', 'fast')
        requested_amount = request.args.get('requested_amount', type=float)
        
        if not requested_amount or requested_amount <= 0:
            return error_response("请提供有效的充电量")
        
        if charging_mode not in ['fast', 'trickle']:
            return error_response("无效的充电模式")
        
        # 获取充电服务实例
        charging_service = current_app.extensions.get('charging_service')
        if not charging_service:
            return error_response("充电服务不可用", code=503)
        
        # 计算估算时间
        power_rating = 30.0 if charging_mode == 'fast' else 7.0  # kW
        charging_time_hours = requested_amount / power_rating
        
        # 获取当前队列状态来估算等待时间
        system_status = charging_service.get_system_status_for_ui()
        queue_key = 'fast' if charging_mode == 'fast' else 'trickle'
        
        station_waiting = system_status.get('station_waiting_area', {}).get(queue_key, 0)
        engine_waiting = system_status.get('engine_dispatch_queues', {}).get(f'{queue_key}_count', 0)
        
        total_waiting = station_waiting + engine_waiting
        estimated_wait_minutes = total_waiting * 5  # 粗略估算：每个请求平均5分钟处理时间
        
        result = {
            'charging_mode': charging_mode,
            'requested_amount': requested_amount,
            'power_rating': power_rating,
            'charging_time_hours': round(charging_time_hours, 2),
            'charging_time_minutes': round(charging_time_hours * 60, 1),
            'estimated_wait_minutes': estimated_wait_minutes,
            'total_time_minutes': round(charging_time_hours * 60 + estimated_wait_minutes, 1),
            'queue_position': {
                'station_waiting': station_waiting,
                'engine_waiting': engine_waiting,
                'total_waiting': total_waiting
            }
        }
        
        return success_response(
            data=result,
            message="充电时间估算成功"
        )
    
    except Exception as e:
        print(f"估算充电时间错误: {e}")
        return error_response("系统错误，请稍后重试", code=500)

@charging_bp.route('/stop', methods=['POST'])
@login_required
def stop_charging():
    """用户主动停止充电"""
    try:
        user_id = session.get('user_id')
        data = request.get_json()
        
        if not data:
            return error_response("请求数据不能为空")
        
        session_id = data.get('session_id', '').strip()
        if not session_id:
            return error_response("会话ID不能为空")
        
        # 验证会话归属
        from models.charging import ChargingSession, ChargingStatus
        
        charging_session = ChargingSession.query.filter_by(
            session_id=session_id,
            user_id=user_id
        ).first()
        
        if not charging_session:
            return error_response("充电会话不存在或无权访问", code=404)
        
        if charging_session.status not in [ChargingStatus.CHARGING, ChargingStatus.COMPLETING]:
            return error_response("当前会话状态不允许停止充电", code=400)
        
        # 获取充电服务实例
        charging_service = current_app.extensions.get('charging_service')
        if not charging_service:
            return error_response("充电服务不可用", code=503)
        
        # 停止充电
        if charging_session.pile_id:
            try:
                import scheduler_core
                scheduler_core.end_charging(charging_session.pile_id)
                
                return success_response(
                    data={
                        'session_id': session_id,
                        'pile_id': charging_session.pile_id
                    },
                    message="停止充电指令已发送"
                )
            except Exception as e:
                print(f"停止充电错误: {e}")
                return error_response("停止充电失败", code=500)
        else:
            return error_response("充电桩信息不完整", code=400)
    
    except Exception as e:
        print(f"停止充电错误: {e}")
        return error_response("系统错误，请稍后重试", code=500)

@charging_bp.route('/history', methods=['GET'])
@login_required
def get_charging_history():
    """获取用户充电历史记录"""
    try:
        user_id = session.get('user_id')
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        charging_mode = request.args.get('charging_mode')
        
        # 限制每页数量
        per_page = min(per_page, 50)
        
        from models.charging import ChargingSession, ChargingStatus, ChargingMode
        from datetime import datetime, timedelta
        
        # 构建查询
        query = ChargingSession.query.filter_by(user_id=user_id)
        
        # 只查询已完成的会话
        query = query.filter(ChargingSession.status.in_([
            ChargingStatus.COMPLETED, 
            ChargingStatus.CANCELLED, 
            ChargingStatus.FAULT_COMPLETED
        ]))
        
        # 充电模式过滤
        if charging_mode and charging_mode in ['fast', 'trickle']:
            charging_mode_enum = ChargingMode.FAST if charging_mode == 'fast' else ChargingMode.TRICKLE
            query = query.filter_by(charging_mode=charging_mode_enum)
        
        # 日期过滤
        if start_date:
            try:
                start_dt = datetime.fromisoformat(start_date)
                query = query.filter(ChargingSession.created_at >= start_dt)
            except ValueError:
                return error_response("开始日期格式错误")
        
        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date)
                end_dt = end_dt + timedelta(days=1)  # 包含当天
                query = query.filter(ChargingSession.created_at < end_dt)
            except ValueError:
                return error_response("结束日期格式错误")
        
        # 按结束时间倒序排列
        query = query.order_by(ChargingSession.end_time.desc())
        
        # 分页查询
        pagination = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        
        sessions = pagination.items
        
        # 计算统计信息
        total_amount = sum(float(session.actual_amount or 0) for session in sessions)
        total_cost = sum(float(session.total_fee or 0) for session in sessions)
        total_duration = sum(float(session.charging_duration or 0) for session in sessions)
        
        return success_response(data={
            'history': [session.to_detail_dict() for session in sessions],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': pagination.total,
                'pages': pagination.pages,
                'has_prev': pagination.has_prev,
                'has_next': pagination.has_next
            },
            'statistics': {
                'total_sessions': pagination.total,
                'total_amount_kwh': round(total_amount, 2),
                'total_cost': round(total_cost, 2),
                'total_duration_hours': round(total_duration, 2),
                'average_cost_per_kwh': round(total_cost / total_amount, 2) if total_amount > 0 else 0
            }
        }, message="获取充电历史成功")
    
    except Exception as e:
        print(f"获取充电历史错误: {e}")
        return error_response("系统错误，请稍后重试", code=500)