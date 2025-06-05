from decimal import Decimal
from datetime import datetime
from typing import Dict

class BillingSystem:
    """计费系统类"""
    
    # 峰平谷时段定义 (小时)
    PEAK_HOURS = [(10, 15), (18, 21)]  # 峰时段: 10-15, 18-21
    VALLEY_HOURS = [(23, 7)]          # 谷时段: 23-7
    # 其余时间为平时段
    
    # 电价配置 (元/kWh)
    ELECTRICITY_RATES = {
        'peak': Decimal('1.0'),     # 峰时电价
        'normal': Decimal('0.7'),   # 平时电价
        'valley': Decimal('0.4')    # 谷时电价
    }
    
    # 服务费配置 (元/kWh)
    SERVICE_FEE_RATE = Decimal('0.8')
    
    @staticmethod
    def get_time_period(hour: int) -> str:
        """根据小时判断峰平谷时段"""
        for start, end in BillingSystem.PEAK_HOURS:
            if start <= hour < end:
                return 'peak'
        
        for start, end in BillingSystem.VALLEY_HOURS:
            if (start <= hour <= 23) or (0 <= hour < end):
                return 'valley'
        
        return 'normal'
    
    @staticmethod
    def calculate_billing(start_time: datetime, end_time: datetime, power_consumed: Decimal) -> Dict:
        """计算充电费用"""
        duration = end_time - start_time
        total_hours = Decimal(str(duration.total_seconds() / 3600))
        
        # 简化计算：按开始时间的时段计算（实际应按时段分段计算）
        time_period = BillingSystem.get_time_period(start_time.hour)
        
        electricity_rate = BillingSystem.ELECTRICITY_RATES[time_period]
        electricity_fee = power_consumed * electricity_rate
        service_fee = power_consumed * BillingSystem.SERVICE_FEE_RATE
        total_fee = electricity_fee + service_fee
        
        return {
            'power_consumed': float(power_consumed),
            'duration_hours': float(total_hours),
            'time_period': time_period,
            'electricity_rate': float(electricity_rate),
            'electricity_fee': float(electricity_fee),
            'service_fee': float(service_fee),
            'total_fee': float(total_fee)
        }