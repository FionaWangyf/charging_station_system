from flask import Blueprint, request, session
from datetime import datetime
from decimal import Decimal, InvalidOperation
from services.billing_service import BillingService
from utils.response import success_response, error_response, validation_error_response
from utils.validators import validate_required_fields
from functools import wraps

# 创建蓝图
billing_bp = Blueprint('billing', __name__)

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

@billing_bp.route('/test', methods=['GET'])
def test():
    """测试接口"""
    return success_response(data={'message': '计费API正常运行'})

@billing_bp.route('/rates', methods=['GET'])
def get_billing_rates():
    """获取当前电价配置"""
    try:
        rates = BillingService.get_billing_rates()
        
        # 添加时段说明
        data = {
            'rates': rates,
            'time_periods': {
                'peak': {
                    'name': '峰时',
                    'hours': '10:00-15:00, 18:00-21:00',
                    'rate': rates['peak_rate']
                },
                'normal': {
                    'name': '平时', 
                    'hours': '07:00-10:00, 15:00-18:00, 21:00-23:00',
                    'rate': rates['normal_rate']
                },
                'valley': {
                    'name': '谷时',
                    'hours': '23:00-07:00',
                    'rate': rates['valley_rate']
                }
            },
            'service_fee_rate': rates['service_fee_rate']
        }
        
        return success_response(data=data, message="获取电价配置成功")
    except Exception as e:
        return error_response(f"获取电价配置失败: {str(e)}", code=500)

@billing_bp.route('/rates', methods=['PUT'])
@admin_required
def update_billing_rates():
    """更新电价配置（管理员功能）"""
    try:
        data = request.get_json()
        if not data:
            return error_response("请求数据不能为空")
        
        # 验证必要字段
        required_fields = ['peak_rate', 'normal_rate', 'valley_rate', 'service_fee_rate']
        errors = validate_required_fields(data, required_fields)
        
        # 验证费率值
        for field in required_fields:
            if field in data:
                try:
                    rate = float(data[field])
                    if rate < 0:
                        errors[field] = "费率不能为负数"
                except (ValueError, TypeError):
                    errors[field] = "费率必须是有效数字"
        
        if errors:
            return validation_error_response(errors)
        
        # 更新配置
        rates = {
            'peak': float(data['peak_rate']),
            'normal': float(data['normal_rate']),
            'valley': float(data['valley_rate']),
            'service_fee': float(data['service_fee_rate'])
        }
        
        success = BillingService.update_billing_rates(rates)
        if success:
            return success_response(data=rates, message="电价配置更新成功")
        else:
            return error_response("电价配置更新失败", code=500)
        
    except Exception as e:
        return error_response(f"电价配置更新失败: {str(e)}", code=500)

@billing_bp.route('/calculate', methods=['POST'])
@login_required
def calculate_billing():
    """计算充电费用"""
    try:
        data = request.get_json()
        if not data:
            return error_response("请求数据不能为空")
        
        # 验证必要字段
        required_fields = ['start_time', 'end_time', 'power_consumed']
        errors = validate_required_fields(data, required_fields)
        
        if errors:
            return validation_error_response(errors)
        
        # 解析时间
        try:
            start_time = datetime.fromisoformat(data['start_time'].replace('Z', '+00:00'))
            end_time = datetime.fromisoformat(data['end_time'].replace('Z', '+00:00'))
        except ValueError:
            return error_response("时间格式错误，请使用ISO格式")
        
        # 验证时间逻辑
        if start_time >= end_time:
            return error_response("结束时间必须晚于开始时间")
        
        # 验证功率消耗
        try:
            power_consumed = Decimal(str(data['power_consumed']))
            if power_consumed <= 0:
                return error_response("消耗电量必须大于0")
        except (InvalidOperation, ValueError):
            return error_response("消耗电量格式错误")
        
        # 计算费用
        billing_result = BillingService.calculate_billing(start_time, end_time, power_consumed)
        
        return success_response(data=billing_result, message="费用计算成功")
        
    except Exception as e:
        return error_response(f"费用计算失败: {str(e)}", code=500)

@billing_bp.route('/records', methods=['POST'])
@login_required
def create_charging_record():
    """创建充电记录（模拟充电完成）"""
    try:
        user_id = session.get('user_id')
        data = request.get_json()
        if not data:
            return error_response("请求数据不能为空")
        
        # 验证必要字段
        required_fields = ['pile_id', 'start_time', 'end_time', 'power_consumed']
        errors = validate_required_fields(data, required_fields)
        
        if errors:
            return validation_error_response(errors)
        
        # 解析数据
        try:
            pile_id = data['pile_id'].strip()
            start_time = datetime.fromisoformat(data['start_time'].replace('Z', '+00:00'))
            end_time = datetime.fromisoformat(data['end_time'].replace('Z', '+00:00'))
            power_consumed = Decimal(str(data['power_consumed']))
        except (ValueError, InvalidOperation):
            return error_response("数据格式错误")
        
        # 验证数据
        if not pile_id:
            return error_response("充电桩ID不能为空")
        
        if start_time >= end_time:
            return error_response("结束时间必须晚于开始时间")
        
        if power_consumed <= 0:
            return error_response("消耗电量必须大于0")
        
        # 创建充电记录
        record = BillingService.create_charging_record(
            user_id=user_id,
            pile_id=pile_id,
            start_time=start_time,
            end_time=end_time,
            power_consumed=power_consumed
        )
        
        if record:
            return success_response(
                data=record.to_dict(),
                message="充电记录创建成功",
                code=201
            )
        else:
            return error_response("充电记录创建失败", code=500)
        
    except Exception as e:
        return error_response(f"充电记录创建失败: {str(e)}", code=500)

@billing_bp.route('/records/<int:record_id>', methods=['GET'])
@login_required
def get_charging_record_detail(record_id):
    """获取充电记录详情"""
    try:
        user_id = session.get('user_id')
        
        # 获取记录详情
        record_detail = BillingService.get_charging_record_detail(record_id, user_id)
        
        if record_detail:
            return success_response(data=record_detail, message="获取充电记录详情成功")
        else:
            return error_response("充电记录不存在", code=404)
        
    except Exception as e:
        return error_response(f"获取充电记录详情失败: {str(e)}", code=500)