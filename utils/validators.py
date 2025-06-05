import re

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