from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from decimal import Decimal
from enum import Enum
from models.user import db

class ChargingMode(Enum):
    FAST = "fast"
    TRICKLE = "trickle"

class ChargingStatus(Enum):
    STATION_WAITING = "station_waiting"      # 充电站等候区等待
    ENGINE_QUEUED = "engine_queued"          # 调度引擎队列中
    CHARGING = "charging"                    # 正在充电
    COMPLETING = "completing"                # 充电完成中（过渡状态）
    COMPLETED = "completed"                  # 充电完成
    CANCELLED = "cancelled"                  # 已取消
    FAULT_COMPLETED = "fault_completed"      # 故障完成
    CANCELLING_AFTER_DISPATCH = "cancelling_after_dispatch"  # 调度后取消

class PileStatus(Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    MAINTENANCE = "maintenance"
    FAULT = "fault"

class ChargingSession(db.Model):
    """充电会话模型"""
    __tablename__ = 'charging_sessions'
    
    # 基本信息
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    session_id = db.Column(db.String(50), unique=True, nullable=False, comment='会话ID')
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, comment='用户ID')
    pile_id = db.Column(db.String(20), db.ForeignKey('charging_piles.id'), nullable=True, comment='充电桩ID')
    
    # 队列信息
    queue_number = db.Column(db.String(30), comment='队列号码')
    charging_mode = db.Column(db.Enum(ChargingMode), nullable=False, comment='充电模式')
    
    # 充电信息
    requested_amount = db.Column(db.Numeric(10, 2), nullable=False, comment='请求充电量(kWh)')
    actual_amount = db.Column(db.Numeric(10, 2), default=0.0, comment='实际充电量(kWh)')
    charging_duration = db.Column(db.Numeric(10, 4), default=0.0, comment='充电时长(小时)')
    
    # 时间信息
    start_time = db.Column(db.DateTime, comment='开始充电时间')
    end_time = db.Column(db.DateTime, comment='结束充电时间')
    
    # 费用信息
    charging_fee = db.Column(db.Numeric(10, 2), default=0.0, comment='充电费用')
    service_fee = db.Column(db.Numeric(10, 2), default=0.0, comment='服务费用')
    total_fee = db.Column(db.Numeric(10, 2), default=0.0, comment='总费用')
    
    # 状态信息
    status = db.Column(db.Enum(ChargingStatus), default=ChargingStatus.STATION_WAITING, comment='充电状态')
    
    # 时间戳
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')
    
    # 建立关系
    user = db.relationship('User', backref=db.backref('charging_sessions', lazy=True))
    pile = db.relationship('ChargingPile', backref=db.backref('charging_sessions', lazy=True))
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'session_id': self.session_id,
            'user_id': self.user_id,
            'pile_id': self.pile_id,
            'queue_number': self.queue_number,
            'charging_mode': self.charging_mode.value if self.charging_mode else None,
            'requested_amount': float(self.requested_amount) if self.requested_amount else 0.0,
            'actual_amount': float(self.actual_amount) if self.actual_amount else 0.0,
            'charging_duration': float(self.charging_duration) if self.charging_duration else 0.0,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'charging_fee': float(self.charging_fee) if self.charging_fee else 0.0,
            'service_fee': float(self.service_fee) if self.service_fee else 0.0,
            'total_fee': float(self.total_fee) if self.total_fee else 0.0,
            'status': self.status.value if self.status else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def to_detail_dict(self):
        """转换为详细字典格式（包含用户和充电桩信息）"""
        data = self.to_dict()
        if self.user:
            data['user_info'] = {
                'username': self.user.username,
                'car_id': self.user.car_id
            }
        if self.pile:
            data['pile_info'] = {
                'name': self.pile.name,
                'pile_type': self.pile.pile_type,
                'power_rating': float(self.pile.power_rating)
            }
        return data
    
    def __repr__(self):
        return f'<ChargingSession {self.session_id}>'

# 更新现有的ChargingPile模型（在billing.py中）以支持新的状态
# 注意：你可能需要将这个模型移动到这里，或者在billing.py中导入新的枚举