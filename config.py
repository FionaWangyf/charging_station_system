import os
from datetime import timedelta

class Config:
    """基础配置类"""
    # 基本配置
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-here-change-in-production'
    
    # 数据库配置
    DB_HOST = os.environ.get('DB_HOST') or 'localhost'
    DB_PORT = os.environ.get('DB_PORT') or 3306
    DB_USER = os.environ.get('DB_USER') or 'root'
    DB_PASSWORD = os.environ.get('DB_PASSWORD') or 'password'
    DB_NAME = os.environ.get('DB_NAME') or 'charging_station'
    
    SQLALCHEMY_DATABASE_URI = f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
        'pool_timeout': 20,
        'max_overflow': 0
    }
    
    # Redis配置
    REDIS_HOST = os.environ.get('REDIS_HOST') or 'localhost'
    REDIS_PORT = os.environ.get('REDIS_PORT') or 6379
    REDIS_DB = os.environ.get('REDIS_DB') or 0
    REDIS_PASSWORD = os.environ.get('REDIS_PASSWORD') or None
    
    # JWT配置（保留以备后用）
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'jwt-secret-key-change-in-production'
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)  # token 24小时过期
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)  # 刷新token 30天过期
    
    # Session配置
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = False  # 生产环境应设为True
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)  # Session 24小时过期
    
    # 计费系统配置
    BILLING_CONFIG = {
        'default_rates': {
            'peak': 1.0,      # 峰时电价
            'normal': 0.7,    # 平时电价
            'valley': 0.4,    # 谷时电价
            'service_fee': 0.8 # 服务费
        },
        'peak_hours': [(10, 15), (18, 21)],    # 峰时段
        'valley_hours': [(23, 7)],             # 谷时段
        'max_power_per_charge': 1000,          # 单次充电最大电量
        'min_power_per_charge': 0.1            # 单次充电最小电量
    }
    
    # 充电桩配置
    CHARGING_CONFIG = {
        'fast_charging_power': 30,    # 快充功率 kW
        'slow_charging_power': 7,     # 慢充功率 kW
        'max_queue_length': 10,       # 最大队列长度
        'waiting_area_capacity': 6,   # 等候区容量
        'max_charging_duration': 480  # 最大充电时长（分钟）
    }
    
    # 分页配置
    PAGINATION_CONFIG = {
        'default_per_page': 10,
        'max_per_page': 100
    }
    
    # 日志配置
    LOG_LEVEL = os.environ.get('LOG_LEVEL') or 'INFO'
    LOG_FILE = os.environ.get('LOG_FILE') or 'logs/app.log'
    
    # 其他配置
    JSON_AS_ASCII = False  # 支持中文JSON响应
    JSONIFY_PRETTYPRINT_REGULAR = True  # JSON格式化
    
    # API配置
    API_VERSION = 'v1'
    API_TITLE = '充电桩管理系统API'
    API_DESCRIPTION = '充电桩管理系统的RESTful API接口'

class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True
    TESTING = False
    
    # 开发环境下的特殊配置
    SQLALCHEMY_ECHO = False  # 是否打印SQL语句
    
    # 更宽松的Session配置
    SESSION_COOKIE_SECURE = False

class TestingConfig(Config):
    """测试环境配置"""
    DEBUG = True
    TESTING = True
    
    # 测试数据库
    DB_NAME = os.environ.get('TEST_DB_NAME') or 'charging_station_test'
    SQLALCHEMY_DATABASE_URI = f'mysql+pymysql://{Config.DB_USER}:{Config.DB_PASSWORD}@{Config.DB_HOST}:{Config.DB_PORT}/{DB_NAME}'
    
    # 测试Redis
    REDIS_DB = 1  # 使用不同的Redis数据库
    
    # 禁用CSRF保护（测试环境）
    WTF_CSRF_ENABLED = False

class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False
    TESTING = False
    
    # 生产环境安全配置
    SESSION_COOKIE_SECURE = True  # HTTPS环境下启用
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Strict'
    
    # 更严格的数据库配置
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 3600,  # 1小时回收连接
        'pool_timeout': 30,
        'max_overflow': 10,
        'pool_size': 20
    }
    
    # 日志级别
    LOG_LEVEL = 'WARNING'

# 根据环境变量选择配置
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

def get_config():
    """获取当前配置"""
    config_name = os.environ.get('FLASK_ENV', 'development')
    return config.get(config_name, config['default'])