#!/usr/bin/env python3
"""
充电桩调度功能测试脚本
专门测试调度策略、排队机制、故障处理等核心功能
"""

import requests
import json
import time
import random
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

class SchedulerTester:
    def __init__(self, base_url="http://localhost:5001"):
        self.base_url = base_url
        self.admin_session = requests.Session()
        self.test_users = []
        self.test_sessions = []
        self.lock = threading.Lock()
        
        # 城市车牌前缀
        self.city_prefixes = ["京A", "京B", "京C", "沪A", "沪B", "粤A", "粤B", "川A", "浙A", "苏A"]
        self.used_car_ids = set()
        self.used_usernames = set()
        
    def log(self, message, level="INFO"):
        """线程安全的日志输出"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        with self.lock:
            print(f"[{timestamp}] {level}: {message}")
    
    def generate_unique_car_id(self):
        """生成唯一的车牌号"""
        while True:
            prefix = random.choice(self.city_prefixes)
            # 生成5位数字，确保格式正确
            number = f"{random.randint(10000, 99999)}"
            car_id = f"{prefix}{number}"
            
            if car_id not in self.used_car_ids:
                self.used_car_ids.add(car_id)
                return car_id
    
    def generate_unique_username(self):
        """生成唯一的用户名"""
        while True:
            # 缩短前缀以符合20位限制
            username = f"test_{random.randint(100, 999)}_{int(time.time()) % 1000}"
            if username not in self.used_usernames:
                self.used_usernames.add(username)
                return username
    
    def admin_login(self):
        """管理员登录"""
        self.log("管理员登录中...")
        login_data = {"username": "admin", "password": "admin123"}
        
        try:
            response = self.admin_session.post(
                f"{self.base_url}/api/user/login", 
                json=login_data, 
                timeout=10
            )
            
            if response.status_code == 200:
                self.log("✅ 管理员登录成功")
                return True
            else:
                self.log(f"❌ 管理员登录失败: {response.status_code} - {response.text}", "ERROR")
                return False
        except Exception as e:
            self.log(f"❌ 管理员登录异常: {e}", "ERROR")
            return False
    
    def cleanup_system(self):
        """清理系统状态"""
        self.log("🧹 正在清理系统状态...")
        
        try:
            # 强制停止所有充电桩
            for pile_id in ['A', 'B', 'C', 'D', 'E']:
                stop_data = {"pile_id": pile_id, "force": True}
                try:
                    response = self.admin_session.post(
                        f"{self.base_url}/api/admin/pile/stop", 
                        json=stop_data, 
                        timeout=5
                    )
                    if response.status_code == 200:
                        self.log(f"停止充电桩 {pile_id}")
                except:
                    pass
                time.sleep(0.2)
            
            time.sleep(3)
            
            # 重新启动所有充电桩
            for pile_id in ['A', 'B', 'C', 'D', 'E']:
                start_data = {"pile_id": pile_id}
                try:
                    response = self.admin_session.post(
                        f"{self.base_url}/api/admin/pile/start", 
                        json=start_data, 
                        timeout=5
                    )
                    if response.status_code == 200:
                        self.log(f"启动充电桩 {pile_id}")
                except:
                    pass
                time.sleep(0.2)
            
            time.sleep(5)  # 等待状态同步
            self.log("✅ 系统状态清理完成")
            return True
            
        except Exception as e:
            self.log(f"❌ 系统清理失败: {e}", "ERROR")
            return False
    
    def create_test_user(self, user_index):
        """创建测试用户"""
        car_id = self.generate_unique_car_id()
        username = self.generate_unique_username()
        
        user_data = {
            "car_id": car_id,
            "username": username,
            "password": "test123",
            "car_capacity": random.uniform(50.0, 80.0)
        }
        
        try:
            session = requests.Session()
            session.timeout = 10
            
            # 注册用户
            response = session.post(
                f"{self.base_url}/api/user/register", 
                json=user_data, 
                timeout=10
            )
            
            if response.status_code not in [201, 409]:  # 201=成功, 409=已存在
                self.log(f"❌ 用户注册失败: {response.status_code} - {response.text}", "ERROR")
                return None
            
            # 登录用户
            login_data = {"username": username, "password": "test123"}
            response = session.post(
                f"{self.base_url}/api/user/login", 
                json=login_data, 
                timeout=10
            )
            
            if response.status_code == 200:
                user_data['session'] = session
                user_data['user_id'] = response.json().get('data', {}).get('user_info', {}).get('id')
                self.log(f"✅ 用户 {username} (车牌: {car_id}) 创建成功")
                return user_data
            else:
                self.log(f"❌ 用户登录失败: {response.status_code}", "ERROR")
                return None
                
        except Exception as e:
            self.log(f"❌ 创建用户异常: {e}", "ERROR")
            return None
    
    def submit_charging_request(self, user, charging_mode, requested_amount):
        """提交充电请求"""
        request_data = {
            "charging_mode": charging_mode,
            "requested_amount": requested_amount
        }
        
        try:
            response = user['session'].post(
                f"{self.base_url}/api/charging/request",
                json=request_data,
                timeout=15
            )
            
            if response.status_code == 201:
                data = response.json().get('data', {})
                session_id = data.get('session_id')
                self.log(f"✅ {user['username']} 提交 {charging_mode} 请求成功: {session_id}")
                return session_id
            else:
                error_msg = response.json().get('message', response.text) if response.text else '无响应内容'
                self.log(f"❌ {user['username']} 充电请求失败: {response.status_code} - {error_msg}", "ERROR")
                return None
                
        except Exception as e:
            self.log(f"❌ {user['username']} 提交请求异常: {e}", "ERROR")
            return None
    
    def get_system_status(self):
        """获取系统状态"""
        try:
            response = self.admin_session.get(
                f"{self.base_url}/api/admin/piles/status", 
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json().get('data', {})
            else:
                self.log(f"❌ 获取系统状态失败: {response.status_code}", "ERROR")
                return {}
        except Exception as e:
            self.log(f"❌ 获取系统状态异常: {e}", "ERROR")
            return {}
    
    def get_queue_info(self):
        """获取队列信息"""
        try:
            response = self.admin_session.get(
                f"{self.base_url}/api/admin/queue/info",
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json().get('data', {})
            else:
                return {}
        except Exception as e:
            return {}
    
    def wait_for_dispatch(self, max_wait_time=90):
        """等待调度完成"""
        self.log(f"⏳ 等待调度完成... (最多等待{max_wait_time}秒)")
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            queue_info = self.get_queue_info()
            summary = queue_info.get('summary', {})
            
            station_waiting = summary.get('total_waiting_station', 0)
            engine_waiting = summary.get('total_waiting_engine', 0)
            charging_count = len(queue_info.get('charging_sessions', []))
            
            self.log(f"当前状态: 等候区={station_waiting}, 引擎队列={engine_waiting}, 充电中={charging_count}")
            
            # 增加详细的队列信息
            if queue_info.get('station_waiting_area'):
                fast_station = len(queue_info['station_waiting_area'].get('fast', []))
                trickle_station = len(queue_info['station_waiting_area'].get('trickle', []))
                self.log(f"等候区详情: 快充={fast_station}, 慢充={trickle_station}")
            
            if queue_info.get('engine_dispatch_queues'):
                fast_engine = len(queue_info['engine_dispatch_queues'].get('fast', []))
                trickle_engine = len(queue_info['engine_dispatch_queues'].get('trickle', []))
                self.log(f"引擎队列详情: 快充={fast_engine}, 慢充={trickle_engine}")
            
            # 检查充电桩状态
            system_status = self.get_system_status()
            if system_status.get('piles'):
                occupied_piles = []
                for pile in system_status['piles']:
                    if pile.get('current_session'):
                        occupied_piles.append(f"{pile['id']}({pile['type']})")
                if occupied_piles:
                    self.log(f"已占用充电桩: {', '.join(occupied_piles)}")
            
            if station_waiting == 0 and engine_waiting == 0:
                self.log("✅ 所有请求已完成调度")
                return True
            
            time.sleep(4)
        
        self.log("⏰ 调度等待超时", "WARNING")
        return False
    
    def test_basic_scheduling_strategy(self):
        """测试基础调度策略：最短完成时间"""
        self.log("=" * 60)
        self.log("🎯 测试1: 基础调度策略 - 最短完成时间算法")
        self.log("=" * 60)
        
        # 创建测试用户
        users = []
        for i in range(4):
            user = self.create_test_user(i)  # 传递数字索引
            if user:
                users.append(user)
            time.sleep(0.5)
        
        if len(users) < 4:
            self.log(f"❌ 测试用户创建不足: {len(users)}/4", "ERROR")
            return False
        
        # 测试用例：模拟不同充电时长需求
        test_cases = [
            {"user_idx": 0, "mode": "fast", "amount": 15.0, "expected_time": 0.5},  # 30kW，0.5小时
            {"user_idx": 1, "mode": "fast", "amount": 30.0, "expected_time": 1.0},  # 30kW，1.0小时
            {"user_idx": 2, "mode": "trickle", "amount": 7.0, "expected_time": 1.0},   # 7kW，1.0小时
            {"user_idx": 3, "mode": "trickle", "amount": 14.0, "expected_time": 2.0},  # 7kW，2.0小时
        ]
        
        # 按顺序提交请求
        submitted_requests = []
        for i, case in enumerate(test_cases):
            user = users[case["user_idx"]]
            self.log(f"📋 提交请求 {i+1}: {user['username']} 请求 {case['mode']} {case['amount']}kWh (预计{case['expected_time']}小时)")
            
            session_id = self.submit_charging_request(user, case["mode"], case["amount"])
            if session_id:
                submitted_requests.append({
                    "session_id": session_id,
                    "user": user,
                    "mode": case["mode"],
                    "amount": case["amount"],
                    "expected_time": case["expected_time"]
                })
            
            time.sleep(2)  # 避免请求过快
        
        if not submitted_requests:
            self.log("❌ 没有成功提交的请求", "ERROR")
            return False
        
        # 等待调度
        self.wait_for_dispatch(60)
        
        # 分析调度结果
        return self.analyze_scheduling_results(submitted_requests)
    
    def analyze_scheduling_results(self, submitted_requests):
        """分析调度结果"""
        self.log("📊 分析调度结果...")
        
        # 获取详细的系统状态
        system_status = self.get_system_status()
        piles = system_status.get('piles', [])
        
        # 打印所有充电桩状态用于调试
        self.log("🔍 所有充电桩状态:")
        for pile in piles:
            pile_id = pile.get('id')
            pile_type = pile.get('type')
            db_status = pile.get('db_status')
            app_status = pile.get('app_status', 'unknown')
            current_session = pile.get('current_session')
            
            if current_session:
                self.log(f"  桩 {pile_id}({pile_type}): {db_status}/{app_status} - 会话 {current_session.get('session_id')}")
            else:
                self.log(f"  桩 {pile_id}({pile_type}): {db_status}/{app_status} - 空闲")
        
        # 统计调度情况
        fast_piles = ['A', 'B']
        trickle_piles = ['C', 'D', 'E']
        
        fast_occupied = []
        trickle_occupied = []
        
        for pile in piles:
            pile_id = pile.get('id')
            current_session = pile.get('current_session')
            
            if current_session and pile_id in fast_piles:
                fast_occupied.append({
                    'pile_id': pile_id,
                    'session_id': current_session.get('session_id'),
                    'requested_amount': current_session.get('requested_amount'),
                    'status': current_session.get('status')
                })
            elif current_session and pile_id in trickle_piles:
                trickle_occupied.append({
                    'pile_id': pile_id,
                    'session_id': current_session.get('session_id'),
                    'requested_amount': current_session.get('requested_amount'),
                    'status': current_session.get('status')
                })
        
        self.log(f"快充桩占用情况: {len(fast_occupied)} 个")
        for occupied in fast_occupied:
            self.log(f"  桩 {occupied['pile_id']}: 会话 {occupied['session_id']} ({occupied['requested_amount']}kWh) - {occupied.get('status', 'unknown')}")
        
        self.log(f"慢充桩占用情况: {len(trickle_occupied)} 个")
        for occupied in trickle_occupied:
            self.log(f"  桩 {occupied['pile_id']}: 会话 {occupied['session_id']} ({occupied['requested_amount']}kWh) - {occupied.get('status', 'unknown')}")
        
        # 检查提交的请求与分配结果的匹配
        fast_requests = [req for req in submitted_requests if req['mode'] == 'fast']
        trickle_requests = [req for req in submitted_requests if req['mode'] == 'trickle']
        
        self.log(f"📋 请求提交情况: 快充请求={len(fast_requests)}, 慢充请求={len(trickle_requests)}")
        
        # 验证调度策略
        success = True
        
        # 检查快充请求分配
        if len(fast_requests) > 0:
            if len(fast_occupied) > 0:
                self.log(f"✅ 快充调度正常：{len(fast_occupied)}/{len(fast_requests)} 个快充请求被分配")
                
                # 验证最短完成时间策略
                if len(fast_occupied) >= 2:
                    # 比较分配的请求电量，较小的应该先分配
                    amounts = [float(occ['requested_amount']) for occ in fast_occupied]
                    if amounts[0] <= amounts[1]:
                        self.log("✅ 快充调度策略正确：较小电量请求优先分配")
                    else:
                        self.log("⚠️ 快充调度策略可能有问题：分配顺序与预期不符")
                        
            else:
                self.log("❌ 快充调度异常：没有快充请求被分配")
                success = False
        
        # 检查慢充请求分配
        if len(trickle_requests) > 0:
            if len(trickle_occupied) > 0:
                self.log(f"✅ 慢充调度正常：{len(trickle_occupied)}/{len(trickle_requests)} 个慢充请求被分配")
            else:
                self.log("❌ 慢充调度异常：没有慢充请求被分配")
                success = False
        
        # 检查是否有请求仍在队列中
        queue_info = self.get_queue_info()
        if queue_info:
            summary = queue_info.get('summary', {})
            total_waiting = summary.get('total_waiting_station', 0) + summary.get('total_waiting_engine', 0)
            if total_waiting > 0:
                self.log(f"⚠️ 仍有 {total_waiting} 个请求在队列中等待")
        
        return success
    
    def test_concurrent_requests(self):
        """测试并发请求处理"""
        self.log("=" * 60)
        self.log("🎯 测试2: 并发请求处理")
        self.log("=" * 60)
        
        # 创建多个用户进行并发测试
        users = []
        for i in range(6):
            user = self.create_test_user(i)  # 传递索引而不是字符串
            if user:
                users.append(user)
            time.sleep(0.3)
        
        if len(users) < 6:
            self.log(f"❌ 并发测试用户创建不足: {len(users)}/6", "ERROR")
            return False
        
        # 定义并发请求
        concurrent_requests = [
            {"mode": "fast", "amount": 20.0},
            {"mode": "fast", "amount": 25.0},
            {"mode": "fast", "amount": 30.0},  # 第3个快充请求应该排队
            {"mode": "trickle", "amount": 10.0},
            {"mode": "trickle", "amount": 15.0},
            {"mode": "trickle", "amount": 20.0},
        ]
        
        # 使用线程池并发提交请求
        successful_requests = 0
        
        def submit_request(user_request_pair):
            user, request_data = user_request_pair
            session_id = self.submit_charging_request(user, request_data["mode"], request_data["amount"])
            return session_id is not None
        
        with ThreadPoolExecutor(max_workers=6) as executor:
            self.log("🚀 并发提交请求...")
            futures = [
                executor.submit(submit_request, (users[i], concurrent_requests[i]))
                for i in range(len(users))
            ]
            
            for future in as_completed(futures):
                if future.result():
                    successful_requests += 1
        
        self.log(f"📊 并发请求结果: {successful_requests}/{len(users)} 个请求成功")
        
        # 等待调度
        self.wait_for_dispatch(90)
        
        # 验证等候区和队列状态
        queue_info = self.get_queue_info()
        summary = queue_info.get('summary', {})
        
        total_waiting = summary.get('total_waiting_station', 0) + summary.get('total_waiting_engine', 0)
        total_charging = summary.get('total_charging', 0)
        
        self.log(f"📊 队列状态: 等待中={total_waiting}, 充电中={total_charging}")
        
        # 验证等候区容量限制（需求中提到最大6个车位）
        station_waiting = summary.get('total_waiting_station', 0)
        if station_waiting <= 6:
            self.log("✅ 等候区容量控制正常")
        else:
            self.log(f"❌ 等候区超出容量限制: {station_waiting}/6")
        
        return successful_requests >= 4  # 至少有4个请求成功
    
    def test_queue_number_generation(self):
        """测试排队号码生成规则"""
        self.log("=" * 60)
        self.log("🎯 测试3: 排队号码生成规则")
        self.log("=" * 60)
        
        # 创建用户测试排队号
        users = []
        for i in range(4):
            user = self.create_test_user(i)  # 传递索引
            if user:
                users.append(user)
        
        if len(users) < 4:
            return False
        
        # 提交请求并验证排队号格式
        fast_queue_numbers = []
        trickle_queue_numbers = []
        
        # 提交快充请求
        for i in range(2):
            session_id = self.submit_charging_request(users[i], "fast", 25.0)
            if session_id:
                # 查询用户状态获取排队号
                response = users[i]['session'].get(f"{self.base_url}/api/charging/status")
                if response.status_code == 200:
                    data = response.json().get('data', {})
                    queue_number = data.get('queue_number', '')
                    if queue_number:
                        fast_queue_numbers.append(queue_number)
                        self.log(f"快充排队号: {queue_number}")
            
            time.sleep(1)
        
        # 提交慢充请求
        for i in range(2, 4):
            session_id = self.submit_charging_request(users[i], "trickle", 15.0)
            if session_id:
                # 查询用户状态获取排队号
                response = users[i]['session'].get(f"{self.base_url}/api/charging/status")
                if response.status_code == 200:
                    data = response.json().get('data', {})
                    queue_number = data.get('queue_number', '')
                    if queue_number:
                        trickle_queue_numbers.append(queue_number)
                        self.log(f"慢充排队号: {queue_number}")
            
            time.sleep(1)
        
        # 验证排队号格式
        success = True
        
        # 验证快充排队号（应该以F开头）
        for queue_no in fast_queue_numbers:
            if not queue_no.startswith('F'):
                self.log(f"❌ 快充排队号格式错误: {queue_no} (应以F开头)")
                success = False
            else:
                self.log(f"✅ 快充排队号格式正确: {queue_no}")
        
        # 验证慢充排队号（应该以T开头）
        for queue_no in trickle_queue_numbers:
            if not queue_no.startswith('T'):
                self.log(f"❌ 慢充排队号格式错误: {queue_no} (应以T开头)")
                success = False
            else:
                self.log(f"✅ 慢充排队号格式正确: {queue_no}")
        
        return success
    
    def test_fault_handling(self):
        """测试故障处理机制"""
        self.log("=" * 60)
        self.log("🎯 测试4: 充电桩故障处理")
        self.log("=" * 60)
        
        # 创建用户并提交请求
        user = self.create_test_user(0)  # 传递索引
        if not user:
            return False
        
        # 提交快充请求
        session_id = self.submit_charging_request(user, "fast", 25.0)
        if not session_id:
            return False
        
        # 等待调度到充电桩
        self.log("⏳ 等待请求被调度到充电桩...")
        time.sleep(15)  # 增加等待时间
        
        # 多次检查充电桩状态
        occupied_pile_id = None
        for attempt in range(6):  # 最多检查6次
            system_status = self.get_system_status()
            piles = system_status.get('piles', [])
            
            for pile in piles:
                if pile.get('current_session'):
                    occupied_pile_id = pile.get('id')
                    self.log(f"🔍 发现被占用的充电桩: {occupied_pile_id}")
                    break
            
            if occupied_pile_id:
                break
                
            self.log(f"⏳ 第{attempt+1}次检查，未发现被占用的充电桩，等待...")
            time.sleep(5)
        
        if not occupied_pile_id:
            self.log("❌ 没有找到被占用的充电桩")
            # 输出调试信息
            self.log("🔍 当前所有充电桩状态:")
            for pile in piles:
                self.log(f"  {pile.get('id')}: {pile.get('db_status')} - 会话: {pile.get('current_session', '无')}")
            return False
        
        self.log(f"📍 充电桩 {occupied_pile_id} 被占用，模拟故障...")
        
        # 模拟充电桩故障（强制停止）
        stop_data = {"pile_id": occupied_pile_id, "force": True}
        response = self.admin_session.post(
            f"{self.base_url}/api/admin/pile/stop",
            json=stop_data,
            timeout=10
        )
        
        if response.status_code == 200:
            self.log(f"✅ 成功模拟充电桩 {occupied_pile_id} 故障")
        else:
            self.log(f"❌ 模拟故障失败: {response.status_code}")
            return False
        
        # 等待故障处理
        time.sleep(5)
        
        # 检查故障处理结果
        new_status = self.get_system_status()
        new_piles = new_status.get('piles', [])
        
        fault_pile = None
        for pile in new_piles:
            if pile.get('id') == occupied_pile_id:
                fault_pile = pile
                break
        
        if fault_pile and fault_pile.get('db_status') in ['fault', 'maintenance', 'offline']:
            self.log(f"✅ 故障充电桩状态正确: {fault_pile.get('db_status')}")
        else:
            self.log("❌ 故障充电桩状态异常")
        
        # 检查用户充电状态
        response = user['session'].get(f"{self.base_url}/api/charging/status")
        if response.status_code == 200:
            data = response.json().get('data', {})
            self.log(f"用户状态: {data.get('status', 'unknown')}")
        
        # 恢复充电桩
        start_data = {"pile_id": occupied_pile_id}
        response = self.admin_session.post(
            f"{self.base_url}/api/admin/pile/start",
            json=start_data,
            timeout=10
        )
        
        if response.status_code == 200:
            self.log(f"✅ 充电桩 {occupied_pile_id} 恢复成功")
            return True
        else:
            self.log(f"❌ 充电桩恢复失败: {response.status_code}")
            return False
    
    def run_all_tests(self):
        """运行所有调度测试"""
        self.log("🚀 开始充电桩调度功能测试")
        self.log("=" * 80)
        
        # 管理员登录
        if not self.admin_login():
            return False
        
        # 清理系统
        if not self.cleanup_system():
            return False
        
        # 定义测试套件
        tests = [
            ("基础调度策略测试", self.test_basic_scheduling_strategy),
            ("并发请求处理测试", self.test_concurrent_requests),
            ("排队号码生成测试", self.test_queue_number_generation),
            ("故障处理机制测试", self.test_fault_handling),
        ]
        
        results = {}
        
        for test_name, test_func in tests:
            self.log(f"\n🎯 开始执行: {test_name}")
            try:
                result = test_func()
                results[test_name] = result
                status = "✅ 通过" if result else "❌ 失败"
                self.log(f"{status}: {test_name}")
            except Exception as e:
                self.log(f"❌ {test_name} 执行异常: {e}", "ERROR")
                results[test_name] = False
            
            # 测试间清理和等待
            time.sleep(3)
            if test_name != tests[-1][0]:  # 不是最后一个测试
                self.cleanup_system()
        
        # 输出测试结果
        self.print_test_results(results)
        return all(results.values())
    
    def print_test_results(self, results):
        """打印测试结果"""
        self.log("\n" + "=" * 80)
        self.log("🎯 调度功能测试结果汇总")
        self.log("=" * 80)
        
        passed = sum(1 for result in results.values() if result)
        total = len(results)
        
        for test_name, result in results.items():
            status = "✅ 通过" if result else "❌ 失败"
            self.log(f"{test_name}: {status}")
        
        self.log(f"\n📊 总计: {passed}/{total} 个测试通过")
        self.log(f"📈 通过率: {(passed/total)*100:.1f}%")
        
        if passed == total:
            self.log("🎉 所有调度功能测试通过！")
            self.log("调度策略、排队机制、故障处理等核心功能工作正常。")
        else:
            self.log("⚠️ 部分调度功能存在问题，请检查：")
            self.log("1. 调度引擎是否正常运行")
            self.log("2. 充电桩状态管理是否正确")
            self.log("3. 队列管理逻辑是否有误")
            self.log("4. 故障处理机制是否完善")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='充电桩调度功能测试脚本')
    parser.add_argument('--url', default='http://localhost:5001',
                       help='服务器地址 (默认: http://localhost:5001)')
    
    args = parser.parse_args()
    
    tester = SchedulerTester(args.url)
    
    try:
        success = tester.run_all_tests()
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n测试被用户中断")
        exit(1)
    except Exception as e:
        print(f"测试执行出错: {e}")
        exit(1)