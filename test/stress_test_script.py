#!/usr/bin/env python3
"""
充电桩管理系统 - 压力测试脚本
模拟多用户并发使用场景
"""

import asyncio
import aiohttp
import json
import time
import random
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import threading

class StressTester:
    def __init__(self, base_url="http://localhost:5001", max_users=20):
        self.base_url = base_url
        self.max_users = max_users
        self.results = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'response_times': [],
            'errors': []
        }
        self.lock = threading.Lock()
        
    def log(self, message, level="INFO"):
        """线程安全的日志输出"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        with self.lock:
            print(f"[{timestamp}] {level}: {message}")
    
    def record_result(self, success, response_time, error=None):
        """记录测试结果"""
        with self.lock:
            self.results['total_requests'] += 1
            if success:
                self.results['successful_requests'] += 1
            else:
                self.results['failed_requests'] += 1
                if error:
                    self.results['errors'].append(error)
            self.results['response_times'].append(response_time)
    
    async def create_user_session(self, session, user_id):
        """创建用户会话"""
        user_data = {
            "car_id": f"测试{user_id:04d}",
            "username": f"stressuser{user_id}",
            "password": "test123",
            "car_capacity": random.uniform(40.0, 80.0)
        }
        
        try:
            # 注册用户
            start_time = time.time()
            async with session.post(
                f"{self.base_url}/api/user/register",
                json=user_data,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                register_time = time.time() - start_time
                
                if response.status in [201, 409]:  # 201=成功, 409=已存在
                    self.record_result(True, register_time)
                else:
                    self.record_result(False, register_time, f"注册失败: {response.status}")
                    return None
            
            # 登录用户
            login_data = {
                "username": user_data["username"],
                "password": user_data["password"]
            }
            
            start_time = time.time()
            async with session.post(
                f"{self.base_url}/api/user/login",
                json=login_data,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                login_time = time.time() - start_time
                
                if response.status == 200:
                    self.record_result(True, login_time)
                    return user_data
                else:
                    self.record_result(False, login_time, f"登录失败: {response.status}")
                    return None
                    
        except Exception as e:
            self.record_result(False, 5.0, f"创建用户会话异常: {str(e)}")
            return None
    
    async def submit_charging_request(self, session, user_data):
        """提交充电请求"""
        charging_modes = ["fast", "trickle"]
        charging_mode = random.choice(charging_modes)
        requested_amount = random.uniform(10.0, 50.0)
        
        request_data = {
            "charging_mode": charging_mode,
            "requested_amount": round(requested_amount, 1)
        }
        
        try:
            start_time = time.time()
            async with session.post(
                f"{self.base_url}/api/charging/request",
                json=request_data,
                timeout=aiohttp.ClientTimeout(total=15)
            ) as response:
                response_time = time.time() - start_time
                
                if response.status == 201:
                    data = await response.json()
                    session_id = data.get('data', {}).get('session_id')
                    self.record_result(True, response_time)
                    self.log(f"用户 {user_data['username']} 成功提交 {charging_mode} 请求: {session_id}")
                    return session_id
                else:
                    error_text = await response.text()
                    self.record_result(False, response_time, f"充电请求失败: {response.status} - {error_text}")
                    return None
                    
        except Exception as e:
            self.record_result(False, 10.0, f"提交充电请求异常: {str(e)}")
            return None
    
    async def monitor_charging_status(self, session, user_data, session_id, monitor_duration=30):
        """监控充电状态"""
        monitor_start = time.time()
        
        while time.time() - monitor_start < monitor_duration:
            try:
                start_time = time.time()
                async with session.get(
                    f"{self.base_url}/api/charging/status",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    response_time = time.time() - start_time
                    
                    if response.status == 200:
                        self.record_result(True, response_time)
                        data = await response.json()
                        status_info = data.get('data', {})
                        
                        if status_info.get('status') == 'charging':
                            self.log(f"用户 {user_data['username']} 正在充电")
                        elif status_info.get('status') == 'completed':
                            self.log(f"用户 {user_data['username']} 充电完成")
                            break
                    else:
                        self.record_result(False, response_time, f"状态查询失败: {response.status}")
                        
            except Exception as e:
                self.record_result(False, 3.0, f"状态监控异常: {str(e)}")
            
            await asyncio.sleep(random.uniform(2, 5))
    
    async def simulate_user_behavior(self, session, user_id):
        """模拟单个用户的完整行为"""
        try:
            # 创建用户会话
            user_data = await self.create_user_session(session, user_id)
            if not user_data:
                return
            
            # 随机等待，模拟用户到达时间分散
            await asyncio.sleep(random.uniform(0, 10))
            
            # 提交充电请求
            session_id = await self.submit_charging_request(session, user_data)
            if not session_id:
                return
            
            # 监控充电状态
            await self.monitor_charging_status(session, user_data, session_id, 60)
            
            # 随机执行其他操作
            await self.random_operations(session, user_data)
            
        except Exception as e:
            self.log(f"用户 {user_id} 行为模拟异常: {str(e)}", "ERROR")
    
    async def random_operations(self, session, user_data):
        """随机执行其他操作"""
        operations = [
            self.check_system_status,
            self.query_charging_records,
            self.estimate_charging_time
        ]
        
        # 随机选择1-3个操作执行
        selected_ops = random.sample(operations, random.randint(1, min(3, len(operations))))
        
        for operation in selected_ops:
            try:
                await operation(session, user_data)
                await asyncio.sleep(random.uniform(1, 3))
            except Exception as e:
                self.log(f"随机操作异常: {str(e)}", "ERROR")
    
    async def check_system_status(self, session, user_data):
        """查询系统状态"""
        try:
            start_time = time.time()
            async with session.get(
                f"{self.base_url}/api/charging/system-status",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                response_time = time.time() - start_time
                
                if response.status == 200:
                    self.record_result(True, response_time)
                else:
                    self.record_result(False, response_time, f"系统状态查询失败: {response.status}")
                    
        except Exception as e:
            self.record_result(False, 3.0, f"系统状态查询异常: {str(e)}")
    
    async def query_charging_records(self, session, user_data):
        """查询充电记录"""
        try:
            start_time = time.time()
            async with session.get(
                f"{self.base_url}/api/user/charging-records?page=1&per_page=5",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                response_time = time.time() - start_time
                
                if response.status == 200:
                    self.record_result(True, response_time)
                else:
                    self.record_result(False, response_time, f"充电记录查询失败: {response.status}")
                    
        except Exception as e:
            self.record_result(False, 3.0, f"充电记录查询异常: {str(e)}")
    
    async def estimate_charging_time(self, session, user_data):
        """估算充电时间"""
        try:
            charging_mode = random.choice(["fast", "trickle"])
            amount = random.uniform(20, 40)
            
            start_time = time.time()
            async with session.get(
                f"{self.base_url}/api/charging/estimate-time?charging_mode={charging_mode}&requested_amount={amount}",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                response_time = time.time() - start_time
                
                if response.status == 200:
                    self.record_result(True, response_time)
                else:
                    self.record_result(False, response_time, f"时间估算失败: {response.status}")
                    
        except Exception as e:
            self.record_result(False, 3.0, f"时间估算异常: {str(e)}")
    
    async def run_stress_test(self, duration_minutes=5):
        """运行压力测试"""
        self.log(f"开始压力测试: {self.max_users} 个并发用户, 持续 {duration_minutes} 分钟")
        
        # 创建连接器，允许更多并发连接
        connector = aiohttp.TCPConnector(
            limit=100,
            limit_per_host=50,
            keepalive_timeout=30
        )
        
        async with aiohttp.ClientSession(
            connector=connector,
            cookie_jar=aiohttp.CookieJar()
        ) as session:
            
            start_time = time.time()
            end_time = start_time + (duration_minutes * 60)
            
            tasks = []
            user_id = 0
            
            while time.time() < end_time:
                # 控制并发用户数
                if len(tasks) < self.max_users:
                    user_id += 1
                    task = asyncio.create_task(
                        self.simulate_user_behavior(session, user_id)
                    )
                    tasks.append(task)
                
                # 清理完成的任务
                tasks = [task for task in tasks if not task.done()]
                
                # 避免CPU过载
                await asyncio.sleep(0.5)
            
            # 等待所有任务完成
            self.log("等待所有用户任务完成...")
            await asyncio.gather(*tasks, return_exceptions=True)
        
        self.log("压力测试完成")
    
    def print_results(self):
        """打印测试结果"""
        print("\n" + "=" * 60)
        print("压力测试结果统计")
        print("=" * 60)
        
        total = self.results['total_requests']
        successful = self.results['successful_requests']
        failed = self.results['failed_requests']
        
        print(f"总请求数: {total}")
        print(f"成功请求: {successful}")
        print(f"失败请求: {failed}")
        print(f"成功率: {(successful/total)*100:.1f}%" if total > 0 else "成功率: 0%")
        
        if self.results['response_times']:
            response_times = self.results['response_times']
            avg_time = sum(response_times) / len(response_times)
            max_time = max(response_times)
            min_time = min(response_times)
            
            print(f"\n响应时间统计:")
            print(f"平均响应时间: {avg_time:.3f}s")
            print(f"最大响应时间: {max_time:.3f}s")
            print(f"最小响应时间: {min_time:.3f}s")
            
            # 计算百分位数
            sorted_times = sorted(response_times)
            p95_index = int(0.95 * len(sorted_times))
            p99_index = int(0.99 * len(sorted_times))
            
            print(f"95%分位数: {sorted_times[p95_index]:.3f}s")
            print(f"99%分位数: {sorted_times[p99_index]:.3f}s")
        
        if self.results['errors']:
            print(f"\n错误统计 (前10个):")
            error_counts = {}
            for error in self.results['errors'][:10]:
                error_counts[error] = error_counts.get(error, 0) + 1
            
            for error, count in error_counts.items():
                print(f"  {error}: {count}次")
        
        print("\n" + "=" * 60)

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='充电桩管理系统压力测试')
    parser.add_argument('--url', default='http://localhost:5001',
                       help='服务器地址 (默认: http://localhost:5001)')
    parser.add_argument('--users', type=int, default=20,
                       help='并发用户数 (默认: 20)')
    parser.add_argument('--duration', type=int, default=5,
                       help='测试持续时间(分钟) (默认: 5)')
    
    args = parser.parse_args()
    
    print(f"压力测试配置:")
    print(f"  服务器地址: {args.url}")
    print(f"  并发用户数: {args.users}")
    print(f"  测试时长: {args.duration} 分钟")
    print()
    
    tester = StressTester(args.url, args.users)
    
    try:
        # 检查服务器是否可用
        import requests
        response = requests.get(f"{args.url}/health", timeout=5)
        if response.status_code != 200:
            print(f"❌ 服务器不可用: {response.status_code}")
            sys.exit(1)
        
        print("✅ 服务器连接正常，开始压力测试...")
        
        # 运行异步测试
        asyncio.run(tester.run_stress_test(args.duration))
        
        # 打印结果
        tester.print_results()
        
    except KeyboardInterrupt:
        print("\n测试被用户中断")
        tester.print_results()
    except Exception as e:
        print(f"测试执行出错: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()