from flask import Blueprint, request, session
from models.user import db, User
from services.billing_service import BillingService
from utils.response import success_response, error_response, validation_error_response
from utils.validators import validate_car_id, validate_username, validate_password, validate_car_capacity, validate_required_fields
from functools import wraps

# 创建蓝图
user_bp = Blueprint('user', __name__)

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

@user_bp.route('/test', methods=['GET'])
def test():
    """测试接口"""
    return success_response(data={'message': '用户API正常运行'})

# ==================== 认证相关 ====================

@user_bp.route('/register', methods=['POST'])
def register():
    """用户注册接口"""
    try:
        # 获取请求数据
        data = request.get_json()
        if not data:
            return error_response("请求数据不能为空")
        
        car_id = data.get('car_id', '').strip()
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        car_capacity = data.get('car_capacity')
        
        # 数据验证
        errors = {}
        
        # 验证车牌号
        is_valid, msg = validate_car_id(car_id)
        if not is_valid:
            errors['car_id'] = msg
        
        # 验证用户名
        is_valid, msg = validate_username(username)
        if not is_valid:
            errors['username'] = msg
        
        # 验证密码
        is_valid, msg = validate_password(password)
        if not is_valid:
            errors['password'] = msg
        
        # 验证电池容量
        is_valid, msg = validate_car_capacity(car_capacity)
        if not is_valid:
            errors['car_capacity'] = msg
        
        if errors:
            return validation_error_response(errors)
        
        # 检查车牌号是否已存在
        existing_user = User.query.filter_by(car_id=car_id).first()
        if existing_user:
            return error_response("该车牌号已注册", code=409)
        
        # 检查用户名是否已存在
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            return error_response("用户名已存在", code=409)
        
        # 创建新用户
        new_user = User(
            car_id=car_id,
            username=username,
            car_capacity=float(car_capacity)
        )
        new_user.set_password(password)
        
        # 保存到数据库
        db.session.add(new_user)
        db.session.commit()
        
        return success_response(
            data={
                "user_id": new_user.id,
                "message": "注册成功"
            },
            message="用户注册成功",
            code=201
        )
        
    except Exception as e:
        db.session.rollback()
        return error_response(f"注册失败: {str(e)}", code=500)

@user_bp.route('/login', methods=['POST'])
def login():
    """用户登录接口"""
    try:
        # 获取请求数据
        data = request.get_json()
        if not data:
            return error_response("请求数据不能为空")
        
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        
        if not username or not password:
            return error_response("用户名和密码不能为空")
        
        # 查找用户
        user = User.query.filter_by(username=username).first()
        if not user:
            return error_response("用户名或密码错误", code=401)
        
        # 验证密码
        if not user.check_password(password):
            return error_response("用户名或密码错误", code=401)
        
        # 检查用户状态
        if user.status != 'active':
            return error_response("账户已被禁用", code=403)
        
        # 将用户信息存储在session中
        session['user_id'] = user.id
        session['username'] = user.username
        session['user_type'] = user.user_type
        
        return success_response(
            data={
                "user_info": user.to_dict(),
                "session_id": "登录成功，session已创建"
            },
            message="登录成功"
        )
        
    except Exception as e:
        return error_response(f"登录失败: {str(e)}", code=500)

@user_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    """用户登出接口"""
    try:
        session.clear()
        return success_response(message="登出成功")
    except Exception as e:
        return error_response(f"登出失败: {str(e)}", code=500)

# ==================== 用户信息管理 ====================

@user_bp.route('/profile', methods=['GET'])
@login_required
def get_profile():
    """获取用户信息"""
    try:
        # 从session获取用户ID
        user_id = session.get('user_id')
        
        # 查找用户
        user = User.query.get(user_id)
        if not user:
            return error_response("用户不存在", code=404)
        
        return success_response(
            data=user.to_dict(),
            message="获取用户信息成功"
        )
        
    except Exception as e:
        return error_response(f"获取用户信息失败: {str(e)}", code=500)

@user_bp.route('/profile', methods=['PUT'])
@login_required
def update_profile():
    """更新用户个人信息"""
    try:
        user_id = session.get('user_id')
        user = User.query.get(user_id)
        
        if not user:
            return error_response("用户不存在", code=404)
        
        # 获取请求数据
        data = request.get_json()
        if not data:
            return error_response("请求数据不能为空")
        
        # 可更新的字段
        car_capacity = data.get('car_capacity')
        
        # 验证数据
        errors = {}
        updated_fields = []
        
        # 更新电池容量
        if car_capacity is not None:
            is_valid, msg = validate_car_capacity(car_capacity)
            if not is_valid:
                errors['car_capacity'] = msg
            else:
                user.car_capacity = float(car_capacity)
                updated_fields.append('电池容量')
        
        if errors:
            return validation_error_response(errors)
        
        if not updated_fields:
            return error_response("没有需要更新的字段")
        
        # 保存更改
        db.session.commit()
        
        return success_response(
            data={
                "user_info": user.to_dict(),
                "updated_fields": updated_fields
            },
            message=f"成功更新: {', '.join(updated_fields)}"
        )
        
    except Exception as e:
        db.session.rollback()
        return error_response(f"更新个人信息失败: {str(e)}", code=500)

@user_bp.route('/change-password', methods=['PUT'])
@login_required
def change_password():
    """修改密码"""
    try:
        user_id = session.get('user_id')
        user = User.query.get(user_id)
        
        if not user:
            return error_response("用户不存在", code=404)
        
        # 获取请求数据
        data = request.get_json()
        if not data:
            return error_response("请求数据不能为空")
        
        old_password = data.get('old_password', '').strip()
        new_password = data.get('new_password', '').strip()
        confirm_password = data.get('confirm_password', '').strip()
        
        # 验证数据
        errors = {}
        
        if not old_password:
            errors['old_password'] = "原密码不能为空"
        elif not user.check_password(old_password):
            errors['old_password'] = "原密码错误"
        
        # 验证新密码
        is_valid, msg = validate_password(new_password)
        if not is_valid:
            errors['new_password'] = msg
        elif new_password == old_password:
            errors['new_password'] = "新密码不能与原密码相同"
        
        if new_password != confirm_password:
            errors['confirm_password'] = "确认密码与新密码不一致"
        
        if errors:
            return validation_error_response(errors)
        
        # 更新密码
        user.set_password(new_password)
        db.session.commit()
        
        return success_response(message="密码修改成功")
        
    except Exception as e:
        db.session.rollback()
        return error_response(f"修改密码失败: {str(e)}", code=500)

# ==================== 充电详单功能 ====================

@user_bp.route('/charging-records', methods=['GET'])
@login_required
def get_charging_records():
    """获取用户充电详单列表"""
    try:
        user_id = session.get('user_id')
        
        # 获取查询参数
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        start_date = request.args.get('start_date')  # YYYY-MM-DD
        end_date = request.args.get('end_date')      # YYYY-MM-DD
        
        # 限制每页数量
        per_page = min(per_page, 50)
        
        # 获取充电记录
        result = BillingService.get_user_charging_records(
            user_id=user_id,
            page=page,
            per_page=per_page,
            start_date=start_date,
            end_date=end_date
        )
        
        return success_response(data=result, message="获取充电记录成功")
        
    except Exception as e:
        return error_response(f"获取充电记录失败: {str(e)}", code=500)

@user_bp.route('/charging-records/<int:record_id>', methods=['GET'])
@login_required
def get_charging_record_detail(record_id):
    """获取充电详单详情"""
    try:
        user_id = session.get('user_id')
        
        # 获取记录详情
        record_detail = BillingService.get_charging_record_detail(record_id, user_id)
        
        if record_detail:
            return success_response(data=record_detail, message="获取充电详单详情成功")
        else:
            return error_response("充电记录不存在或无权访问", code=404)
        
    except Exception as e:
        return error_response(f"获取充电详单详情失败: {str(e)}", code=500)

@user_bp.route('/charging-summary', methods=['GET'])
@login_required
def get_charging_summary():
    """获取用户充电汇总信息"""
    try:
        user_id = session.get('user_id')
        
        # 获取不同时间范围的汇总
        # 本月汇总
        from datetime import datetime, timedelta
        now = datetime.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        month_result = BillingService.get_user_charging_records(
            user_id=user_id,
            page=1,
            per_page=1000,  # 获取所有记录用于统计
            start_date=month_start.isoformat()
        )
        
        # 近30天汇总
        thirty_days_ago = now - timedelta(days=30)
        thirty_days_result = BillingService.get_user_charging_records(
            user_id=user_id,
            page=1,
            per_page=1000,
            start_date=thirty_days_ago.isoformat()
        )
        
        summary_data = {
            'current_month': {
                'period': f"{month_start.strftime('%Y-%m')}-01 至今",
                'total_records': month_result['summary']['total_records'],
                'total_power_consumed': month_result['summary']['total_power_consumed'],
                'total_cost': month_result['summary']['total_cost']
            },
            'last_30_days': {
                'period': f"近30天",
                'total_records': thirty_days_result['summary']['total_records'],
                'total_power_consumed': thirty_days_result['summary']['total_power_consumed'],
                'total_cost': thirty_days_result['summary']['total_cost']
            }
        }
        
        return success_response(data=summary_data, message="获取充电汇总成功")
        
    except Exception as e:
        return error_response(f"获取充电汇总失败: {str(e)}", code=500)

# ==================== 调试功能 ====================

@user_bp.route('/session-info', methods=['GET'])
def get_session_info():
    """获取session信息（调试用）"""
    return success_response(data={
        'session_data': dict(session),
        'is_logged_in': 'user_id' in session
    })

# ==================== 管理员功能 ====================

@user_bp.route('/admin/users', methods=['GET'])
@admin_required
def admin_get_all_users():
    """管理员获取所有用户列表"""
    try:
        # 获取查询参数
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        status = request.args.get('status')  # active, inactive, banned
        user_type = request.args.get('user_type')  # user, admin
        search = request.args.get('search', '').strip()  # 搜索用户名或车牌号
        
        # 限制每页数量
        per_page = min(per_page, 100)
        
        # 构建查询
        query = User.query
        
        # 状态过滤
        if status:
            query = query.filter_by(status=status)
        
        # 用户类型过滤
        if user_type:
            query = query.filter_by(user_type=user_type)
        
        # 搜索过滤
        if search:
            query = query.filter(
                db.or_(
                    User.username.like(f'%{search}%'),
                    User.car_id.like(f'%{search}%')
                )
            )
        
        # 按创建时间倒序排列
        query = query.order_by(User.created_at.desc())
        
        # 分页查询
        pagination = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        
        users = pagination.items
        
        # 统计信息
        total_users = User.query.count()
        active_users = User.query.filter_by(status='active').count()
        admin_users = User.query.filter_by(user_type='admin').count()
        
        return success_response(data={
            'users': [user.to_dict() for user in users],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': pagination.total,
                'pages': pagination.pages,
                'has_prev': pagination.has_prev,
                'has_next': pagination.has_next
            },
            'statistics': {
                'total_users': total_users,
                'active_users': active_users,
                'admin_users': admin_users
            }
        }, message="获取用户列表成功")
        
    except Exception as e:
        return error_response(f"获取用户列表失败: {str(e)}", code=500)

@user_bp.route('/admin/users/<int:user_id>', methods=['GET'])
@admin_required
def admin_get_user_detail(user_id):
    """管理员获取特定用户详情"""
    try:
        user = User.query.get(user_id)
        if not user:
            return error_response("用户不存在", code=404)
        
        return success_response(
            data=user.to_dict(),
            message="获取用户详情成功"
        )
        
    except Exception as e:
        return error_response(f"获取用户详情失败: {str(e)}", code=500)

@user_bp.route('/admin/users/<int:user_id>/status', methods=['PUT'])
@admin_required
def admin_update_user_status(user_id):
    """管理员更新用户状态"""
    try:
        user = User.query.get(user_id)
        if not user:
            return error_response("用户不存在", code=404)
        
        # 获取请求数据
        data = request.get_json()
        if not data:
            return error_response("请求数据不能为空")
        
        new_status = data.get('status', '').strip()
        reason = data.get('reason', '').strip()
        
        # 验证状态值
        valid_statuses = ['active', 'inactive', 'banned']
        if new_status not in valid_statuses:
            return error_response(f"无效的状态值，必须是: {', '.join(valid_statuses)}")
        
        # 不能修改自己的状态
        current_admin_id = session.get('user_id')
        if user_id == current_admin_id:
            return error_response("不能修改自己的账户状态")
        
        old_status = user.status
        user.status = new_status
        db.session.commit()
        
        return success_response(
            data={
                "user_id": user_id,
                "old_status": old_status,
                "new_status": new_status,
                "reason": reason
            },
            message=f"用户状态已从 {old_status} 更新为 {new_status}"
        )
        
    except Exception as e:
        db.session.rollback()
        return error_response(f"更新用户状态失败: {str(e)}", code=500)