from models.user import db, User
from models.billing import ChargingRecord, SystemConfig, ChargingPile
from services.billing_service import BillingService
from sqlalchemy import text

def init_database(app):
    """初始化数据库"""
    with app.app_context():
        try:
            # 检查数据库连接
            with db.engine.connect() as connection:
                connection.execute(text('SELECT 1'))
            print("✅ 数据库连接成功！")
            
            # 创建所有表
            db.create_all()
            print("✅ 数据表创建成功！")
            
            # 创建默认管理员账户
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