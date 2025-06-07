from decimal import Decimal
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from models.billing import ChargingRecord, SystemConfig, db
from models.user import User

class BillingService:
    """计费服务类"""
    
    # 默认电价配置
    DEFAULT_RATES = {
        'peak': Decimal('1.0'),      # 峰时电价
        'normal': Decimal('0.7'),    # 平时电价
        'valley': Decimal('0.4'),    # 谷时电价
        'service_fee': Decimal('0.8') # 服务费
    }
    
    # 峰平谷时段定义 (小时)
    PEAK_HOURS = [(10, 15), (18, 21)]    # 峰时段: 10-15, 18-21
    VALLEY_HOURS = [(23, 7)]             # 谷时段: 23-7 (跨日)
    # 其余时间为平时段: 7-10, 15-18, 21-23
    
    @staticmethod
    def get_billing_rates() -> Dict[str, float]:
        """获取当前计费费率配置"""
        try:
            config = SystemConfig.query.filter_by(config_key='billing_rates').first()
            if config and config.config_value:
                rates = config.config_value
                return {
                    'peak_rate': float(rates.get('peak', BillingService.DEFAULT_RATES['peak'])),
                    'normal_rate': float(rates.get('normal', BillingService.DEFAULT_RATES['normal'])),
                    'valley_rate': float(rates.get('valley', BillingService.DEFAULT_RATES['valley'])),
                    'service_fee_rate': float(rates.get('service_fee', BillingService.DEFAULT_RATES['service_fee']))
                }
        except Exception:
            pass
        
        # 返回默认配置
        return {
            'peak_rate': float(BillingService.DEFAULT_RATES['peak']),
            'normal_rate': float(BillingService.DEFAULT_RATES['normal']),
            'valley_rate': float(BillingService.DEFAULT_RATES['valley']),
            'service_fee_rate': float(BillingService.DEFAULT_RATES['service_fee'])
        }
    
    @staticmethod
    def update_billing_rates(rates: Dict[str, float]) -> bool:
        """更新计费费率配置"""
        try:
            config = SystemConfig.query.filter_by(config_key='billing_rates').first()
            if config:
                config.config_value = rates
                config.updated_at = datetime.utcnow()
            else:
                config = SystemConfig(
                    config_key='billing_rates',
                    config_value=rates,
                    description='充电计费费率配置'
                )
                db.session.add(config)
            
            db.session.commit()
            return True
        except Exception:
            db.session.rollback()
            return False
    
    @staticmethod
    def get_time_period(dt: datetime) -> str:
        """根据时间判断峰平谷时段"""
        hour = dt.hour
        
        # 检查峰时段
        for start, end in BillingService.PEAK_HOURS:
            if start <= hour < end:
                return 'peak'
        
        # 检查谷时段（需要考虑跨日情况）
        for start, end in BillingService.VALLEY_HOURS:
            if start > end:  # 跨日情况，如23-7
                if hour >= start or hour < end:
                    return 'valley'
            else:
                if start <= hour < end:
                    return 'valley'
        
        # 其他时间为平时段
        return 'normal'
    
    @staticmethod
    def calculate_duration_hours(start_time: datetime, end_time: datetime) -> float:
        """计算充电时长（小时）"""
        duration = end_time - start_time
        return duration.total_seconds() / 3600
    
    @staticmethod
    def calculate_billing(start_time: datetime, end_time: datetime, 
                         power_consumed: Decimal) -> Dict:
        """
        计算充电费用
        简化版本：按开始时间的时段统一计费
        完整版本应该按时段分段计费
        """
        # 获取当前费率配置
        rates = BillingService.get_billing_rates()
        
        # 计算充电时长
        duration_hours = BillingService.calculate_duration_hours(start_time, end_time)
        
        # 判断时段
        time_period = BillingService.get_time_period(start_time)
        
        # 获取对应时段的电价
        rate_key = f'{time_period}_rate'
        electricity_rate = Decimal(str(rates[rate_key]))
        service_fee_rate = Decimal(str(rates['service_fee_rate']))
        
        # 计算费用
        electricity_fee = power_consumed * electricity_rate
        service_fee = power_consumed * service_fee_rate
        total_fee = electricity_fee + service_fee
        
        return {
            'power_consumed': float(power_consumed),
            'duration_hours': round(duration_hours, 2),
            'time_period': time_period,
            'electricity_rate': float(electricity_rate),
            'service_fee_rate': float(service_fee_rate),
            'electricity_fee': float(electricity_fee),
            'service_fee': float(service_fee),
            'total_fee': float(total_fee),
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat()
        }
    
    @staticmethod
    def create_charging_record(user_id: int, pile_id: str, start_time: datetime,
                             end_time: datetime, power_consumed: Decimal) -> Optional[ChargingRecord]:
        """创建充电记录"""
        try:
            # 计算费用
            billing_result = BillingService.calculate_billing(start_time, end_time, power_consumed)
            
            # 创建记录
            record = ChargingRecord(
                user_id=user_id,
                pile_id=pile_id,
                start_time=start_time,
                end_time=end_time,
                power_consumed=power_consumed,
                electricity_fee=Decimal(str(billing_result['electricity_fee'])),
                service_fee=Decimal(str(billing_result['service_fee'])),
                total_fee=Decimal(str(billing_result['total_fee'])),
                time_period=billing_result['time_period'],
                status='completed'
            )
            
            db.session.add(record)
            db.session.commit()
            return record
        except Exception:
            db.session.rollback()
            return None
    
    @staticmethod
    def get_user_charging_records(user_id: int, page: int = 1, per_page: int = 10,
                                start_date: Optional[str] = None, 
                                end_date: Optional[str] = None) -> Dict:
        """获取用户充电记录"""
        try:
            # 构建查询
            query = ChargingRecord.query.filter_by(user_id=user_id)
            
            # 日期过滤
            if start_date:
                start_dt = datetime.fromisoformat(start_date)
                query = query.filter(ChargingRecord.created_at >= start_dt)
            
            if end_date:
                end_dt = datetime.fromisoformat(end_date)
                # 结束日期包含当天，所以加一天
                end_dt = end_dt + timedelta(days=1)
                query = query.filter(ChargingRecord.created_at < end_dt)
            
            # 按创建时间倒序排列
            query = query.order_by(ChargingRecord.created_at.desc())
            
            # 分页查询
            pagination = query.paginate(
                page=page,
                per_page=per_page,
                error_out=False
            )
            
            records = pagination.items
            
            # 计算汇总信息
            total_power = sum(float(record.power_consumed or 0) for record in records)
            total_cost = sum(float(record.total_fee or 0) for record in records)
            
            return {
                'records': [record.to_dict() for record in records],
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': pagination.total,
                    'pages': pagination.pages,
                    'has_prev': pagination.has_prev,
                    'has_next': pagination.has_next
                },
                'summary': {
                    'total_records': pagination.total,
                    'total_power_consumed': round(total_power, 3),
                    'total_cost': round(total_cost, 2)
                }
            }
        except Exception:
            return {
                'records': [],
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': 0,
                    'pages': 0,
                    'has_prev': False,
                    'has_next': False
                },
                'summary': {
                    'total_records': 0,
                    'total_power_consumed': 0.0,
                    'total_cost': 0.0
                }
            }
    
    @staticmethod
    def get_charging_record_detail(record_id: int, user_id: Optional[int] = None) -> Optional[Dict]:
        """获取充电记录详情"""
        try:
            query = ChargingRecord.query.filter_by(id=record_id)
            
            # 如果指定用户ID，则只查询该用户的记录
            if user_id:
                query = query.filter_by(user_id=user_id)
            
            record = query.first()
            if record:
                return record.to_detail_dict()
            return None
        except Exception:
            return None