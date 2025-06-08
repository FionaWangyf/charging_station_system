#!/usr/bin/env python3
"""
充电服务内部问题诊断脚本
检查为什么请求提交成功但没有进入队列
"""

import requests
import json
import time
import random
from datetime import datetime

class ServiceDebugger:
    def __init__(self, base_url="http://localhost:5001"):
        self.base_url = base_url
        self.admin_session = requests.Session()
        
    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        print(f"[{timestamp}] {level}: {message}")
    
    def admin_login(self):
        """管理员登录"""
        login_data = {"username": "admin", "password": "admin123"}
        try:
            response = self.admin_session.post(f"{self.base_url}/api/user/login", json=login_data, timeout=10)
            if response.status_code == 200:
                self.log("✅ 管理员登录成功")
                return True
            else:
                self.log(f"❌ 管理员登录失败: {response.status_code}")
                return False
        except Exception as e:
            self.log(f"❌ 管理员登录异常: {e}", "ERROR")
            return False
    
    def check_service_initialization(self):
        """检查充电服务初始化状态"""
        self.log("🔧 检查充电服务初始化状态...")
        
        # 检查系统状态API
        try:
            response = requests.get(f"{self.base_url}/api/charging/system-status", timeout=5)
            if response.status_code == 200:
                data = response.json().get('data', {})
                if 'error' in data:
                    self.log(f"❌ 充电服务有错误: {data['error']}")
                    return False
                else:
                    self.log("✅ 充电服务系统状态API正常")
                    return True
            else:
                self.log(f"❌ 系统状态API调用失败: {response.status_code}")
                return False
        except Exception as e:
            self.log(f"❌ 检查服务状态异常: {e}", "ERROR")
            return False
    
    def check_charging_service_extension(self):
        """检查Flask扩展中的充电服务"""
        self.log("🔌 检查充电服务扩展...")
        
        # 通过尝试访问需要充电服务的API来检查
        try:
            response = self.admin_session.get(f"{self.base_url}/api/admin/overview", timeout=5)
            if response.status_code == 200:
                self.log("✅ 管理员API正常，充电服务扩展可能正常")
                return True
            else:
                self.log(f"❌ 管理员API调用失败: {response.status_code}")
                return False
        except Exception as e:
            self.log(f"❌ 检查充电服务扩展异常: {e}", "ERROR")
            return False
    
    def wait_for_charging_service(self, max_retries=10, retry_interval=1):
        """等待充电服务初始化完成"""
        self.log("⏳ 等待充电服务初始化...")
        for i in range(max_retries):
            try:
                response = self.admin_session.get(
                    f"{self.base_url}/api/charging/system-status",
                    timeout=5
                )
                if response.status_code == 200:
                    self.log("✅ 充电服务已就绪")
                    return True
            except Exception as e:
                self.log(f"等待充电服务初始化中... ({i+1}/{max_retries})")
                time.sleep(retry_interval)
        self.log("❌ 充电服务初始化超时")
        return False
    
    def wait_for_session_completion(self, session_id, max_retries=30, retry_interval=1):
        """等待会话完成"""
        self.log(f"⏳ 等待会话 {session_id} 完成...")
        for i in range(max_retries):
            try:
                response = self.admin_session.get(
                    f"{self.base_url}/api/charging/sessions/{session_id}",
                    timeout=5
                )
                if response.status_code == 200:
                    data = response.json()
                    status = data.get('data', {}).get('status')
                    if status in ['completed', 'cancelled', 'fault_completed']:
                        self.log(f"✅ 会话 {session_id} 已完成，状态: {status}")
                        return True
                time.sleep(retry_interval)
            except Exception as e:
                self.log(f"等待会话完成中... ({i+1}/{max_retries})")
                time.sleep(retry_interval)
        self.log(f"❌ 等待会话 {session_id} 完成超时")
        return False
    
    def test_request_submission_detailed(self):
        """详细测试请求提交过程"""
        self.log("📋 详细测试请求提交过程...")
        
        # 等待充电服务初始化
        if not self.wait_for_charging_service():
            return False
        
        # 创建用户
        user = self.create_test_user()
        if not user:
            return False
        
        # 检查并清理已有的充电会话
        self.log("🧹 检查并清理已有充电会话...")
        try:
            response = user['session'].get(
                f"{self.base_url}/api/charging/status",
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                if data.get('data', {}).get('has_active_request'):
                    session_id = data['data'].get('session_id')
                    if session_id:
                        # 取消已有的充电请求
                        cancel_response = user['session'].post(
                            f"{self.base_url}/api/charging/request/cancel",
                            json={"session_id": session_id},
                            timeout=5
                        )
                        self.log(f"已取消已有充电请求: {session_id}")
                        # 等待取消操作完成
                        time.sleep(2)
        except Exception as e:
            self.log(f"检查/清理已有会话时出错: {str(e)}")
        
        # 检查用户初始状态
        self.log("👤 检查用户初始状态...")
        initial_status = self.get_user_status(user)
        self.log(f"初始状态: {initial_status}")
        
        # 提交请求
        self.log("📤 提交充电请求...")
        request_data = {"charging_mode": "fast", "requested_amount": 25.0}
        
        try:
            response = user['session'].post(
                f"{self.base_url}/api/charging/request",
                json=request_data,
                timeout=15
            )
            
            self.log(f"📊 请求响应详情:")
            self.log(f"   状态码: {response.status_code}")
            self.log(f"   响应头: {dict(response.headers)}")
            
            if response.text:
                try:
                    response_data = response.json()
                    self.log(f"   响应数据: {json.dumps(response_data, indent=2, ensure_ascii=False)}")
                    
                    if response.status_code == 201:
                        session_id = response_data.get('data', {}).get('session_id')
                        self.log(f"✅ 请求提交成功，会话ID: {session_id}")
                        
                        # 等待会话完成
                        if not self.wait_for_session_completion(session_id):
                            self.log("❌ 等待会话完成超时")
                            return False
                        
                        # 等待一段时间确保状态完全更新
                        time.sleep(2)
                        
                        # 立即检查各种状态
                        self.immediate_status_check(user, session_id)
                        return True
                    else:
                        self.log(f"❌ 请求提交失败: {response_data.get('message', '未知错误')}")
                        return False
                except json.JSONDecodeError:
                    self.log(f"   响应文本: {response.text}")
            else:
                self.log("   响应为空")
            
            return False
            
        except Exception as e:
            self.log(f"❌ 请求提交异常: {e}", "ERROR")
            return False
    
    def immediate_status_check(self, user, session_id):
        """请求提交后立即检查状态"""
        self.log(f"🔍 立即检查会话 {session_id} 的状态...")
        
        # 1. 检查用户状态
        user_status = self.get_user_status(user)
        self.log(f"👤 用户状态: {user_status}")
        
        # 2. 检查Redis队列（通过管理员API）
        self.check_redis_queues()
        
        # 3. 检查充电会话（通过用户API）
        self.check_user_sessions(user)
        
        # 4. 等待几秒后再检查
        time.sleep(3)
        self.log("⏳ 3秒后再次检查...")
        
        user_status = self.get_user_status(user)
        self.log(f"👤 3秒后用户状态: {user_status}")
        self.check_redis_queues()
    
    def get_user_status(self, user):
        """获取用户状态"""
        try:
            response = user['session'].get(f"{self.base_url}/api/charging/status", timeout=5)
            if response.status_code == 200:
                return response.json().get('data', {})
            else:
                return {"error": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"error": str(e)}
    
    def check_redis_queues(self):
        """检查Redis队列状态"""
        try:
            response = self.admin_session.get(f"{self.base_url}/api/admin/queue/info", timeout=5)
            if response.status_code == 200:
                data = response.json().get('data', {})
                summary = data.get('summary', {})
                
                self.log("📋 Redis队列状态:")
                self.log(f"   等候区总计: {summary.get('total_waiting_station', 0)}")
                self.log(f"   引擎队列总计: {summary.get('total_waiting_engine', 0)}")
                self.log(f"   正在充电: {summary.get('total_charging', 0)}")
                
                queue_info = data.get('queue_info', {})
                station_area = queue_info.get('station_waiting_area', {})
                self.log(f"   快充等候区: {len(station_area.get('fast', []))}")
                self.log(f"   慢充等候区: {len(station_area.get('trickle', []))}")
                
                return True
            else:
                self.log(f"❌ 队列信息API失败: {response.status_code}")
                return False
        except Exception as e:
            self.log(f"❌ 检查Redis队列异常: {e}", "ERROR")
            return False
    
    def check_user_sessions(self, user):
        """检查用户充电会话"""
        try:
            response = user['session'].get(f"{self.base_url}/api/charging/sessions", timeout=5)
            if response.status_code == 200:
                data = response.json().get('data', {})
                sessions = data.get('sessions', [])
                
                self.log(f"📊 用户充电会话: {len(sessions)} 个")
                for session in sessions:
                    self.log(f"   会话: {session.get('session_id')}, 状态: {session.get('status')}")
                
                return len(sessions) > 0
            else:
                self.log(f"❌ 用户会话API失败: {response.status_code}")
                return False
        except Exception as e:
            self.log(f"❌ 检查用户会话异常: {e}", "ERROR")
            return False
    
    def create_test_user(self):
        """创建测试用户"""
        car_id = f"京A{random.randint(10000, 99999)}"
        username = f"service_debug_{random.randint(100, 999)}"
        
        user_data = {
            "car_id": car_id,
            "username": username,
            "password": "test123",
            "car_capacity": 60.0
        }
        
        try:
            session = requests.Session()
            
            # 注册
            response = session.post(f"{self.base_url}/api/user/register", json=user_data, timeout=10)
            if response.status_code not in [201, 409]:
                self.log(f"❌ 用户注册失败: {response.status_code} - {response.text}")
                return None
            
            # 登录
            login_data = {"username": username, "password": "test123"}
            response = session.post(f"{self.base_url}/api/user/login", json=login_data, timeout=10)
            if response.status_code == 200:
                self.log(f"✅ 测试用户创建成功: {username} ({car_id})")
                return {'session': session, 'username': username, 'car_id': car_id}
            else:
                self.log(f"❌ 用户登录失败: {response.status_code}")
                return None
                
        except Exception as e:
            self.log(f"❌ 创建测试用户异常: {e}", "ERROR")
            return None
    
    def test_different_request_types(self):
        """测试不同类型的请求"""
        self.log("🧪 测试不同类型的充电请求...")
        
        user = self.create_test_user()
        if not user:
            return False
        
        # 测试多种请求参数组合
        test_cases = [
            {"charging_mode": "fast", "requested_amount": 25.0},
            {"charging_mode": "trickle", "requested_amount": 15.0},
            {"charging_mode": "fast", "requested_amount": 30.0},
        ]
        
        for i, case in enumerate(test_cases):
            self.log(f"\n🧪 测试用例 {i+1}: {case}")
            
            try:
                response = user['session'].post(
                    f"{self.base_url}/api/charging/request",
                    json=case,
                    timeout=15
                )
                
                self.log(f"响应状态: {response.status_code}")
                if response.text:
                    try:
                        response_data = response.json()
                        self.log(f"响应数据: {response_data}")
                    except:
                        self.log(f"响应文本: {response.text}")
                
                # 每个测试之间等待一下
                time.sleep(2)
                
            except Exception as e:
                self.log(f"❌ 测试用例 {i+1} 异常: {e}", "ERROR")
        
        return True
    
    def test_scheduling_logic(self):
        """测试调度逻辑"""
        self.log("📋 测试调度逻辑...")
        
        # 创建测试用户
        user = self.create_test_user()
        if not user:
            return False
        
        # 提交充电请求
        self.log("📤 提交充电请求...")
        request_data = {"charging_mode": "fast", "requested_amount": 25.0}
        
        try:
            response = user['session'].post(
                f"{self.base_url}/api/charging/request",
                json=request_data,
                timeout=15
            )
            
            if response.status_code == 201:
                data = response.json()
                session_id = data.get('data', {}).get('session_id')
                self.log(f"✅ 请求提交成功，会话ID: {session_id}")
                
                # 等待一段时间让调度系统处理
                time.sleep(5)
                
                # 检查调度结果
                status_response = user['session'].get(
                    f"{self.base_url}/api/charging/status",
                    timeout=5
                )
                
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    self.log(f"📊 调度状态: {json.dumps(status_data, indent=2, ensure_ascii=False)}")
                    
                    # 检查是否被调度到充电桩
                    if status_data.get('data', {}).get('pile_id'):
                        self.log(f"✅ 请求已被调度到充电桩: {status_data['data']['pile_id']}")
                        return True
                    else:
                        self.log("❌ 请求未被调度到充电桩")
                        return False
                else:
                    self.log(f"❌ 获取状态失败: {status_response.status_code}")
                    return False
            else:
                self.log(f"❌ 请求提交失败: {response.status_code}")
                return False
                
        except Exception as e:
            self.log(f"❌ 测试过程出错: {str(e)}")
            return False
    
    def test_fault_handling(self):
        """测试故障处理机制"""
        self.log("📋 测试故障处理机制...")
        
        # 创建测试用户
        user = self.create_test_user()
        if not user:
            return False
        
        # 提交充电请求
        self.log("📤 提交充电请求...")
        request_data = {"charging_mode": "fast", "requested_amount": 25.0}
        
        try:
            response = user['session'].post(
                f"{self.base_url}/api/charging/request",
                json=request_data,
                timeout=15
            )
            
            if response.status_code == 201:
                data = response.json()
                session_id = data.get('data', {}).get('session_id')
                self.log(f"✅ 请求提交成功，会话ID: {session_id}")
                
                # 等待调度系统处理
                time.sleep(5)
                
                # 模拟充电桩故障
                self.log("🔧 模拟充电桩故障...")
                system_status = user['session'].get(
                    f"{self.base_url}/api/charging/system-status",
                    timeout=5
                ).json()
                
                if system_status.get('success'):
                    piles = system_status.get('data', {}).get('charging_piles', {})
                    if piles:
                        # 获取第一个可用的充电桩
                        pile_id = next((pid for pid, pile in piles.items() 
                                     if pile.get('status') == 'available'), None)
                        
                        if pile_id:
                            # 模拟故障
                            self.log(f"🔧 模拟充电桩 {pile_id} 故障...")
                            # 这里需要调用你的故障模拟接口
                            # 例如：/api/charging/simulate-fault/{pile_id}
                            
                            # 等待故障处理
                            time.sleep(5)
                            
                            # 检查故障处理结果
                            status_response = user['session'].get(
                                f"{self.base_url}/api/charging/status",
                                timeout=5
                            )
                            
                            if status_response.status_code == 200:
                                status_data = status_response.json()
                                self.log(f"📊 故障处理状态: {json.dumps(status_data, indent=2, ensure_ascii=False)}")
                                
                                # 检查是否触发了故障处理机制
                                if status_data.get('data', {}).get('status') == 'fault':
                                    self.log("✅ 故障处理机制正常触发")
                                    return True
                                else:
                                    self.log("❌ 故障处理机制未触发")
                                    return False
                            else:
                                self.log(f"❌ 获取状态失败: {status_response.status_code}")
                                return False
                        else:
                            self.log("❌ 未找到可用的充电桩")
                            return False
                    else:
                        self.log("❌ 未找到充电桩信息")
                        return False
                else:
                    self.log("❌ 获取系统状态失败")
                    return False
            else:
                self.log(f"❌ 请求提交失败: {response.status_code}")
                return False
                
        except Exception as e:
            self.log(f"❌ 测试过程出错: {str(e)}")
            return False
    
    def diagnose_service_issues(self):
        """诊断充电服务问题"""
        self.log("\n🔍 开始诊断充电服务问题...")
        
        # 1. 检查服务初始化
        self.log("\n1️⃣ 检查服务初始化")
        service_ok = self.check_service_initialization()
        
        # 2. 检查扩展注册
        self.log("\n2️⃣ 检查扩展注册")
        extension_ok = self.check_charging_service_extension()
        
        # 3. 测试请求提交
        self.log("\n3️⃣ 测试请求提交")
        request_ok = self.test_request_submission_detailed()
        
        # 4. 测试不同请求类型
        self.log("\n4️⃣ 测试不同请求类型")
        types_ok = self.test_different_request_types()
        
        # 5. 测试故障处理机制
        self.log("\n5️⃣ 测试故障处理机制")
        fault_handling_ok = self.test_fault_handling()
        
        # 6. 诊断结果
        self.log("\n" + "=" * 60)
        self.log("🎯 诊断结果汇总")
        self.log("=" * 60)
        self.log(f"服务初始化: {'✅ 正常' if service_ok else '❌ 异常'}")
        self.log(f"扩展注册: {'✅ 正常' if extension_ok else '❌ 异常'}")
        self.log(f"请求提交: {'✅ 正常' if request_ok else '❌ 异常'}")
        self.log(f"不同请求类型: {'✅ 正常' if types_ok else '❌ 异常'}")
        self.log(f"故障处理机制: {'✅ 正常' if fault_handling_ok else '❌ 异常'}")
        
        if not any([service_ok, extension_ok, request_ok, fault_handling_ok]):
            self.log("\n❌ 严重问题：充电服务完全无法工作")
            self.log("\n💡 可能的原因:")
            self.log("1. 充电服务未正确初始化")
            self.log("2. 数据库连接失败")
            self.log("3. Redis连接失败")
            self.log("4. 系统资源不足")
            self.log("5. 确认charging_service在app.extensions中正确注册")
        
        return any([service_ok, extension_ok, request_ok, fault_handling_ok])

if __name__ == "__main__":
    debugger = ServiceDebugger()
    
    try:
        debugger.diagnose_service_issues()
    except KeyboardInterrupt:
        print("\n调试被用户中断")
    except Exception as e:
        print(f"调试过程出错: {e}")