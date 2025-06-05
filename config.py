import os
from dotenv import load_dotenv
import redis
import json
from typing import Dict



# 数据库连接配置
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'root',
    'database': 'charging_station',
    'charset': 'utf8mb4',
    'port': 3306,
}

# Redis连接
redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

class ConfigManager:
    """系统配置管理类"""
    
    DEFAULT_CONFIG = {
        'system': {
            'max_queue_size': 50,
            'default_charging_power': 7.0,  # kW
            'max_charging_duration': 480,   # 分钟
            'queue_timeout': 300,           # 秒
        },
        'billing': {
            'peak_rate': 1.0,
            'normal_rate': 0.7,
            'valley_rate': 0.4,
            'service_fee_rate': 0.8,
        },
        'notification': {
            'queue_position_threshold': 3,
            'charging_complete_notify': True,
            'fault_notify': True,
        }
    }
    
    @staticmethod
    def get_config(key: str = None):
        """获取系统配置"""
        config_json = redis_client.get('system_config')
        if not config_json:
            # 初始化默认配置
            ConfigManager.set_config(ConfigManager.DEFAULT_CONFIG)
            config = ConfigManager.DEFAULT_CONFIG
        else:
            config = json.loads(config_json)
        
        if key:
            return config.get(key, {})
        return config
    
    @staticmethod
    def set_config(config: Dict):
        """设置系统配置"""
        redis_client.set('system_config', json.dumps(config))
    
    @staticmethod
    def update_config(key: str, value: Dict):
        """更新特定配置项"""
        config = ConfigManager.get_config()
        config[key] = value
        ConfigManager.set_config(config)