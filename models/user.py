from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import bcrypt

db = SQLAlchemy()

class User(db.Model):
    """用户模型"""
    __tablename__ = 'users'
    
    # 基本信息
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    car_id = db.Column(db.String(20), unique=True, nullable=False, comment='车牌号')
    username = db.Column(db.String(50), unique=True, nullable=False, comment='用户名')
    password_hash = db.Column(db.String(255), nullable=False, comment='密码哈希')
    car_capacity = db.Column(db.Float, nullable=False, comment='车辆电池容量(度)')
    
    # 用户类型：user(普通用户) or admin(管理员)
    user_type = db.Column(db.String(10), default='user', nullable=False, comment='用户类型')
    
    # 时间戳
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')
    
    # 用户状态：active(活跃), inactive(非活跃), banned(封禁)
    status = db.Column(db.String(10), default='active', nullable=False, comment='用户状态')
    
    def set_password(self, password):
        """设置密码（加密存储）"""
        salt = bcrypt.gensalt()
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def check_password(self, password):
        """验证密码"""
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'car_id': self.car_id,
            'username': self.username,
            'car_capacity': self.car_capacity,
            'user_type': self.user_type,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f'<User {self.username}>'


class UserToken(db.Model):
    """用户Token记录（用于token黑名单管理）"""
    __tablename__ = 'user_tokens'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    token_jti = db.Column(db.String(255), unique=True, nullable=False, comment='Token的JTI标识')
    token_type = db.Column(db.String(20), nullable=False, comment='Token类型: access/refresh')
    is_revoked = db.Column(db.Boolean, default=False, comment='是否已撤销')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    
    # 建立与用户的关系
    user = db.relationship('User', backref=db.backref('tokens', lazy=True))
    
    def __repr__(self):
        return f'<UserToken {self.token_jti}>'