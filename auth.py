import jwt
from flask import request, jsonify, g
from functools import wraps

SECRET_KEY = 'asdfg'

def token_required(f):
    """JWT认证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'code': 5001, 'message': '缺少认证令牌'}), 401
        
        try:
            if token.startswith('Bearer '):
                token = token[7:]
            data = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
            g.current_user_id = data['user_id']
            g.current_user_role = data.get('role', 'user')
        except jwt.ExpiredSignatureError:
            return jsonify({'code': 5002, 'message': '令牌已过期'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'code': 5003, 'message': '无效令牌'}), 401
        
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """管理员权限装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if g.current_user_role != 'admin':
            return jsonify({'code': 5004, 'message': '需要管理员权限'}), 403
        return f(*args, **kwargs)
    return decorated_function