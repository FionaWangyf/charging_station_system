#!/usr/bin/env python3
"""
简化修复脚本 - 直接使用SQL避免ORM关系问题
"""

import sys
import os
from flask import Flask
from config import get_config

def direct_sql_cleanup():
    """使用直接SQL清理问题数据"""
    app = Flask(__name__)
    config_class = get_config()
    app.config.from_object(config_class)
    
    from models.user import db
    from sqlalchemy import text
    
    db.init_app(app)
    
    with app.app_context():
        try:
            print("🔧 使用直接SQL进行数据清理...")
            
            # 1. 查看当前completing状态的会话
            result = db.session.execute(text(
                "SELECT COUNT(*) as count FROM charging_sessions WHERE status = 'completing'"
            ))
            completing_count = result.fetchone()[0]
            print(f"📊 发现 {completing_count} 个completing状态的会话")
            
            if completing_count > 0:
                # 2. 将所有completing状态改为completed
                result = db.session.execute(text("""
                    UPDATE charging_sessions 
                    SET status = 'completed', 
                        end_time = NOW(),
                        charging_fee = COALESCE(charging_fee, 0.0),
                        service_fee = COALESCE(service_fee, 0.0),
                        total_fee = COALESCE(total_fee, 0.0)
                    WHERE status = 'completing'
                """))
                
                print(f"✅ 更新了 {result.rowcount} 个completing会话为completed状态")
            
            # 3. 查看并清理其他活跃状态
            active_statuses = ['station_waiting', 'engine_queued', 'charging']
            for status in active_statuses:
                result = db.session.execute(text(
                    f"SELECT COUNT(*) as count FROM charging_sessions WHERE status = '{status}'"
                ))
                count = result.fetchone()[0]
                
                if count > 0:
                    print(f"📊 发现 {count} 个 {status} 状态的会话")
                    
                    # 可选：将这些也设为取消状态
                    response = input(f"是否将 {count} 个 {status} 状态的会话设为cancelled？(y/N): ").strip().lower()
                    if response in ['y', 'yes']:
                        result = db.session.execute(text(f"""
                            UPDATE charging_sessions 
                            SET status = 'cancelled', 
                                end_time = NOW()
                            WHERE status = '{status}'
                        """))
                        print(f"✅ 取消了 {result.rowcount} 个 {status} 会话")
            
            # 4. 重置所有充电桩状态为available
            result = db.session.execute(text(
                "SELECT COUNT(*) as count FROM charging_piles WHERE status != 'available'"
            ))
            non_available_count = result.fetchone()[0]
            
            if non_available_count > 0:
                print(f"📊 发现 {non_available_count} 个非available状态的充电桩")
                
                result = db.session.execute(text(
                    "UPDATE charging_piles SET status = 'available'"
                ))
                print(f"✅ 重置了 {result.rowcount} 个充电桩状态为available")
            
            # 5. 提交所有更改
            db.session.commit()
            print("✅ 所有SQL更改已提交")
            
            # 6. 显示最终状态
            print("\n📊 清理后状态:")
            
            # 会话状态统计
            result = db.session.execute(text("""
                SELECT status, COUNT(*) as count 
                FROM charging_sessions 
                GROUP BY status
            """))
            print("充电会话状态:")
            for row in result:
                print(f"   {row.status}: {row.count}")
            
            # 充电桩状态统计
            result = db.session.execute(text("""
                SELECT status, COUNT(*) as count 
                FROM charging_piles 
                GROUP BY status
            """))
            print("充电桩状态:")
            for row in result:
                print(f"   {row.status}: {row.count}")
            
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ SQL清理失败: {e}")
            import traceback
            traceback.print_exc()
            return False

def clear_redis_cache():
    """清理Redis缓存"""
    try:
        import redis
        from config import get_config
        
        config = get_config()
        redis_client = redis.Redis(
            host=getattr(config, 'REDIS_HOST', 'localhost'),
            port=getattr(config, 'REDIS_PORT', 6379),
            db=getattr(config, 'REDIS_DB', 0),
            decode_responses=True
        )
        
        print("🧹 清理Redis缓存...")
        
        # 清理队列
        keys_to_delete = [
            'station_waiting_area:fast',
            'station_waiting_area:trickle'
        ]
        
        for key in keys_to_delete:
            redis_client.delete(key)
            print(f"   删除键: {key}")
        
        # 清理session相关键
        session_keys = redis_client.keys('session_*')
        if session_keys:
            redis_client.delete(*session_keys)
            print(f"   删除了 {len(session_keys)} 个session键")
        
        # 清理pile状态键
        pile_keys = redis_client.keys('pile_status:*')
        if pile_keys:
            redis_client.delete(*pile_keys)
            print(f"   删除了 {len(pile_keys)} 个pile状态键")
        
        # 清理其他可能的键
        other_keys = redis_client.keys('*lock*') + redis_client.keys('*completing*')
        if other_keys:
            redis_client.delete(*other_keys)
            print(f"   删除了 {len(other_keys)} 个其他键")
        
        print("✅ Redis缓存清理完成")
        return True
        
    except Exception as e:
        print(f"⚠️  Redis清理失败（可能Redis未启动）: {e}")
        return False

def test_type_conversion():
    """测试类型转换"""
    print("🧪 测试数据类型转换...")
    
    from decimal import Decimal
    
    test_cases = [
        (25.5, "float"),
        (Decimal('25.5'), "Decimal"),
        ("25.5", "string"),
        (25, "int")
    ]
    
    for value, type_name in test_cases:
        try:
            # 测试转换为Decimal
            if isinstance(value, (int, float)):
                decimal_value = Decimal(str(value))
            elif isinstance(value, str):
                decimal_value = Decimal(value)
            elif isinstance(value, Decimal):
                decimal_value = value
            else:
                decimal_value = Decimal(str(float(value)))
            
            print(f"   ✅ {type_name} {value} -> Decimal {decimal_value}")
            
            # 测试Decimal运算
            rate = Decimal('1.0')
            result = decimal_value * rate
            print(f"      运算测试: {decimal_value} * {rate} = {result}")
            
        except Exception as e:
            print(f"   ❌ {type_name} {value} 转换失败: {e}")
    
    print("✅ 类型转换测试完成")

def main():
    """主函数"""
    print("=" * 60)
    print("🔧 简化数据修复工具")
    print("=" * 60)
    
    # 测试类型转换
    test_type_conversion()
    
    print("\n" + "=" * 40)
    
    # 确认清理
    response = input("是否执行数据库清理？(y/N): ").strip().lower()
    if response not in ['y', 'yes']:
        print("❌ 操作已取消")
        return False
    
    # 执行清理
    success = True
    
    # SQL清理
    if not direct_sql_cleanup():
        success = False
    
    # Redis清理
    clear_redis_cache()
    
    if success:
        print("\n🎉 简化修复完成！")
        print("📋 下一步:")
        print("   1. 重启应用: python app.py")
        print("   2. 测试充电功能")
        print("   3. 监控日志确认无错误")
    else:
        print("\n💥 修复过程中出现错误")
    
    return success

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)