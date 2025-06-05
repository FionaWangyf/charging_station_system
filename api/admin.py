from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
import uuid

from auth import token_required, admin_required
from database import DatabaseManager
from config import redis_client
from utils import format_response


admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/piles', methods=['GET'])
@token_required
@admin_required
def get_piles():
    """获取充电桩状态"""
    try:
        status_filter = request.args.get('status')
        page = int(request.args.get('page', 1))
        size = int(request.args.get('size', 20))
        
        offset = (page - 1) * size
        
        # 构建查询条件
        where_conditions = []
        params = []
        
        if status_filter:
            where_conditions.append('status = %s')
            params.append(status_filter)
        
        where_clause = ' WHERE ' + ' AND '.join(where_conditions) if where_conditions else ''
        
        # 查询充电桩列表
        query = f"""
        SELECT p.*, 
               COUNT(cr.id) as total_charges,
               COALESCE(SUM(cr.total_fee), 0) as total_revenue
        FROM charging_piles p
        LEFT JOIN charging_records cr ON p.id = cr.pile_id AND cr.status = 'completed'
        {where_clause}
        GROUP BY p.id
        ORDER BY p.created_at DESC
        LIMIT %s OFFSET %s
        """
        params.extend([size, offset])
        
        piles = DatabaseManager.execute_query(query, params, fetch_all=True)
        
        # 查询总数
        count_query = f"SELECT COUNT(*) as total FROM charging_piles{where_clause}"
        count_result = DatabaseManager.execute_query(count_query, params[:-2], fetch_one=True)
        total = count_result['total'] if count_result else 0
        
        # 格式化结果
        pile_data = []
        for pile in piles:
            # 获取当前使用状态
            current_user = None
            if pile['status'] == 'occupied':
                user_query = """
                SELECT u.username, cr.start_time 
                FROM charging_records cr
                JOIN users u ON cr.user_id = u.id
                WHERE cr.pile_id = %s AND cr.status = 'charging'
                ORDER BY cr.start_time DESC
                LIMIT 1
                """
                user_result = DatabaseManager.execute_query(user_query, [pile['id']], fetch_one=True)
                if user_result:
                    current_user = {
                        'username': user_result['username'],
                        'start_time': user_result['start_time'].isoformat()
                    }
            
            pile_data.append({
                'id': pile['id'],
                'name': pile['name'],
                'status': pile['status'],
                'power_rating': float(pile['power_rating']),
                'location': pile['location'],
                'total_charges': pile['total_charges'],
                'total_revenue': float(pile['total_revenue']),
                'current_user': current_user,
                'created_at': pile['created_at'].isoformat(),
                'updated_at': pile['updated_at'].isoformat()
            })
        
        data = {
            'piles': pile_data,
            'pagination': {
                'page': page,
                'size': size,
                'total': total,
                'pages': (total + size - 1) // size
            }
        }
        
        return jsonify(format_response(200, '获取充电桩状态成功', data))
    except Exception as e:
        return jsonify(format_response(3001, f'获取充电桩状态失败: {str(e)}')), 500

@admin_bp.route('/system/status', methods=['GET'])
@token_required
@admin_required
def get_system_status():
    """获取系统状态"""
    try:
        # Redis连接状态
        try:
            redis_client.ping()
            redis_status = 'connected'
        except:
            redis_status = 'disconnected'
        
        # 数据库连接状态
        try:
            DatabaseManager.execute_query("SELECT 1", fetch_one=True)
            db_status = 'connected'
        except:
            db_status = 'disconnected'
        
        # 获取系统负载信息
        current_queue_size = redis_client.llen('charging_queue')
        
        # 活跃用户数（过去24小时）
        active_users_query = """
        SELECT COUNT(DISTINCT user_id) as count 
        FROM charging_records 
        WHERE created_at >= %s
        """
        yesterday = datetime.now() - timedelta(hours=24)
        active_users_result = DatabaseManager.execute_query(active_users_query, [yesterday], fetch_one=True)
        active_users = active_users_result['count'] if active_users_result else 0
        
        # 充电桩状态汇总
        pile_summary_query = """
        SELECT status, COUNT(*) as count 
        FROM charging_piles 
        GROUP BY status
        """
        pile_summary = DatabaseManager.execute_query(pile_summary_query, fetch_all=True)
        pile_status_counts = {row['status']: row['count'] for row in pile_summary}
        
        data = {
            'services': {
                'redis': redis_status,
                'database': db_status
            },
            'queue': {
                'current_size': current_queue_size,
                'max_size': 50  # 从配置中获取
            },
            'users': {
                'active_24h': active_users
            },
            'charging_piles': {
                'available': pile_status_counts.get('available', 0),
                'occupied': pile_status_counts.get('occupied', 0),
                'fault': pile_status_counts.get('fault', 0),
                'maintenance': pile_status_counts.get('maintenance', 0),
                'total': sum(pile_status_counts.values())
            },
            'system_time': datetime.now().isoformat()
        }
        
        return jsonify(format_response(200, '获取系统状态成功', data))
    except Exception as e:
        return jsonify(format_response(5006, f'获取系统状态失败: {str(e)}')), 500