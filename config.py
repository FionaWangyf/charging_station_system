import os
from dotenv import load_dotenv
from datetime import timedelta

# 加载环境变量
load_dotenv()

class Config:
    # 从环境变量读取敏感信息
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-only-for-development'
    
    # 数据库配置
    MYSQL_USERNAME = os.environ.get('MYSQL_USERNAME') or 'root'
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD') or 'password'
    DATABASE_URL = f"mysql://{MYSQL_USERNAME}:{MYSQL_PASSWORD}@localhost/charging_station"
    MYSQL_HOST = 'localhost'
    MYSQL_PORT = int(3306)
    MYSQL_USER = 'root'
    MYSQL_PASSWORD = '123456'
    MYSQL_DATABASE = 'charging_station'    

    # 系统配置（这些可以公开）
    FAST_CHARGING_PILES = 2
    SLOW_CHARGING_PILES = 3
    WAITING_AREA_SIZE = 6

    # Flask配置
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'charging_station_secret_key'

    
    # Redis配置
    REDIS_HOST = os.environ.get('REDIS_HOST') or 'localhost'
    REDIS_PORT = int(os.environ.get('REDIS_PORT') or 6379)
    REDIS_DB = int(os.environ.get('REDIS_DB') or 0)
    REDIS_PASSWORD = os.environ.get('REDIS_PASSWORD') or None
    
    # 系统参数配置（可通过API动态修改）
    FAST_CHARGING_PILE_NUM = 2  # 快充桩数量
    TRICKLE_CHARGING_PILE_NUM = 3  # 慢充桩数量
    WAITING_AREA_SIZE = 6  # 等候区容量
    CHARGING_QUEUE_LEN = 2  # 充电桩排队队列长度
    
    # 充电功率配置
    FAST_CHARGING_POWER = 30  # 快充功率：30度/小时
    TRICKLE_CHARGING_POWER = 7  # 慢充功率：7度/小时
    
    # 计费配置
    PEAK_PRICE = 1.0      # 峰时电价：1.0元/度
    NORMAL_PRICE = 0.7    # 平时电价：0.7元/度
    VALLEY_PRICE = 0.4    # 谷时电价：0.4元/度
    SERVICE_PRICE = 0.8   # 服务费：0.8元/度