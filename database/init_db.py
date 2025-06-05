from models.user import db, User
from sqlalchemy import text

def init_database(app):
    """初始化数据库"""
    with app.app_context():
        try:
            # 检查数据库连接 - 使用新的SQLAlchemy语法
            with db.engine.connect() as connection:
                connection.execute(text('SELECT 1'))
            print("数据库连接成功！")
            
            # 创建所有表
            db.create_all()
            print("数据表创建成功！")
            
            # 创建默认管理员账户
            admin = User.query.filter_by(username='admin').first()
            if not admin:
                admin = User(
                    car_id='ADMIN001',
                    username='admin',
                    car_capacity=0,  # 管理员不需要车辆信息
                    user_type='admin'
                )
                admin.set_password('admin123')  # 默认密码，生产环境需要修改
                db.session.add(admin)
                db.session.commit()
                print("✅ 默认管理员账户已创建: username=admin, password=admin123")
            else:
                print("✅ 管理员账户已存在")
            
            print("✅ 数据库初始化完成！")
            
        except Exception as e:
            print(f"❌ 数据库初始化失败: {str(e)}")
            print("请检查：")
            print("1. MySQL服务是否启动")
            print("2. 数据库 'charging_station' 是否已创建")
            print("3. 数据库连接配置是否正确")
            raise