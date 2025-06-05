from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta

from auth import token_required, admin_required
from database import DatabaseManager
from config import redis_client
from utils import format_response

statistics_bp = Blueprint('statistics', __name__)

@statistics_bp.route('/overview', methods=['GET'])
@token_required
@admin_required
def get_statistics_overview():
    """获取统计概览"""
    try:
        # 今日统计
        today = datetime.now().date()
        
        # 今日充电次数
        today_count_query = """
        SELECT COUNT(*) as count FROM charging_records 
        WHERE DATE(created_at) = %s AND status = 'completed'
        """
        today_count = DatabaseManager.execute_query(today_count_query, [today], fetch_one=True)
        
        # 今日收入
        today_revenue_query = """
        SELECT COALESCE(SUM(total_fee), 0) as revenue FROM charging_records 
        WHERE DATE(created_at) = %s AND status = 'completed'
        """
        today_revenue = DatabaseManager.execute_query(today_revenue_query, [today], fetch_one=True)
        
        # 充电桩状态统计
        pile_status_query = """
        SELECT status, COUNT(*) as count FROM charging_piles GROUP BY status
        """
        pile_status = DatabaseManager.execute_query(pile_status_query, fetch_all=True)
        
        # 当前排队人数
        queue_count = redis_client.llen('charging_queue')
        
        data = {
            'today_charging_count': today_count['count'] if today_count else 0,
            'today_revenue': float(today_revenue['revenue']) if today_revenue else 0.0,
            'pile_status': pile_status or [],
            'current_queue_count': queue_count,
            'date': today.isoformat()
        }
        
        return jsonify(format_response(200, '获取统计概览成功', data))
    except Exception as e:
        return jsonify(format_response(4005, f'获取统计概览失败: {str(e)}')), 500

@statistics_bp.route('/daily', methods=['GET'])
@token_required
@admin_required
def get_daily_statistics():
    """获取日统计数据"""
    try:
        days = int(request.args.get('days', 7))
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days-1)
        
        query = """
        SELECT DATE(created_at) as date,
               COUNT(*) as charging_count,
               COALESCE(SUM(total_fee), 0) as revenue,
               COALESCE(SUM(power_consumed), 0) as power_consumed
        FROM charging_records 
        WHERE DATE(created_at) BETWEEN %s AND %s AND status = 'completed'
        GROUP BY DATE(created_at)
        ORDER BY date
        """
        
        results = DatabaseManager.execute_query(query, [start_date, end_date], fetch_all=True)
        
        # 填充缺失日期
        daily_stats = []
        current_date = start_date
        result_dict = {item['date']: item for item in results}
        
        while current_date <= end_date:
            if current_date in result_dict:
                stats = result_dict[current_date]
                daily_stats.append({
                    'date': current_date.isoformat(),
                    'charging_count': stats['charging_count'],
                    'revenue': float(stats['revenue']),
                    'power_consumed': float(stats['power_consumed'])
                })
            else:
                daily_stats.append({
                    'date': current_date.isoformat(),
                    'charging_count': 0,
                    'revenue': 0.0,
                    'power_consumed': 0.0
                })
            current_date += timedelta(days=1)
        
        return jsonify(format_response(200, '获取日统计数据成功', daily_stats))
    except Exception as e:
        return jsonify(format_response(4006, f'获取日统计数据失败: {str(e)}')), 500