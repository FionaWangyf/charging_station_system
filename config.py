import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class Config:
    # 从环境变量读取敏感信息
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-only-for-development'
    
    # 数据库配置
    MYSQL_USERNAME = os.environ.get('MYSQL_USERNAME') or 'root'
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD') or 'password'
    DATABASE_URL = f"mysql://{MYSQL_USERNAME}:{MYSQL_PASSWORD}@localhost/charging_station"
    
    # 系统配置（这些可以公开）
    FAST_CHARGING_PILES = 2
    SLOW_CHARGING_PILES = 3
    WAITING_AREA_SIZE = 6