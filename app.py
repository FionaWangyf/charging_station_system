from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
import os

# 加载环境变量
load_dotenv()

from config import get_config
from models.user import db
from database.init_db import init_database

def create_app():
    """创建Flask应用"""
    app = Flask(__name__)
    
    # 加载配置
    config_class = get_config()
    app.config.from_object(config_class)
    
    # 初始化扩展
    db.init_app(app)
    CORS(app, supports_credentials=True)
    
    # 注册API蓝图
    from api.user import user_bp
    from api.billing import billing_bp
    from api.statistics import statistics_bp
    
    app.register_blueprint(user_bp, url_prefix='/api/user')
    app.register_blueprint(billing_bp, url_prefix='/api/billing')
    app.register_blueprint(statistics_bp, url_prefix='/api/statistics')
    
    # 初始化数据库
    init_database(app)
    
    # 健康检查路由
    @app.route('/health')
    def health_check():
        return {'status': 'healthy', 'message': '充电桩管理系统运行正常'}
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5001)