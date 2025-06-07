from flask import Flask
from flask_socketio import SocketIO
from flask_cors import CORS
from dotenv import load_dotenv
import os

# 加载环境变量
load_dotenv()

from config import get_config
from models.user import db
def init_database(app):
    """初始化数据库"""
    with app.app_context():
        try:
            # 检查数据库连接
            with db.engine.connect() as connection:
                connection.execute(db.text('SELECT 1'))
            print("✅ 数据库连接成功！")
            
            # 创建所有表
            db.create_all()
            print("✅ 数据表创建成功！")
            
            # 创建默认管理员账户
            from models.user import User
            admin = User.query.filter_by(username='admin').first()
            if not admin:
                admin = User(
                    car_id='ADMIN001',
                    username='admin',
                    car_capacity=0,
                    user_type='admin'
                )
                admin.set_password('admin123')
                db.session.add(admin)
                db.session.commit()
                print("✅ 默认管理员账户已创建: username=admin, password=admin123")
            
            # 初始化计费配置
            init_billing_config()
            
            # 创建示例充电桩
            init_sample_piles()
            
            print("✅ 数据库初始化完成！")
            
        except Exception as e:
            print(f"❌ 数据库初始化失败: {str(e)}")
            raise

def init_billing_config():
    """初始化计费配置"""
    try:
        from models.billing import SystemConfig
        config = SystemConfig.query.filter_by(config_key='billing_rates').first()
        if not config:
            default_rates = {
                'peak': 1.0,
                'normal': 0.7, 
                'valley': 0.4,
                'service_fee': 0.8
            }
            config = SystemConfig(
                config_key='billing_rates',
                config_value=default_rates,
                description='充电计费费率配置'
            )
            db.session.add(config)
            db.session.commit()
            print("✅ 计费配置初始化完成")
    except Exception as e:
        print(f"❌ 计费配置初始化失败: {e}")

def init_sample_piles():
    """创建示例充电桩"""
    try:
        from models.billing import ChargingPile
        if ChargingPile.query.count() == 0:
            sample_piles = [
                ChargingPile(id='A', name='快充桩A', pile_type='fast', power_rating=30.0),
                ChargingPile(id='B', name='快充桩B', pile_type='fast', power_rating=30.0),
                ChargingPile(id='C', name='慢充桩C', pile_type='slow', power_rating=7.0),
                ChargingPile(id='D', name='慢充桩D', pile_type='slow', power_rating=7.0),
                ChargingPile(id='E', name='慢充桩E', pile_type='slow', power_rating=7.0),
            ]
            
            for pile in sample_piles:
                db.session.add(pile)
            
            db.session.commit()
            print("✅ 示例充电桩创建完成")
    except Exception as e:
        print(f"❌ 示例充电桩创建失败: {e}")

# 确保调度引擎核心可以被导入
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'scheduler_core'))

def create_app():
    """创建Flask应用"""
    app = Flask(__name__)
    
    # 加载配置
    config_class = get_config()
    app.config.from_object(config_class)
    
    # 初始化扩展
    db.init_app(app)
    CORS(app, supports_credentials=True)
    
    # 初始化SocketIO
    socketio = SocketIO(
        app, 
        cors_allowed_origins="*", 
        async_mode='threading',
        logger=False,
        engineio_logger=False
    )
    
    # 注册WebSocket事件
    from websocket.events import register_socketio_events
    register_socketio_events(socketio)
    
    # 注册API蓝图
    register_blueprints(app)
    
    # 初始化数据库
    init_database(app)
    
    # 初始化充电服务
    init_charging_service(app, socketio)
    
    # 健康检查路由
    @app.route('/health')
    def health_check():
        return {'status': 'healthy', 'message': '充电桩管理系统运行正常'}
    
    @app.route('/')
    def home():
        return {
            'message': '智能充电站管理系统API',
            'status': 'running',
            'version': '1.0.0',
            'modules': ['用户服务', '调度引擎', '充电控制', '计费系统', '统计分析']
        }
    
    return app, socketio

def register_blueprints(app):
    """注册所有API蓝图"""
    
    # 现有的蓝图
    from api.user import user_bp
    from api.billing import billing_bp
    from api.statistics import statistics_bp
    
    app.register_blueprint(user_bp, url_prefix='/api/user')
    app.register_blueprint(billing_bp, url_prefix='/api/billing')
    app.register_blueprint(statistics_bp, url_prefix='/api/statistics')
    
    # 新增的充电相关蓝图
    from api.charging import charging_bp
    from api.admin import admin_bp
    
    app.register_blueprint(charging_bp, url_prefix='/api/charging')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    
    print("✅ 所有API蓝图已注册")

def init_charging_service(app, socketio):
    """初始化充电服务"""
    try:
        from services.charging_service import ChargingService
        
        # 创建充电服务实例并初始化
        charging_service = ChargingService(app=app, socketio=socketio)
        
        # 将服务实例注册到app扩展中
        if not hasattr(app, 'extensions'):
            app.extensions = {}
        app.extensions['charging_service'] = charging_service
        app.extensions['socketio'] = socketio
        
        print("✅ 充电服务初始化完成")
        
    except Exception as e:
        print(f"❌ 充电服务初始化失败: {str(e)}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == '__main__':
    app, socketio = create_app()
    
    # 开发环境运行配置
    debug_mode = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    port = int(os.environ.get('FLASK_PORT', 5001))
    
    print("=" * 60)
    print("智能充电站管理系统启动中...")
    print(f"调试模式: {debug_mode}")
    print(f"端口: {port}")
    print("模块状态:")
    print("  ✅ 用户认证与权限管理")
    print("  ✅ 充电调度引擎")
    print("  ✅ 充电控制与业务流程")
    print("  ✅ 计费系统与统计分析")
    print("  ✅ WebSocket实时通信")
    print("=" * 60)
    
    socketio.run(
        app, 
        debug=debug_mode, 
        port=port,
        host='0.0.0.0',
        allow_unsafe_werkzeug=True
    )