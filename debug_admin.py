#!/usr/bin/env python3
"""
调试管理员API问题
"""

import requests
import json

def test_admin_login():
    """测试管理员登录"""
    print("🔐 测试管理员登录...")
    
    try:
        session = requests.Session()
        response = session.post(
            "http://localhost:5001/api/user/login",
            json={
                "username": "admin",
                "password": "admin123"
            }
        )
        
        print(f"登录状态码: {response.status_code}")
        print(f"登录响应: {response.text}")
        
        if response.status_code == 200:
            print("✅ 管理员登录成功")
            return session
        else:
            print("❌ 管理员登录失败")
            return None
            
    except Exception as e:
        print(f"❌ 登录异常: {e}")
        return None

def test_pile_operations(session):
    """测试充电桩操作"""
    if not session:
        print("❌ 没有有效的会话，跳过充电桩操作测试")
        return
    
    print("\n🔌 测试充电桩操作...")
    
    # 1. 获取充电桩状态
    print("1️⃣ 获取充电桩状态...")
    try:
        response = session.get("http://localhost:5001/api/admin/piles/status")
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            piles = data.get('data', {}).get('piles', [])
            print(f"✅ 找到 {len(piles)} 个充电桩")
            for pile in piles:
                print(f"   {pile['id']}: {pile['db_status']} ({pile['type']})")
        else:
            print(f"❌ 获取状态失败: {response.text}")
    except Exception as e:
        print(f"❌ 获取状态异常: {e}")
    
    # 2. 测试关闭充电桩 (不强制)
    print("\n2️⃣ 测试关闭充电桩A (非强制)...")
    try:
        response = session.post(
            "http://localhost:5001/api/admin/pile/stop",
            json={
                "pile_id": "A",
                "force": False
            }
        )
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.text}")
        
        if response.status_code == 200:
            print("✅ 关闭充电桩成功")
        else:
            print("❌ 关闭充电桩失败")
            
    except Exception as e:
        print(f"❌ 关闭充电桩异常: {e}")
    
    # 3. 测试启动充电桩
    print("\n3️⃣ 测试启动充电桩A...")
    try:
        response = session.post(
            "http://localhost:5001/api/admin/pile/start",
            json={
                "pile_id": "A"
            }
        )
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.text}")
        
        if response.status_code == 200:
            print("✅ 启动充电桩成功")
        else:
            print("❌ 启动充电桩失败")
            
    except Exception as e:
        print(f"❌ 启动充电桩异常: {e}")

def test_other_admin_apis(session):
    """测试其他管理员API"""
    if not session:
        return
    
    print("\n📊 测试其他管理员API...")
    
    # 测试系统概览
    print("1️⃣ 测试系统概览...")
    try:
        response = session.get("http://localhost:5001/api/admin/overview")
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            print("✅ 系统概览获取成功")
        else:
            print(f"❌ 系统概览失败: {response.text}")
    except Exception as e:
        print(f"❌ 系统概览异常: {e}")
    
    # 测试队列信息
    print("\n2️⃣ 测试队列信息...")
    try:
        response = session.get("http://localhost:5001/api/admin/queue/info")
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            print("✅ 队列信息获取成功")
        else:
            print(f"❌ 队列信息失败: {response.text}")
    except Exception as e:
        print(f"❌ 队列信息异常: {e}")

def check_server_logs():
    """检查服务器可能的错误"""
    print("\n📋 检查建议:")
    print("1. 检查服务器日志中的详细错误信息")
    print("2. 确认数据库连接正常")
    print("3. 确认Redis服务运行正常")
    print("4. 确认调度引擎模块加载正常")
    print("5. 确认所有模型关系正确")

def test_direct_database():
    """直接测试数据库连接"""
    print("\n🗄️ 测试数据库连接...")
    
    try:
        from flask import Flask
        from config import get_config
        from models.user import db
        from models.billing import ChargingPile
        
        app = Flask(__name__)
        config_class = get_config()
        app.config.from_object(config_class)
        db.init_app(app)
        
        with app.app_context():
            # 查询充电桩
            piles = ChargingPile.query.all()
            print(f"✅ 数据库查询成功，找到 {len(piles)} 个充电桩")
            for pile in piles:
                print(f"   {pile.id}: {pile.status} ({pile.pile_type})")
            
            return True
            
    except Exception as e:
        print(f"❌ 数据库测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_scheduler_core():
    """测试调度引擎核心"""
    print("\n⚙️ 测试调度引擎...")
    
    try:
        import scheduler_core
        print("✅ 调度引擎模块导入成功")
        
        # 测试获取所有充电桩
        try:
            piles = scheduler_core.get_all_piles()
            print(f"✅ 引擎中有 {len(piles)} 个充电桩")
            for pile in piles:
                print(f"   {pile.pile_id}: {pile.status.value}")
        except Exception as e:
            print(f"❌ 获取引擎充电桩失败: {e}")
        
        # 检查是否有remove_pile方法
        if hasattr(scheduler_core, 'remove_pile'):
            print("✅ 调度引擎有 remove_pile 方法")
        else:
            print("⚠️ 调度引擎没有 remove_pile 方法")
        
        # 检查是否有mark_fault方法
        if hasattr(scheduler_core, 'mark_fault'):
            print("✅ 调度引擎有 mark_fault 方法")
        else:
            print("⚠️ 调度引擎没有 mark_fault 方法")
        
        return True
        
    except Exception as e:
        print(f"❌ 调度引擎测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数"""
    print("=" * 60)
    print("🔧 管理员API调试工具")
    print("=" * 60)
    
    # 测试数据库
    print("第1步：测试数据库连接")
    if not test_direct_database():
        print("💥 数据库测试失败，请先解决数据库问题")
        return
    
    # 测试调度引擎
    print("\n第2步：测试调度引擎")
    test_scheduler_core()
    
    # 测试API
    print("\n第3步：测试管理员API")
    session = test_admin_login()
    
    if session:
        test_pile_operations(session)
        test_other_admin_apis(session)
    else:
        print("❌ 无法测试API，登录失败")
    
    # 提供建议
    check_server_logs()
    
    print("\n" + "=" * 60)
    print("调试完成")

if __name__ == "__main__":
    main()