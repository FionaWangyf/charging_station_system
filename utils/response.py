from flask import jsonify

def success_response(data=None, message="操作成功", code=200):
    """成功响应"""
    response = {
        'code': code,
        'message': message,
        'success': True
    }
    if data is not None:
        response['data'] = data
    return jsonify(response), code

def error_response(message="操作失败", code=400, error_type="OPERATION_FAILED"):
    """错误响应"""
    return jsonify({
        'code': code,
        'message': message,
        'success': False,
        'error_type': error_type
    }), code

def validation_error_response(errors, message="数据验证失败"):
    """数据验证错误响应"""
    return jsonify({
        'code': 400,
        'message': message,
        'success': False,
        'error_type': 'VALIDATION_ERROR',
        'errors': errors
    }), 400