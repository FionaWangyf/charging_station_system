from flask import Blueprint, jsonify, request
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from sqlalchemy import func, and_
from models.billing import ChargingRecord, ChargingPile, db
from models.user import User

class StatisticsService:
    """统计服务类"""
    
    @staticmethod
    def get_overview_statistics() -> Dict:
        """获取系统概览统计"""
        try:
            today = datetime.now().date()
            yesterday = today - timedelta(days=1)
            
            # 今日充电次数
            today_count = db.session.query(func.count(ChargingRecord.id)).filter(
                func.date(ChargingRecord.created_at) == today,
                ChargingRecord.status == 'completed'
            ).scalar() or 0
            
            # 昨日充电次数
            yesterday_count = db.session.query(func.count(ChargingRecord.id)).filter(
                func.date(ChargingRecord.created_at) == yesterday,
                ChargingRecord.status == 'completed'
            ).scalar() or 0
            
            # 今日收入
            today_revenue = db.session.query(func.sum(ChargingRecord.total_fee)).filter(
                func.date(ChargingRecord.created_at) == today,
                ChargingRecord.status == 'completed'
            ).scalar() or 0
            
            # 昨日收入
            yesterday_revenue = db.session.query(func.sum(ChargingRecord.total_fee)).filter(
                func.date(ChargingRecord.created_at) == yesterday,
                ChargingRecord.status == 'completed'
            ).scalar() or 0
            
            # 今日充电量
            today_power = db.session.query(func.sum(ChargingRecord.power_consumed)).filter(
                func.date(ChargingRecord.created_at) == today,
                ChargingRecord.status == 'completed'
            ).scalar() or 0
            
            # 活跃用户数（过去7天）
            week_ago = datetime.now() - timedelta(days=7)
            active_users = db.session.query(func.count(func.distinct(ChargingRecord.user_id))).filter(
                ChargingRecord.created_at >= week_ago
            ).scalar() or 0
            
            # 充电桩状态统计
            pile_status_query = db.session.query(
                ChargingPile.status,
                func.count(ChargingPile.id)
            ).group_by(ChargingPile.status).all()
            
            pile_status_counts = {status: count for status, count in pile_status_query}
            
            # 计算增长率
            count_growth = 0
            if yesterday_count > 0:
                count_growth = ((today_count - yesterday_count) / yesterday_count) * 100
            
            revenue_growth = 0
            if yesterday_revenue > 0:
                revenue_growth = ((float(today_revenue) - float(yesterday_revenue)) / float(yesterday_revenue)) * 100
            
            return {
                'today': {
                    'charging_count': today_count,
                    'revenue': float(today_revenue),
                    'power_consumed': float(today_power),
                    'date': today.isoformat()
                },
                'yesterday': {
                    'charging_count': yesterday_count,
                    'revenue': float(yesterday_revenue),
                    'date': yesterday.isoformat()
                },
                'growth': {
                    'count_growth_rate': round(count_growth, 2),
                    'revenue_growth_rate': round(revenue_growth, 2)
                },
                'users': {
                    'active_users_7days': active_users,
                    'total_users': User.query.count()
                },
                'charging_piles': {
                    'available': pile_status_counts.get('available', 0),
                    'occupied': pile_status_counts.get('occupied', 0),
                    'fault': pile_status_counts.get('fault', 0),
                    'maintenance': pile_status_counts.get('maintenance', 0),
                    'total': sum(pile_status_counts.values())
                }
            }
        except Exception as e:
            print(f"获取概览统计失败: {e}")
            return {}
    
    @staticmethod
    def get_daily_statistics(days: int = 7) -> List[Dict]:
        """获取日统计数据 - 按充电桩分组"""
        try:
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=days-1)
            
            # 按充电桩分组查询统计数据
            pile_query = db.session.query(
                ChargingRecord.pile_id,
                func.count(ChargingRecord.id).label('charging_count'),
                func.sum(ChargingRecord.total_fee).label('revenue'),
                func.sum(ChargingRecord.power_consumed).label('power_consumed'),
                #func.sum(ChargingRecord.charging_duration).label('total_duration')
            ).filter(
                ChargingRecord.status == 'completed',
                func.date(ChargingRecord.created_at) >= start_date,
                func.date(ChargingRecord.created_at) <= end_date
            ).group_by(ChargingRecord.pile_id).all()
            
            # 获取所有充电桩信息，确保没有数据的充电桩也显示
            from models.billing import ChargingPile
            all_piles = ChargingPile.query.all()
            
            # 构建结果
            result = []
            for pile in all_piles:
                pile_data = {
                    'pile_id': pile.id,
                    'charging_count': 0,
                    'revenue': 0.0,
                    'power_consumed': 0.0,
                    #'total_duration': 0.0
                }
                
                # 查找对应的统计数据
                for row in pile_query:
                    if row.pile_id == pile.id:
                        pile_data.update({
                            'charging_count': row.charging_count or 0,
                            'revenue': float(row.revenue or 0),
                            'power_consumed': float(row.power_consumed or 0),
                            #'total_duration': float(row.total_duration or 0)
                        })
                        break
                
                result.append(pile_data)
            
            return result
            
        except Exception as e:
            print(f"获取日统计数据失败: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    @staticmethod
    def get_hourly_statistics(date: Optional[str] = None) -> List[Dict]:
        """获取小时统计数据"""
        try:
            if date:
                target_date = datetime.fromisoformat(date).date()
            else:
                target_date = datetime.now().date()
            
            # 查询小时统计
            hourly_query = db.session.query(
                func.hour(ChargingRecord.created_at).label('hour'),
                func.count(ChargingRecord.id).label('charging_count'),
                func.sum(ChargingRecord.total_fee).label('revenue'),
                func.sum(ChargingRecord.power_consumed).label('power_consumed')
            ).filter(
                and_(
                    func.date(ChargingRecord.created_at) == target_date,
                    ChargingRecord.status == 'completed'
                )
            ).group_by(func.hour(ChargingRecord.created_at)).all()
            
            # 创建结果字典
            result_dict = {}
            for row in hourly_query:
                result_dict[row.hour] = {
                    'hour': row.hour,
                    'charging_count': row.charging_count,
                    'revenue': float(row.revenue or 0),
                    'power_consumed': float(row.power_consumed or 0)
                }
            
            # 填充24小时数据
            hourly_stats = []
            for hour in range(24):
                if hour in result_dict:
                    hourly_stats.append(result_dict[hour])
                else:
                    hourly_stats.append({
                        'hour': hour,
                        'charging_count': 0,
                        'revenue': 0.0,
                        'power_consumed': 0.0
                    })
            
            return hourly_stats
        except Exception as e:
            print(f"获取小时统计失败: {e}")
            return []
    
    @staticmethod
    def get_pile_usage_statistics() -> List[Dict]:
        """获取充电桩使用统计"""
        try:
            # 查询每个充电桩的使用情况
            pile_query = db.session.query(
                ChargingRecord.pile_id,
                func.count(ChargingRecord.id).label('total_charges'),
                func.sum(ChargingRecord.total_fee).label('total_revenue'),
                func.sum(ChargingRecord.power_consumed).label('total_power'),
                func.avg(ChargingRecord.power_consumed).label('avg_power'),
                func.max(ChargingRecord.created_at).label('last_charge_time')
            ).filter(
                ChargingRecord.status == 'completed'
            ).group_by(ChargingRecord.pile_id).all()
            
            pile_stats = []
            for row in pile_query:
                # 获取充电桩基本信息
                pile = ChargingPile.query.get(row.pile_id)
                
                pile_stats.append({
                    'pile_id': row.pile_id,
                    'pile_name': pile.name if pile else row.pile_id,
                    'pile_type': pile.pile_type if pile else 'unknown',
                    'pile_status': pile.status if pile else 'unknown',
                    'total_charges': row.total_charges,
                    'total_revenue': float(row.total_revenue or 0),
                    'total_power': float(row.total_power or 0),
                    'avg_power_per_charge': float(row.avg_power or 0),
                    'last_charge_time': row.last_charge_time.isoformat() if row.last_charge_time else None,
                    'utilization_rate': 0  # TODO: 计算利用率
                })
            
            # 按总收入排序
            pile_stats.sort(key=lambda x: x['total_revenue'], reverse=True)
            
            return pile_stats
        except Exception as e:
            print(f"获取充电桩统计失败: {e}")
            return []
    
    @staticmethod
    def get_time_period_statistics() -> Dict:
        """获取峰平谷时段统计"""
        try:
            # 查询不同时段的统计
            period_query = db.session.query(
                func.hour(ChargingRecord.created_at).label('hour'),
                func.count(ChargingRecord.id).label('charging_count'),
                func.sum(ChargingRecord.total_fee).label('revenue'),
                func.sum(ChargingRecord.power_consumed).label('power_consumed')
            ).filter(
                ChargingRecord.status == 'completed'
            ).group_by(func.hour(ChargingRecord.created_at)).all()
            
            # 定义峰平谷时段
            peak_hours = [10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21]
            valley_hours = [0, 1, 2, 3, 4, 5, 6, 7]
            
            # 初始化统计结果
            period_stats = {
                'peak': {'charging_count': 0, 'revenue': 0.0, 'power_consumed': 0.0},
                'normal': {'charging_count': 0, 'revenue': 0.0, 'power_consumed': 0.0},
                'valley': {'charging_count': 0, 'revenue': 0.0, 'power_consumed': 0.0}
            }
            
            # 统计各时段数据
            for row in period_query:
                hour = row.hour
                if hour in peak_hours:
                    period = 'peak'
                elif hour in valley_hours:
                    period = 'valley'
                else:
                    period = 'normal'
                
                period_stats[period]['charging_count'] += row.charging_count
                period_stats[period]['revenue'] += float(row.revenue or 0)
                period_stats[period]['power_consumed'] += float(row.power_consumed or 0)
            
            return period_stats
        except Exception as e:
            print(f"获取峰平谷时段统计失败: {e}")
            return {}
    
    @staticmethod
    def get_user_ranking(limit: int = 10) -> List[Dict]:
        """获取用户排名"""
        try:
            # 查询用户充电统计
            user_query = db.session.query(
                ChargingRecord.user_id,
                func.count(ChargingRecord.id).label('total_charges'),
                func.sum(ChargingRecord.total_fee).label('total_revenue'),
                func.sum(ChargingRecord.power_consumed).label('total_power')
            ).filter(
                ChargingRecord.status == 'completed'
            ).group_by(ChargingRecord.user_id).order_by(
                func.sum(ChargingRecord.total_fee).desc()
            ).limit(limit).all()
            
            user_ranking = []
            for row in user_query:
                user = User.query.get(row.user_id)
                if user:
                    user_ranking.append({
                        'user_id': row.user_id,
                        'username': user.username,
                        'total_charges': row.total_charges,
                        'total_revenue': float(row.total_revenue or 0),
                        'total_power': float(row.total_power or 0)
                    })
            
            return user_ranking
        except Exception as e:
            print(f"获取用户排名失败: {e}")
            return []

# 创建蓝图
statistics_bp = Blueprint('statistics', __name__)

# 创建服务实例
statistics_service = StatisticsService()

@statistics_bp.route('/overview', methods=['GET'])
def get_overview():
    """获取系统概览统计"""
    return jsonify(statistics_service.get_overview_statistics())

@statistics_bp.route('/daily', methods=['GET'])
def get_daily():
    """获取日统计数据"""
    days = request.args.get('days', default=7, type=int)
    from utils.response import success_response
    return success_response(data=statistics_service.get_daily_statistics(days))
    #return jsonify(statistics_service.get_daily_statistics(days))

@statistics_bp.route('/hourly', methods=['GET'])
def get_hourly():
    """获取小时统计数据"""
    date = request.args.get('date')
    return jsonify(statistics_service.get_hourly_statistics(date))

@statistics_bp.route('/pile-usage', methods=['GET'])
def get_pile_usage():
    """获取充电桩使用统计"""
    return jsonify(statistics_service.get_pile_usage_statistics())

@statistics_bp.route('/time-period', methods=['GET'])
def get_time_period():
    """获取峰平谷时段统计"""
    return jsonify(statistics_service.get_time_period_statistics())

@statistics_bp.route('/user-ranking', methods=['GET'])
def get_user_ranking():
    """获取用户排名"""
    limit = request.args.get('limit', default=10, type=int)
    return jsonify(statistics_service.get_user_ranking(limit))