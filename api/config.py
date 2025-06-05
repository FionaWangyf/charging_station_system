from flask import Blueprint, request, jsonify

from auth import token_required, admin_required
from config import ConfigManager
from utils import format_response

config_bp = Blueprint('config', __name__)

@config_bp.route('/', methods=['GET'])
@token_required
@admin_required
def get_system_config():
    """获取系统配置"""
    try:
        config_key = request.args.get('key')
        config = ConfigManager.get_config(config_key)
        
        return jsonify(format_response(200, '获取系统配置成功', config))
    except Exception as e:
        return jsonify(format_response(5001, f'获取系统配置失败: {str(e)}')), 500

@config_bp.route('/', methods=['PUT'])
@token_required
@admin_required
def update_system_config():
    """更新系统配置"""
    try:
        data = request.get_json()
        config_key = data.get('key')
        config_value = data.get('value')
        
        if not config_key or config_value is None:
            return jsonify(format_response(5002, '缺少配置键或值')), 400
        
        ConfigManager.update_config(config_key, config_value)
        
        result_data = {'key': config_key, 'value': config_value}
        return jsonify(format_response(200, '系统配置更新成功', result_data))
    except Exception as e:
        return jsonify(format_response(5003, f'系统配置更新失败: {str(e)}')), 500

@config_bp.route('/billing', methods=['PUT'])
@token_required
@admin_required
def update_billing_config():
    """更新计费配置"""
    try:
        data = request.get_json()
        
        # 验证配置参数
        required_fields = ['peak_rate', 'normal_rate', 'valley_rate', 'service_fee_rate']
        for field in required_fields:
            if field not in data:
                return jsonify(format_response(4009, f'缺少必要参数: {field}')), 400
        
        # 验证费率值
        for field in required_fields:
            if not isinstance(data[field], (int, float)) or data[field] < 0:
                return jsonify(format_response(4010, f'参数 {field} 必须是非负数')), 400
        
        ConfigManager.update_config('billing', data)
        
        return jsonify(format_response(200, '计费配置更新成功', data))
    except Exception as e:
        return jsonify(format_response(4011, f'计费配置更新失败: {str(e)}')), 500