from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from decimal import Decimal
from models.user import db

class ChargingRecord(db.Model):
    """充电记录模型"""
    __tablename__ = 'charging_records'
    
    # 基本信息
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, comment='用户ID')
    pile_id = db.Column(db.String(20), nullable=False, comment='充电桩ID')
    
    # 时间信息
    start_time = db.Column(db.DateTime, nullable=False, comment='开始充电时间')
    end_time = db.Column(db.DateTime, comment='结束充电时间')
    
    # 充电信息
    power_consumed = db.Column(db.Numeric(8, 3), default=0.000, comment='消耗电量(度)')
    
    # 费用信息
    electricity_fee = db.Column(db.Numeric(10, 2), default=0.00, comment='电费')
    service_fee = db.Column(db.Numeric(10, 2), default=0.00, comment='服务费')
    total_fee = db.Column(db.Numeric(10, 2), default=0.00, comment='总费用')
    
    # 时段信息
    time_period = db.Column(db.Enum('peak', 'normal', 'valley', name='time_period_enum'), 
                           nullable=False, comment='充电时段')
    
    # 状态信息
    status = db.Column(db.Enum('charging', 'completed', 'cancelled', 'fault', name='charging_status_enum'),
                      default='charging', comment='充电状态')
    
    # 时间戳
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')
    
    # 建立与用户的关系
    user = db.relationship('User', backref=db.backref('charging_records', lazy=True))
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'pile_id': self.pile_id,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'power_consumed': float(self.power_consumed) if self.power_consumed else 0.0,
            'electricity_fee': float(self.electricity_fee) if self.electricity_fee else 0.0,
            'service_fee': float(self.service_fee) if self.service_fee else 0.0,
            'total_fee': float(self.total_fee) if self.total_fee else 0.0,
            'time_period': self.time_period,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def to_detail_dict(self):
        """转换为详细字典格式（包含用户信息）"""
        data = self.to_dict()
        if self.user:
            data['user_info'] = {
                'username': self.user.username,
                'car_id': self.user.car_id
            }
        return data
    
    def __repr__(self):
        return f'<ChargingRecord {self.id}>'


class SystemConfig(db.Model):
    """系统配置模型"""
    __tablename__ = 'system_configs'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    config_key = db.Column(db.String(100), unique=True, nullable=False, comment='配置键')
    config_value = db.Column(db.JSON, nullable=False, comment='配置值')
    description = db.Column(db.Text, comment='配置描述')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'config_key': self.config_key,
            'config_value': self.config_value,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f'<SystemConfig {self.config_key}>'


class ChargingPile(db.Model):
    """充电桩模型"""
    __tablename__ = 'charging_piles'
    
    id = db.Column(db.String(20), primary_key=True, comment='充电桩ID')
    name = db.Column(db.String(100), nullable=False, comment='充电桩名称')
    pile_type = db.Column(db.Enum('fast', 'slow', name='pile_type_enum'), 
                         nullable=False, comment='充电桩类型')
    power_rating = db.Column(db.Numeric(5, 2), nullable=False, default=7.00, comment='额定功率(kW)')
    status = db.Column(db.Enum('available', 'occupied', 'fault', 'maintenance', name='pile_status_enum'),
                      default='available', comment='充电桩状态')
    location = db.Column(db.String(200), comment='位置描述')
    
    # 统计信息
    total_charges = db.Column(db.Integer, default=0, comment='总充电次数')
    total_power = db.Column(db.Numeric(10, 3), default=0.000, comment='总充电量')
    total_revenue = db.Column(db.Numeric(12, 2), default=0.00, comment='总收入')
    
    # 时间戳
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')
    
    # 建立与充电记录的关系
    charging_records = db.relationship('ChargingRecord', backref='pile', lazy=True,
                                     foreign_keys='ChargingRecord.pile_id',
                                     primaryjoin='ChargingPile.id == ChargingRecord.pile_id')
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'name': self.name,
            'pile_type': self.pile_type,
            'power_rating': float(self.power_rating),
            'status': self.status,
            'location': self.location or '',  # 添加这一行
            'total_charges': self.total_charges,
            'total_power': float(self.total_power) if self.total_power else 0.0,
            'total_revenue': float(self.total_revenue) if self.total_revenue else 0.0,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f'<ChargingPile {self.id}>'