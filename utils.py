from datetime import datetime

def get_current_timestamp():
    """获取当前时间戳"""
    return datetime.now().isoformat()

def format_response(code, message, data=None):
    """格式化API响应"""
    response = {
        'code': code,
        'message': message,
        'timestamp': get_current_timestamp()
    }
    if data is not None:
        response['data'] = data
    return response