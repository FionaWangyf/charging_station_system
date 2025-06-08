#!/usr/bin/env python3
"""
系统问题诊断脚本
快速诊断调度系统的状态和问题
"""

import requests
import json
import time
from datetime import datetime

class SystemDiagnostic:
    def __init__(self, base_url="http://localhost:5001"):
        self.base_url = base_url
        self.admin_session = requests.Session()
        
    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
    
    def diagnose_system(self):
        """诊断系统状态"""
        self.log("🔍 开始系统诊断...")
        
        # 1. 检查服务器连接
        self.log("1️⃣ 检查服务器连接...")
        if not self.check_server_health():
            return False
        
        # 2. 检查管理员登录
        self.log("2️⃣ 检查管理员权限...")
        if not self.check_admin_access():
            return False
        
        # 3. 检查充电桩状态
        self.log("3️⃣ 检查充电桩状态...")
        pile_status = self.check_pile_status()
        
        # 4. 检查队列状态
        self.log("4️⃣ 检查队列状态...")
        queue_status = self.check_queue_status()
        
        # 5. 检查活跃会话
        self.log("5️⃣ 检查活跃充电会话...")
        session_status = self.check_active_sessions()
        
        # 6. 生成诊断报告
        self.generate_diagnosis_report(pile_status, queue_status, session_status)
        
        return True
    
    def check_server_health(self):
        """检查服务器健康状态"""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            if response.status_code == 200:
                self.log("✅ 服务器连接正常")
                return True
            else:
                self.log(f"❌ 服务器响应异常: {response.status_code}", "ERROR")
                return False
        except Exception as e:
            self.log(f"❌ 服务器连接失败: {e}", "ERROR")
            return False
    
    def check_admin_access(self):
        """检查管理员权限"""
        try:
            login_data = {"username": "admin", "password": "admin123"}
            response = self.admin_session.post(f"{self.base_url}/api/user/login", json=login_data, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success') and data.get('data', {}).get('user_info', {}).get('user_type') == 'admin':
                    self.log("✅ 管理员权限正常")
                    return True
                else:
                    self.log("❌ 管理员权限验证失败", "ERROR")
                    return False
            else:
                self.log(f"❌ 管理员登录失败: {response.status_code}", "ERROR")
                return False
        except Exception as e:
            self.log(f"❌ 管理员登录异常: {e}", "ERROR")
            return False
    
    def check_pile_status(self):
        """检查充电桩状态"""
        try:
            response = self.admin_session.get(f"{self.base_url}/api/admin/piles/status", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    piles = data.get('data', {}).get('piles', [])
                    
                    status_summary = {
                        'total': len(piles),
                        'available': 0,
                        'occupied': 0,
                        'offline': 0,
                        'fault': 0
                    }
                    
                    self.log("📊 充电桩状态详情:")
                    for pile in piles:
                        pile_id = pile.get('id')
                        db_status = pile.get('db_status')
                        app_status = pile.get('app_status')
                        current_session = pile.get('current_session')
                        
                        status_summary[app_status] = status_summary.get(app_status, 0) + 1
                        
                        session_info = ""
                        if current_session:
                            session_info = f" (会话: {current_session.get('session_id', '')[:8]}...)"
                        
                        self.log(f"   桩 {pile_id}: DB={db_status}, APP={app_status}{session_info}")
                    
                    self.log(f"📈 状态汇总: {status_summary}")
                    return status_summary
                else:
                    self.log("❌ 充电桩状态获取失败", "ERROR")
                    return None
            else:
                self.log(f"❌ 充电桩状态查询失败: {response.status_code}", "ERROR")
                return None
        except Exception as e:
            self.log(f"❌ 充电桩状态检查异常: {e}", "ERROR")
            return None
    
    def check_queue_status(self):
        """检查队列状态"""
        try:
            response = self.admin_session.get(f"{self.base_url}/api/admin/queue/info", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    queue_info = data.get('data', {})
                    summary = queue_info.get('summary', {})
                    
                    self.log("📊 队列状态详情:")
                    self.log(f"   等候区总计: {summary.get('total_waiting_station', 0)}")
                    self.log(f"   快充等候区: {summary.get('fast_waiting_station', 0)}")
                    self.log(f"   慢充等候区: {summary.get('trickle_waiting_station', 0)}")
                    self.log(f"   引擎队列总计: {summary.get('total_waiting_engine', 0)}")
                    self.log(f"   快充引擎队列: {summary.get('fast_waiting_engine', 0)}")
                    self.log(f"   慢充引擎队列: {summary.get('trickle_waiting_engine', 0)}")
                    
                    return summary
                else:
                    self.log("❌ 队列状态获取失败", "ERROR")
                    return None
            else:
                self.log(f"❌ 队列状态查询失败: {response.status_code}", "ERROR")
                return None
        except Exception as e:
            self.log(f"❌ 队列状态检查异常: {e}", "ERROR")
            return None
    
    def check_active_sessions(self):
        """检查活跃充电会话"""
        try:
            response = self.admin_session.get(f"{self.base_url}/api/admin/queue/info", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    charging_sessions = data.get('data', {}).get('charging_sessions', [])
                    
                    self.log(f"📊 活跃充电会话: {len(charging_sessions)} 个")
                    
                    for session in charging_sessions:
                        session_id = session.get('session_id', '')[:8]
                        user_id = session.get('user_id')
                        pile_id = session.get('pile_id')
                        status = session.get('status')
                        progress = session.get('progress_percentage', 0)
                        
                        self.log(f"   会话 {session_id}...: 用户{user_id} 桩{pile_id} {status} {progress:.1f}%")
                    
                    return len(charging_sessions)
                else:
                    self.log("❌ 充电会话获取失败", "ERROR")
                    return None
            else:
                self.log(f"❌ 充电会话查询失败: {response.status_code}", "ERROR")
                return None
        except Exception as e:
            self.log(f"❌ 充电会话检查异常: {e}", "ERROR")
            return None
    
    def generate_diagnosis_report(self, pile_status, queue_status, session_count):
        """生成诊断报告"""
        self.log("\n" + "=" * 60)
        self.log("🏥 系统诊断报告")
        self.log("=" * 60)
        
        # 总体健康评分
        health_score = 0
        max_score = 100
        issues = []
        recommendations = []
        
        # 1. 充电桩健康检查
        if pile_status:
            pile_health = 0
            total_piles = pile_status.get('total', 0)
            available_piles = pile_status.get('available', 0) + pile_status.get('occupied', 0)
            offline_piles = pile_status.get('offline', 0)
            fault_piles = pile_status.get('fault', 0)
            
            if total_piles > 0:
                pile_health = (available_piles / total_piles) * 40  # 最多40分
                health_score += pile_health
                
                self.log(f"📊 充电桩健康度: {pile_health:.1f}/40")
                
                if offline_piles > 0:
                    issues.append(f"有 {offline_piles} 个充电桩离线")
                    recommendations.append("重启离线充电桩")
                
                if fault_piles > 0:
                    issues.append(f"有 {fault_piles} 个充电桩故障")
                    recommendations.append("检查故障充电桩状态")
            else:
                issues.append("未检测到充电桩")
                recommendations.append("检查充电桩配置")
        else:
            issues.append("无法获取充电桩状态")
            recommendations.append("检查管理员API权限")
        
        # 2. 队列系统健康检查
        if queue_status:
            queue_health = 30  # 队列系统正常运行得30分
            health_score += queue_health
            self.log(f"📊 队列系统健康度: {queue_health}/30")
            
            total_waiting = queue_status.get('total_waiting_station', 0) + queue_status.get('total_waiting_engine', 0)
            if total_waiting > 10:
                issues.append(f"队列积压严重: {total_waiting} 个请求等待")
                recommendations.append("检查调度引擎性能")
        else:
            issues.append("队列系统状态异常")
            recommendations.append("检查Redis连接和调度引擎")
        
        # 3. 会话管理健康检查
        if session_count is not None:
            session_health = 30  # 会话管理正常得30分
            health_score += session_health
            self.log(f"📊 会话管理健康度: {session_health}/30")
            
            if session_count > 15:
                issues.append(f"活跃会话过多: {session_count} 个")
                recommendations.append("清理异常会话")
        else:
            issues.append("会话管理状态异常")
            recommendations.append("检查数据库连接")
        
        # 健康评级
        if health_score >= 90:
            health_grade = "🟢 优秀"
        elif health_score >= 70:
            health_grade = "🟡 良好"
        elif health_score >= 50:
            health_grade = "🟠 一般"
        else:
            health_grade = "🔴 较差"
        
        self.log(f"\n🏥 系统健康评分: {health_score:.1f}/{max_score} ({health_grade})")
        
        # 问题列表
        if issues:
            self.log("\n⚠️ 发现的问题:")
            for i, issue in enumerate(issues, 1):
                self.log(f"   {i}. {issue}")
        else:
            self.log("\n✅ 未发现明显问题")
        
        # 建议列表
        if recommendations:
            self.log("\n💡 改进建议:")
            for i, rec in enumerate(recommendations, 1):
                self.log(f"   {i}. {rec}")
        
        # 针对原始问题的特定建议
        self.log("\n🔧 针对测试失败的建议:")
        self.log("   1. 执行修复版测试: python fixed_scheduler_test.py")
        self.log("   2. 清理所有活跃会话后重新测试")
        self.log("   3. 检查系统是否有残留的用户会话冲突")
        self.log("   4. 确认Redis和数据库状态同步")
        
        return health_score >= 70
    
    def cleanup_system(self):
        """系统清理操作"""
        self.log("\n🧹 执行系统清理...")
        
        try:
            # 强制停止所有充电桩
            for pile_id in ['A', 'B', 'C', 'D', 'E']:
                try:
                    stop_data = {"pile_id": pile_id, "force": True}
                    response = self.admin_session.post(f"{self.base_url}/api/admin/pile/stop", json=stop_data, timeout=5)
                    if response.status_code == 200:
                        self.log(f"✅ 充电桩 {pile_id} 已停止")
                    time.sleep(0.2)
                except:
                    pass
            
            time.sleep(3)
            
            # 重新启动所有充电桩
            for pile_id in ['A', 'B', 'C', 'D', 'E']:
                try:
                    start_data = {"pile_id": pile_id}
                    response = self.admin_session.post(f"{self.base_url}/api/admin/pile/start", json=start_data, timeout=5)
                    if response.status_code == 200:
                        self.log(f"✅ 充电桩 {pile_id} 已启动")
                    time.sleep(0.2)
                except:
                    pass
            
            time.sleep(5)
            self.log("✅ 系统清理完成")
            return True
            
        except Exception as e:
            self.log(f"❌ 系统清理失败: {e}", "ERROR")
            return False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='系统问题诊断工具')
    parser.add_argument('--url', default='http://localhost:5001',
                       help='服务器地址 (默认: http://localhost:5001)')
    parser.add_argument('--cleanup', action='store_true',
                       help='执行系统清理')
    
    args = parser.parse_args()
    
    diagnostic = SystemDiagnostic(args.url)
    
    try:
        if args.cleanup:
            diagnostic.cleanup_system()
        
        success = diagnostic.diagnose_system()
        
        if not success:
            print("\n❌ 系统诊断发现严重问题，建议检查系统配置")
            exit(1)
        else:
            print("\n✅ 系统诊断完成")
            exit(0)
            
    except KeyboardInterrupt:
        print("\n诊断被用户中断")
        exit(1)
    except Exception as e:
        print(f"诊断执行出错: {e}")
        import traceback
        traceback.print_exc()
        exit(1)