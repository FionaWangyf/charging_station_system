#!/usr/bin/env python3
"""
重建数据库脚本 - 解决外键约束问题
"""

import os
import sys
from flask import Flask
from config import get_config

def rebuild_database():
    """重建数据库"""
    app = Flask(__name__)
    
    # 加载配置
    config_class = get_config()
    app.config.from_object(config_class)
    
    # 初始化数据库
    from models.user import db
    db.init_app(app)
    
    with app.app_context():
        print("🔄 开始重建数据库...")
        
        try:
            # 方法1：禁用外键检查后删除所有表
            print("🔐 禁用外键检查...")
            from sqlalchemy import text
            
            with db.engine.connect() as connection:
                # 禁用外键检查
                connection.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
                
                # 获取所有表名
                result = connection.execute(text("SHOW TABLES"))
                tables = [row[0] for row in result]
                print(f"📋 发现现有表: {', '.join(tables)}")
                
                # 逐个删除表
                for table in tables:
                    try:
                        connection.execute(text(f"DROP TABLE IF EXISTS `{table}`"))
                        print(f"🗑️  删除表: {table}")
                    except Exception as e:
                        print(f"⚠️  删除表 {table} 时出错: {e}")
                
                # 重新启用外键检查
                connection.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
                connection.commit()
            
            print("✅ 现有表已删除")
            
            # 导入所有模型以确保表被创建
            from models.user import User
            from models.billing import ChargingRecord, SystemConfig, ChargingPile
            from models.charging import ChargingSession
            print("📦 模型已导入")
            
            # 重新创建所有表
            print("🏗️  创建新表...")
            db.create_all()
            print("✅ 新表已创建")
            
            # 查看创建的表
            with db.engine.connect() as connection:
                result = connection.execute(text("SHOW TABLES"))
                tables = [row[0] for row in result]
                print(f"📊 已创建的表: {', '.join(tables)}")
                
                # 显示表结构
                for table in tables:
                    result = connection.execute(text(f"DESCRIBE `{table}`"))
                    columns = [row[0] for row in result]
                    print(f"   📋 {table}: {', '.join(columns)}")
            
            # 初始化基础数据
            print("🌱 初始化基础数据...")
            init_basic_data()
            
            print("🎉 数据库重建完成!")
            return True
            
        except Exception as e:
            print(f"❌ 数据库重建失败: {e}")
            import traceback
            traceback.print_exc()
            return False

def init_basic_data():
    """初始化基础数据"""
    from models.user import db, User
    from models.billing import SystemConfig, ChargingPile
    
    try:
        # 创建默认管理员
        admin = User(
            car_id='ADMIN001',
            username='admin',
            car_capacity=0,
            user_type='admin'
        )
        admin.set_password('admin123')
        db.session.add(admin)
        
        # 创建测试用户
        test_user = User(
            car_id='京A12345',
            username='testuser',
            car_capacity=60.0,
            user_type='user'
        )
        test_user.set_password('password123')
        db.session.add(test_user)
        
        # 创建充电桩
        piles = [
            ChargingPile(id='A', name='快充桩A', pile_type='fast', power_rating=30.0, status='available'),
            ChargingPile(id='B', name='快充桩B', pile_type='fast', power_rating=30.0, status='available'),
            ChargingPile(id='C', name='慢充桩C', pile_type='slow', power_rating=7.0, status='available'),
            ChargingPile(id='D', name='慢充桩D', pile_type='slow', power_rating=7.0, status='available'),
            ChargingPile(id='E', name='慢充桩E', pile_type='slow', power_rating=7.0, status='available'),
        ]
        
        for pile in piles:
            db.session.add(pile)
        
        # 创建系统配置
        config = SystemConfig(
            config_key='billing_rates',
            config_value={
                'peak': 1.0,
                'normal': 0.7,
                'valley': 0.4,
                'service_fee': 0.8
            },
            description='充电计费费率配置'
        )
        db.session.add(config)
        
        # 提交所有更改
        db.session.commit()
        print("✅ 基础数据初始化完成")
        print("👤 管理员账户: admin / admin123")
        print("👤 测试用户: testuser / password123")
        print("🔌 充电桩: A(快充), B(快充), C(慢充), D(慢充), E(慢充)")
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ 基础数据初始化失败: {e}")
        raise

def check_database_connection():
    """检查数据库连接"""
    app = Flask(__name__)
    config_class = get_config()
    app.config.from_object(config_class)
    
    from models.user import db
    db.init_app(app)
    
    with app.app_context():
        try:
            from sqlalchemy import text
            with db.engine.connect() as connection:
                result = connection.execute(text("SELECT 1"))
                print("✅ 数据库连接成功")
                return True
        except Exception as e:
            print(f"❌ 数据库连接失败: {e}")
            return False

if __name__ == '__main__':
    print("=" * 60)
    print("充电桩管理系统 - 数据库重建工具")
    print("=" * 60)
    
    # 首先检查数据库连接
    if not check_database_connection():
        print("\n💡 请检查以下配置:")
        print("   1. MySQL服务是否启动")
        print("   2. 数据库用户名密码是否正确")
        print("   3. 数据库是否存在")
        print("   4. 网络连接是否正常")
        sys.exit(1)
    
    # 确认操作
    response = input("\n⚠️  此操作将删除所有现有数据！是否继续？(y/N): ").strip().lower()
    if response not in ['y', 'yes']:
        print("❌ 操作已取消")
        sys.exit(0)
    
    if rebuild_database():
        print("\n🚀 数据库重建成功！")
        print("📋 下一步操作:")
        print("   1. 运行调度引擎测试: python test_scheduler.py")
        print("   2. 启动应用: python app.py")
        print("   3. 使用Postman测试API")
    else:
        print("\n💥 数据库重建失败，请检查错误信息")
        sys.exit(1)