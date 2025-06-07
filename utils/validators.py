import re
from typing import Dict, List, Any

def validate_car_id(car_id):
    """验证车牌号格式"""
    if not car_id:
        return False, "车牌号不能为空"
    
    # 简单的车牌号验证（可以根据需要调整）
    if len(car_id) < 6 or len(car_id) > 10:
        return False, "车牌号长度应在6-10位之间"
    
    return True, ""

def validate_username(username):
    """验证用户名格式"""
    if not username:
        return False, "用户名不能为空"
    
    if len(username) < 3 or len(username) > 20:
        return False, "用户名长度应在3-20位之间"
    
    # 只允许字母、数字、下划线
    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        return False, "用户名只能包含字母、数字和下划线"
    
    return True, ""

def validate_password(password):
    """验证密码强度"""
    if not password:
        return False, "密码不能为空"
    
    if len(password) < 6:
        return False, "密码长度不能少于6位"
    
    if len(password) > 20:
        return False, "密码长度不能超过20位"
    
    return True, ""

def validate_car_capacity(capacity):
    """验证车辆电池容量"""
    try:
        capacity = float(capacity)
        if capacity <= 0:
            return False, "电池容量必须大于0"
        if capacity > 200:  # 假设最大容量200度
            return False, "电池容量不能超过200度"
        return True, ""
    except (ValueError, TypeError):
        return False, "电池容量必须是有效数字"

def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> Dict[str, str]:
    """验证必需字段"""
    errors = {}
    for field in required_fields:
        if field not in data or data[field] is None:
            errors[field] = f"{field}字段不能为空"
        elif isinstance(data[field], str) and not data[field].strip():
            errors[field] = f"{field}字段不能为空"
    return errors

def validate_pagination_params(page: int, per_page: int) -> Dict[str, str]:
    """验证分页参数"""
    errors = {}
    
    if page < 1:
        errors['page'] = "页码必须大于0"
    
    if per_page < 1:
        errors['per_page'] = "每页数量必须大于0"
    elif per_page > 100:
        errors['per_page'] = "每页数量不能超过100"
    
    return errors

def validate_date_range(start_date: str, end_date: str) -> Dict[str, str]:
    """验证日期范围"""
    errors = {}
    
    try:
        from datetime import datetime
        start_dt = datetime.fromisoformat(start_date)
        end_dt = datetime.fromisoformat(end_date)
        
        if start_dt >= end_dt:
            errors['date_range'] = "开始日期必须早于结束日期"
            
    except ValueError:
        errors['date_format'] = "日期格式错误，请使用YYYY-MM-DD格式"
    
    return errors

def validate_billing_data(start_time: str, end_time: str, power_consumed: float) -> Dict[str, str]:
    """验证计费数据"""
    errors = {}
    
    # 验证时间格式
    try:
        from datetime import datetime
        start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
        
        if start_dt >= end_dt:
            errors['time_range'] = "结束时间必须晚于开始时间"
            
    except ValueError:
        errors['time_format'] = "时间格式错误，请使用ISO格式"
    
    # 验证功率消耗
    try:
        power = float(power_consumed)
        if power <= 0:
            errors['power_consumed'] = "消耗电量必须大于0"
        elif power > 1000:  # 假设最大1000度
            errors['power_consumed'] = "消耗电量超出合理范围"
    except (ValueError, TypeError):
        errors['power_consumed'] = "消耗电量必须是有效数字"
    
    return errors

def validate_pile_id(pile_id: str) -> tuple:
    """验证充电桩ID"""
    if not pile_id or not pile_id.strip():
        return False, "充电桩ID不能为空"
    
    pile_id = pile_id.strip()
    if len(pile_id) < 1 or len(pile_id) > 20:
        return False, "充电桩ID长度应在1-20位之间"
    
    # 简单的ID格式验证
    if not re.match(r'^[A-Z0-9]+', pile_id):
        return False, "充电桩ID只能包含大写字母和数字"
    
    return True, ""

def validate_email(email: str) -> tuple:
    """验证邮箱格式"""
    if not email:
        return False, "邮箱不能为空"
    
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    if not re.match(email_pattern, email):
        return False, "邮箱格式不正确"
    
    return True, ""

def validate_phone(phone: str) -> tuple:
    """验证手机号格式"""
    if not phone:
        return False, "手机号不能为空"
    
    # 简单的中国手机号验证
    phone_pattern = r'^1[3-9]\d{9}'
    if not re.match(phone_pattern, phone):
        return False, "手机号格式不正确"
    
    return True, ""