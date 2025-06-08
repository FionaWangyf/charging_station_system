#!/usr/bin/env python3
"""
充电桩管理系统 - 基础功能测试脚本
"""

import requests
import json
import time
import sys
from datetime import datetime, timedelta

class ChargingSystemTester:
    def __init__(self, base_url="http://localhost:5001"):
        self.base_url = base_url
        self.session = requests.Session()
        self.admin_session = requests.Session()
        self.test_users = []
        self.test_sessions = []
        
    def log(self, message, level="INFO"):
        """输出测试日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
    
    def assert_response(self, response, expected_status=200, test_name=""):
        """验证响应结果"""
        if response.status_code != expected_status:
            self.log(f"❌ {test_name} 失败: HTTP {response.status_code}", "ERROR")
            self.log(f"响应内容: {response.text}", "ERROR")
            return False
        
        try:
            data = response.json()
            if not data.get('success', True):
                self.log(f"❌ {test_name} 失败: {data.get('message', '未知错误')}", "ERROR")
                return False
            
            self.log(f"✅ {test_name} 成功", "SUCCESS")
            return True
        except Exception as e:
            self.log(f"❌ {test_name} 响应解析失败: {e}", "ERROR")
            return False
    
    def test_system_health(self):
        """测试系统健康状态"""
        self.log("开始测试系统健康状态...")
        
        try:
            response = self.session.get(f"{self.base_url}/health")
            if self.assert_response(response, test_name="系统健康检查"):
                data = response.json()
                self.log(f"系统状态: {data.get('status')}")
                return True
        except Exception as e:
            self.log(f"❌ 系统健康检查失败: {e}", "ERROR")
            return False
    
    def test_user_registration_and_login(self):
        """测试用户注册和登录"""
        self.log("开始测试用户注册和登录...")
        
        # 测试用户数据
        test_users_data = [
            {
                "car_id": "京A12345",
                "username": "testuser1",
                "password": "password123",
                "car_capacity": 60.0
            },
            {
                "car_id": "京B67890", 
                "username": "testuser2",
                "password": "password123",
                "car_capacity": 50.0
            },
            {
                "car_id": "京C11111",
                "username": "testuser3", 
                "password": "password123",
                "car_capacity": 70.0
            }
        ]
        
        for user_data in test_users_data:
            # 注册用户
            response = self.session.post(
                f"{self.base_url}/api/user/register",
                json=user_data
            )
            
            if not self.assert_response(response, 201, f"用户注册 - {user_data['username']}"):
                continue
            
            # 登录用户
            login_data = {
                "username": user_data["username"],
                "password": user_data["password"]
            }
            
            response = self.session.post(
                f"{self.base_url}/api/user/login",
                json=login_data
            )
            
            if self.assert_response(response, test_name=f"用户登录 - {user_data['username']}"):
                user_info = response.json().get('data', {}).get('user_info', {})
                user_data['user_id'] = user_info.get('id')
                user_data['session'] = requests.Session()
                user_data['session'].cookies.update(self.session.cookies)
                self.test_users.append(user_data)
        
        self.log(f"成功创建 {len(self.test_users)} 个测试用户")
        return len(self.test_users) > 0
    
    def test_admin_login(self):
        """测试管理员登录"""
        self.log("开始测试管理员登录...")
        
        login_data = {
            "username": "admin",
            "password": "admin123"
        }
        
        response = self.admin_session.post(
            f"{self.base_url}/api/user/login",
            json=login_data
        )
        
        return self.assert_response(response, test_name="管理员登录")
    
    def test_charging_request_submission(self):
        """测试充电请求提交"""
        self.log("开始测试充电请求提交...")
        
        if not self.test_users:
            self.log("❌ 没有可用的测试用户", "ERROR")
            return False
        
        # 测试快充请求
        fast_charge_data = {
            "charging_mode": "fast",
            "requested_amount": 25.0
        }
        
        response = self.test_users[0]['session'].post(
            f"{self.base_url}/api/charging/request",
            json=fast_charge_data
        )
        
        if self.assert_response(response, 201, "快充请求提交"):
            session_data = response.json().get('data', {})
            self.test_sessions.append({
                'user': self.test_users[0],
                'session_id': session_data.get('session_id'),
                'mode': 'fast'
            })
        
        # 测试慢充请求
        if len(self.test_users) > 1:
            trickle_charge_data = {
                "charging_mode": "trickle", 
                "requested_amount": 15.0
            }
            
            response = self.test_users[1]['session'].post(
                f"{self.base_url}/api/charging/request",
                json=trickle_charge_data
            )
            
            if self.assert_response(response, 201, "慢充请求提交"):
                session_data = response.json().get('data', {})
                self.test_sessions.append({
                    'user': self.test_users[1],
                    'session_id': session_data.get('session_id'),
                    'mode': 'trickle'
                })
        
        return len(self.test_sessions) > 0
    
    def test_system_status_monitoring(self):
        """测试系统状态监控"""
        self.log("开始测试系统状态监控...")
        
        # 测试系统整体状态
        response = self.session.get(f"{self.base_url}/api/charging/system-status")
        if not self.assert_response(response, test_name="系统状态查询"):
            return False
        
        status_data = response.json().get('data', {})
        self.log(f"等候区状态: {status_data.get('station_waiting_area', {})}")
        self.log(f"充电桩状态: {len(status_data.get('charging_piles', {}))}")
        
        # 测试用户充电状态  
        if self.test_users:
            response = self.test_users[0]['session'].get(
                f"{self.base_url}/api/charging/status"
            )
            self.assert_response(response, test_name="用户充电状态查询")
        
        return True
    
    def test_admin_functions(self):
        """测试管理员功能"""
        self.log("开始测试管理员功能...")
        
        # 测试系统概览
        response = self.admin_session.get(f"{self.base_url}/api/admin/overview")
        if not self.assert_response(response, test_name="管理员系统概览"):
            return False
        
        # 测试充电桩状态查询
        response = self.admin_session.get(f"{self.base_url}/api/admin/piles/status")
        if not self.assert_response(response, test_name="充电桩状态查询"):
            return False
        
        piles_data = response.json().get('data', {}).get('piles', [])
        self.log(f"发现 {len(piles_data)} 个充电桩")
        
        # 测试队列信息查询
        response = self.admin_session.get(f"{self.base_url}/api/admin/queue/info")
        self.assert_response(response, test_name="队列信息查询")
        
        return True
    
    def test_billing_system(self):
        """测试计费系统"""
        self.log("开始测试计费系统...")
        
        # 测试电价配置查询
        response = self.session.get(f"{self.base_url}/api/billing/rates")
        if not self.assert_response(response, test_name="电价配置查询"):
            return False
        
        rates_data = response.json().get('data', {})
        self.log(f"电价配置: {rates_data.get('rates', {})}")
        
        # 测试费用计算
        if self.test_users:
            calc_data = {
                "start_time": "2025-06-07T10:00:00",
                "end_time": "2025-06-07T11:00:00",
                "power_consumed": 25.0
            }
            
            response = self.test_users[0]['session'].post(
                f"{self.base_url}/api/billing/calculate",
                json=calc_data
            )
            
            if self.assert_response(response, test_name="费用计算"):
                billing_data = response.json().get('data', {})
                self.log(f"计算结果: 电费={billing_data.get('electricity_fee')}, "
                        f"服务费={billing_data.get('service_fee')}, "
                        f"总费用={billing_data.get('total_fee')}")
        
        return True
    
    def test_statistics_functions(self):
        """测试统计功能"""
        self.log("开始测试统计功能...")
        
        # 测试概览统计
        response = self.admin_session.get(f"{self.base_url}/api/statistics/overview")
        if not self.assert_response(response, test_name="统计概览"):
            return False
        
        # 测试日统计
        response = self.admin_session.get(f"{self.base_url}/api/statistics/daily?days=7")
        self.assert_response(response, test_name="日统计数据")
        
        # 测试充电桩使用统计
        response = self.admin_session.get(f"{self.base_url}/api/statistics/pile-usage")
        self.assert_response(response, test_name="充电桩使用统计")
        
        return True
    
    def test_edge_cases(self):
        """测试边界情况"""
        self.log("开始测试边界情况...")
        
        # 测试重复请求
        if self.test_users:
            duplicate_request_data = {
                "charging_mode": "fast",
                "requested_amount": 20.0
            }
            
            response = self.test_users[0]['session'].post(
                f"{self.base_url}/api/charging/request",
                json=duplicate_request_data
            )
            
            # 预期应该失败，因为用户已有活跃请求
            if response.status_code == 400:
                self.log("✅ 重复请求正确被拒绝", "SUCCESS")
            else:
                self.log("❌ 重复请求应该被拒绝", "ERROR")
        
        # 测试无效参数
        invalid_request_data = {
            "charging_mode": "invalid_mode",
            "requested_amount": -10.0
        }
        
        response = self.session.post(
            f"{self.base_url}/api/charging/request",
            json=invalid_request_data
        )
        
        if response.status_code >= 400:
            self.log("✅ 无效参数正确被拒绝", "SUCCESS")
        else:
            self.log("❌ 无效参数应该被拒绝", "ERROR")
        
        return True
    
    def wait_for_charging_progress(self, max_wait_time=60):
        """等待充电进度（模拟）"""
        self.log(f"等待充电进度更新... (最多等待{max_wait_time}秒)")
        
        start_time = time.time()
        while time.time() - start_time < max_wait_time:
            time.sleep(5)
            
            # 检查系统状态
            response = self.session.get(f"{self.base_url}/api/charging/system-status")
            if response.status_code == 200:
                status_data = response.json().get('data', {})
                piles = status_data.get('charging_piles', {})
                
                occupied_piles = [pid for pid, pdata in piles.items() 
                                if pdata.get('app_status') == 'occupied']
                
                if occupied_piles:
                    self.log(f"✅ 发现正在充电的充电桩: {occupied_piles}")
                    return True
                
                self.log("等待调度和充电开始...")
            
            time.sleep(5)
        
        self.log("⏰ 等待超时，但这可能是正常的（取决于调度速度）")
        return False
    
    def run_all_tests(self):
        """运行所有测试"""
        self.log("=" * 60)
        self.log("开始充电桩管理系统功能测试")
        self.log("=" * 60)
        
        test_results = {}
        
        # 测试顺序很重要
        tests = [
            ("系统健康检查", self.test_system_health),
            ("用户注册登录", self.test_user_registration_and_login),
            ("管理员登录", self.test_admin_login),
            ("充电请求提交", self.test_charging_request_submission),
            ("系统状态监控", self.test_system_status_monitoring),
            ("管理员功能", self.test_admin_functions),
            ("计费系统", self.test_billing_system),
            ("统计功能", self.test_statistics_functions),
            ("边界情况测试", self.test_edge_cases),
        ]
        
        for test_name, test_func in tests:
            self.log(f"\n{'='*20} {test_name} {'='*20}")
            try:
                result = test_func()
                test_results[test_name] = result
                if result:
                    self.log(f"✅ {test_name} - 通过")
                else:
                    self.log(f"❌ {test_name} - 失败")
            except Exception as e:
                self.log(f"❌ {test_name} - 异常: {e}", "ERROR")
                test_results[test_name] = False
            
            time.sleep(1)  # 避免请求过快
        
        # 等待充电进度（可选）
        if any(test_results.values()):
            self.log(f"\n{'='*20} 充电进度监控 {'='*20}")
            self.wait_for_charging_progress(30)
        
        # 测试结果汇总
        self.log("\n" + "=" * 60)
        self.log("测试结果汇总")
        self.log("=" * 60)
        
        passed_tests = sum(1 for result in test_results.values() if result)
        total_tests = len(test_results)
        
        for test_name, result in test_results.items():
            status = "✅ 通过" if result else "❌ 失败"
            self.log(f"{test_name}: {status}")
        
        self.log(f"\n总计: {passed_tests}/{total_tests} 个测试通过")
        self.log(f"通过率: {(passed_tests/total_tests)*100:.1f}%")
        
        if passed_tests == total_tests:
            self.log("🎉 所有测试通过！系统功能正常")
            return True
        else:
            self.log("⚠️ 部分测试失败，请检查系统状态")
            return False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='充电桩管理系统测试脚本')
    parser.add_argument('--url', default='http://localhost:5001', 
                       help='服务器地址 (默认: http://localhost:5001)')
    parser.add_argument('--wait-time', type=int, default=30,
                       help='等待充电进度的时间(秒) (默认: 30)')
    
    args = parser.parse_args()
    
    tester = ChargingSystemTester(args.url)
    
    try:
        success = tester.run_all_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"测试执行出错: {e}")
        sys.exit(1)