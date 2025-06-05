from flask import Flask, jsonify
from datetime import datetime

# 创建Flask应用
app = Flask(__name__)
app.config['SECRET_KEY'] = 'asdfg'

# 导入模块
from database import init_database
from config import ConfigManager

# 导入蓝图
from api.billing import billing_bp
from api.statistics import statistics_bp
from api.config import config_bp
from api.admin import admin_bp

# from charging_station_system.database import init_database
# from charging_station_system.config import ConfigManager

# from charging_station_system.api.billing import billing_bp
# from charging_station_system.api.statistics import statistics_bp
# from charging_station_system.api.config import config_bp
# from charging_station_system.api.admin import admin_bp


# 注册蓝图
app.register_blueprint(billing_bp, url_prefix='/api/billing')
app.register_blueprint(statistics_bp, url_prefix='/api/statistics')
app.register_blueprint(config_bp, url_prefix='/api/system/config')
app.register_blueprint(admin_bp, url_prefix='/api/admin')

@app.route('/')
def home():
    return {'message': '充电站管理系统API', 'status': 'running'}

# 错误处理
@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'code': 5404,
        'message': '接口不存在',
        'timestamp': datetime.now().isoformat()
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'code': 5500,
        'message': '服务器内部错误',
        'timestamp': datetime.now().isoformat()
    }), 500

def initialize_system():
    """初始化系统"""
    try:
        # 初始化数据库
        print("正在初始化数据库...")
        init_database()
        print("数据库初始化完成")
        
        # 初始化默认配置
        print("正在初始化系统配置...")
        ConfigManager.get_config()
        print("系统配置初始化完成")
        
        return True
    except Exception as e:
        print(f"系统初始化失败: {e}")
        return False

if __name__ == '__main__':
    print("=" * 50)
    print("充电站管理系统启动中...")
    print("=" * 50)
    
    # 初始化系统
    if not initialize_system():
        print("系统初始化失败，无法启动服务")
        exit(1)
    
    print("\n包含功能：")
    print("- 用户管理和认证")
    print("- 充电桩管理和排队系统")
    print("- 计费系统（峰平谷电价、服务费计算）")
    print("- 充电详单生成和查询")
    print("- 数据统计和报表功能")
    print("- 系统配置管理")
    print("- 数据库设计和维护")
    print("- 管理员接口")
    print("- 系统监控")
    
    print(f"\n系统启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("API服务运行在: http://0.0.0.0:5000")
    print("=" * 50)
    
    # 启动应用
    app.run(debug=False, host='0.0.0.0', port=5000)