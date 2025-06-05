from flask import Blueprint, request, jsonify, g
from datetime import datetime
from decimal import Decimal
import uuid

from auth import token_required
from billing import BillingSystem
from database import DatabaseManager
from config import ConfigManager
from utils import format_response

billing_bp = Blueprint('billing', __name__)

@billing_bp.route('/calculate', methods=['POST'])
@token_required
def calculate_billing():
    """计算充电费用"""
    try:
        data = request.get_json()
        start_time = datetime.fromisoformat(data['start_time'])
        end_time = datetime.fromisoformat(data['end_time'])
        power_consumed = Decimal(str(data['power_consumed']))
        
        billing_result = BillingSystem.calculate_billing(start_time, end_time, power_consumed)
        
        return jsonify(format_response(200, '计费计算成功', billing_result))
    except Exception as e:
        return jsonify(format_response(4001, f'计费计算失败: {str(e)}')), 400

@billing_bp.route('/rates', methods=['GET'])
def get_billing_rates():
    """获取当前电价配置"""
    try:
        config = ConfigManager.get_config('billing')
        rates = {
            'peak_rate': config.get('peak_rate', 1.0),
            'normal_rate': config.get('normal_rate', 0.7),
            'valley_rate': config.get('valley_rate', 0.4),
            'service_fee_rate': config.get('service_fee_rate', 0.8),
            'peak_hours': '10:00-15:00, 18:00-21:00',
            'valley_hours': '23:00-7:00',
            'normal_hours': '7:00-10:00, 15:00-18:00, 21:00-23:00'
        }
        
        return jsonify(format_response(200, '获取电价配置成功', rates))
    except Exception as e:
        return jsonify(format_response(4002, f'获取电价配置失败: {str(e)}')), 500

@billing_bp.route('/records', methods=['GET'])
@token_required
def get_charging_records():
    """获取用户充电详单"""
    try:
        user_id = g.current_user_id
        page = int(request.args.get('page', 1))
        size = int(request.args.get('size', 10))
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        offset = (page - 1) * size
        
        # 构建查询条件
        where_conditions = ['user_id = %s']
        params = [user_id]
        
        if start_date:
            where_conditions.append('created_at >= %s')
            params.append(start_date)
        
        if end_date:
            where_conditions.append('created_at <= %s')
            params.append(end_date)
        
        where_clause = ' AND '.join(where_conditions)
        
        # 查询充电记录
        query = f"""
        SELECT id, pile_id, start_time, end_time, power_consumed, 
               electricity_fee, service_fee, total_fee, status, created_at
        FROM charging_records 
        WHERE {where_clause}
        ORDER BY created_at DESC
        LIMIT %s OFFSET %s
        """
        params.extend([size, offset])
        
        records = DatabaseManager.execute_query(query, params, fetch_all=True)
        
        # 查询总数
        count_query = f"SELECT COUNT(*) as total FROM charging_records WHERE {where_clause}"
        count_result = DatabaseManager.execute_query(count_query, params[:-2], fetch_one=True)
        total = count_result['total'] if count_result else 0
        
        data = {
            'records': records,
            'pagination': {
                'page': page,
                'size': size,
                'total': total,
                'pages': (total + size - 1) // size
            }
        }
        
        return jsonify(format_response(200, '获取充电详单成功', data))
    except Exception as e:
        return jsonify(format_response(4003, f'获取充电详单失败: {str(e)}')), 500

@billing_bp.route('/records', methods=['POST'])
@token_required
def create_charging_record():
    """创建充电详单记录"""
    try:
        data = request.get_json()
        
        # 计算费用
        start_time = datetime.fromisoformat(data['start_time'])
        end_time = datetime.fromisoformat(data['end_time'])
        power_consumed = Decimal(str(data['power_consumed']))
        
        billing_result = BillingSystem.calculate_billing(start_time, end_time, power_consumed)
        
        # 插入记录
        query = """
        INSERT INTO charging_records 
        (id, user_id, pile_id, start_time, end_time, power_consumed, 
         electricity_fee, service_fee, total_fee, status, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        record_id = str(uuid.uuid4())
        params = [
            record_id,
            g.current_user_id,
            data['pile_id'],
            start_time,
            end_time,
            billing_result['power_consumed'],
            billing_result['electricity_fee'],
            billing_result['service_fee'],
            billing_result['total_fee'],
            'completed',
            datetime.now()
        ]
        
        DatabaseManager.execute_query(query, params)
        
        result_data = {'record_id': record_id, **billing_result}
        return jsonify(format_response(200, '充电详单创建成功', result_data))
    except Exception as e:
        return jsonify(format_response(4004, f'充电详单创建失败: {str(e)}')), 500