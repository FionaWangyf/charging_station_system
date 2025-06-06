from flask import Flask
from flask_socketio import SocketIO
from flask_cors import CORS
import os

from database import DatabaseManager
from api.charging_control import ChargingControlManager  # 路径按实际结构调整

def create_app():
    app = Flask(__name__)
    
    # 加载配置
    app.config.from_object('config.Config')
    
    # 启用CORS
    CORS(app, origins="*")
    
    # 初始化SocketIO
    socketio = SocketIO(
        app, 
        cors_allowed_origins="*", 
        async_mode='threading',
        logger=True,
        engineio_logger=True
    )
    
    # 初始化数据库和充电控制管理器
    db_manager = DatabaseManager()
    charging_manager = ChargingControlManager(db_manager=db_manager, socketio=socketio)
    # 推荐注册到 app.extensions
    app.extensions = getattr(app, 'extensions', {})
    app.extensions['charging_manager'] = charging_manager
    app.extensions['socketio'] = socketio

    # 注册API路由
    register_routes(app, socketio)
    
    return app, socketio

def register_routes(app, socketio):
    """注册所有API路由"""
    
    # 基础路由
    @app.route('/')
    def home():
        return {
            'message': '智能充电站管理系统API',
            'status': 'running',
            'version': '1.0.0',
            'modules': ['用户服务', '调度引擎', '充电控制', '计费系统']
        }
    
    @app.route('/health')
    def health_check():
        return {'status': 'healthy', 'timestamp': '2024-01-01T00:00:00Z'}
    
    # 注册充电控制相关API
    from api.charging import charging_bp
    app.register_blueprint(charging_bp)
    print("✓ 充电控制与业务流程模块已注册")

# 创建应用实例
app, socketio = create_app()

if __name__ == '__main__':
    # 开发环境运行配置
    debug_mode = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    port = int(os.environ.get('FLASK_PORT', 5000))
    
    print("=" * 50)
    print("智能充电站管理系统启动中...")
    print(f"调试模式: {debug_mode}")
    print(f"端口: {port}")
    print("=" * 50)
    
    socketio.run(
        app, 
        debug=debug_mode, 
        port=port,
        host='0.0.0.0',
        allow_unsafe_werkzeug=True
    )