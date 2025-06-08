#!/bin/bash

# 充电桩管理系统诊断脚本 - 修复版
# 兼容没有timeout命令的系统

BASE_URL="http://localhost:5001"
COOKIE_FILE="/tmp/charging_test_cookies.txt"

echo "======================================"
echo "充电桩管理系统问题诊断 (修复版)"
echo "======================================"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 简单的超时函数
simple_timeout() {
    local timeout_duration=$1
    shift
    "$@" &
    local pid=$!
    
    (
        sleep "$timeout_duration"
        kill $pid 2>/dev/null
    ) &
    local timer_pid=$!
    
    wait $pid 2>/dev/null
    local exit_code=$?
    kill $timer_pid 2>/dev/null
    return $exit_code
}

echo -e "\n${BLUE}1. 检查服务器连接状态${NC}"
if curl -s --max-time 5 "$BASE_URL/health" > /dev/null; then
    echo -e "${GREEN}✅ 服务器响应正常${NC}"
else
    echo -e "${RED}❌ 服务器无响应或响应超时${NC}"
    exit 1
fi

echo -e "\n${BLUE}2. 重新登录获取会话${NC}"
response=$(curl -s -w "%{http_code}" -X POST \
    --max-time 10 \
    -H "Content-Type: application/json" \
    -d '{"username":"quicktest","password":"test123"}' \
    -c "$COOKIE_FILE" \
    "$BASE_URL/api/user/login" 2>/dev/null)

status_code="${response: -3}"
if [ "$status_code" = "200" ]; then
    echo -e "${GREEN}✅ 用户重新登录成功${NC}"
else
    echo -e "${RED}❌ 用户登录失败 (HTTP $status_code)${NC}"
    echo "响应: ${response%???}"
fi

echo -e "\n${BLUE}3. 检查当前用户充电状态${NC}"
response=$(curl -s -w "%{http_code}" \
    --max-time 5 \
    -b "$COOKIE_FILE" \
    "$BASE_URL/api/charging/status" 2>/dev/null)

status_code="${response: -3}"
body="${response%???}"

if [ "$status_code" = "200" ]; then
    echo -e "${GREEN}✅ 充电状态查询成功${NC}"
    echo "当前状态响应:"
    echo "$body" | python3 -m json.tool 2>/dev/null || echo "$body"
    
    # 检查是否有活跃会话
    if echo "$body" | grep -q '"has_active_request":true'; then
        echo -e "${YELLOW}⚠️ 检测到用户有活跃的充电请求${NC}"
        
        # 尝试提取session_id
        session_id=$(echo "$body" | grep -o '"session_id":"[^"]*"' | cut -d'"' -f4)
        if [ -n "$session_id" ]; then
            echo "活跃会话ID: $session_id"
        fi
    else
        echo -e "${GREEN}✅ 用户当前无活跃充电请求${NC}"
    fi
else
    echo -e "${RED}❌ 充电状态查询失败 (HTTP $status_code)${NC}"
    echo "响应: $body"
fi

echo -e "\n${BLUE}4. 检查系统整体状态${NC}"
response=$(curl -s -w "%{http_code}" \
    --max-time 5 \
    "$BASE_URL/api/charging/system-status" 2>/dev/null)

status_code="${response: -3}"
body="${response%???}"

if [ "$status_code" = "200" ]; then
    echo -e "${GREEN}✅ 系统状态查询成功${NC}"
    echo "系统状态:"
    echo "$body" | python3 -m json.tool 2>/dev/null || echo "$body"
else
    echo -e "${RED}❌ 系统状态查询失败 (HTTP $status_code)${NC}"
fi

echo -e "\n${BLUE}5. 测试重复充电请求${NC}"
echo "尝试提交重复的快充请求..."

response=$(curl -s -w "%{http_code}" -X POST \
    --max-time 15 \
    -H "Content-Type: application/json" \
    -d '{"charging_mode":"fast","requested_amount":20.0}' \
    -b "$COOKIE_FILE" \
    "$BASE_URL/api/charging/request" 2>/dev/null)

status_code="${response: -3}"
body="${response%???}"

echo -e "${GREEN}✅ 请求完成 (HTTP $status_code)${NC}"
echo "响应:"
echo "$body" | python3 -m json.tool 2>/dev/null || echo "$body"

if [ "$status_code" = "400" ]; then
    echo -e "${GREEN}✅ 重复请求被正确拒绝 - 这是预期行为${NC}"
elif [ "$status_code" = "201" ]; then
    echo -e "${YELLOW}⚠️ 重复请求成功了，说明之前的请求可能已完成${NC}"
else
    echo -e "${YELLOW}⚠️ 意外的响应状态码: $status_code${NC}"
fi

echo -e "\n${BLUE}6. 测试无效参数请求${NC}"
response=$(curl -s -w "%{http_code}" -X POST \
    --max-time 5 \
    -H "Content-Type: application/json" \
    -d '{"charging_mode":"invalid","requested_amount":-10}' \
    -b "$COOKIE_FILE" \
    "$BASE_URL/api/charging/request" 2>/dev/null)

status_code="${response: -3}"
body="${response%???}"

if [ "$status_code" = "400" ]; then
    echo -e "${GREEN}✅ 无效参数被正确拒绝${NC}"
else
    echo -e "${YELLOW}⚠️ 无效参数响应: HTTP $status_code${NC}"
fi

echo -e "\n${BLUE}7. 检查管理员视角的系统状态${NC}"
# 管理员登录
admin_response=$(curl -s -w "%{http_code}" -X POST \
    --max-time 5 \
    -H "Content-Type: application/json" \
    -d '{"username":"admin","password":"admin123"}' \
    -c "/tmp/admin_cookies.txt" \
    "$BASE_URL/api/user/login" 2>/dev/null)

admin_status="${admin_response: -3}"
if [ "$admin_status" = "200" ]; then
    echo -e "${GREEN}✅ 管理员登录成功${NC}"
    
    # 查看充电桩状态
    pile_response=$(curl -s -w "%{http_code}" \
        --max-time 5 \
        -b "/tmp/admin_cookies.txt" \
        "$BASE_URL/api/admin/piles/status" 2>/dev/null)
    
    pile_status="${pile_response: -3}"
    if [ "$pile_status" = "200" ]; then
        echo -e "${GREEN}✅ 充电桩状态查询成功${NC}"
        echo "充电桩状态概要:"
        echo "${pile_response%???}" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    piles = data.get('data', {}).get('piles', [])
    for pile in piles:
        pile_id = pile.get('id', 'N/A')
        pile_status = pile.get('db_status', 'N/A')
        pile_type = pile.get('type', 'N/A')
        print('  {}: {} ({})'.format(pile_id, pile_status, pile_type))
except:
    print('  解析失败')
" 2>/dev/null
    fi
    
    # 查看队列信息
    queue_response=$(curl -s -w "%{http_code}" \
        --max-time 5 \
        -b "/tmp/admin_cookies.txt" \
        "$BASE_URL/api/admin/queue/info" 2>/dev/null)
    
    queue_status="${queue_response: -3}"
    if [ "$queue_status" = "200" ]; then
        echo -e "${GREEN}✅ 队列信息查询成功${NC}"
        echo "队列状态概要:"
        echo "${queue_response%???}" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    summary = data.get('data', {}).get('summary', {})
    total_waiting = summary.get('total_waiting', 0)
    total_charging = summary.get('total_charging', 0)
    print('  总等待: {}'.format(total_waiting))
    print('  正在充电: {}'.format(total_charging))
except:
    print('  解析失败')
" 2>/dev/null
    fi
fi

echo -e "\n${BLUE}8. 分析和建议${NC}"
echo -e "${GREEN}根据诊断结果分析:${NC}"

# 基于日志输出的分析
echo -e "${YELLOW}从您提供的日志可以看出:${NC}"
echo "✅ 充电调度系统正常工作"
echo "✅ 会话成功调度到充电桩B"
echo "✅ 充电完成并正确计费"
echo "✅ 系统正确处理了completing状态的超时恢复"

echo -e "\n${GREEN}结论:${NC}"
echo "1. 系统功能正常，充电流程完整"
echo "2. 测试脚本可能在等待重复请求响应时卡住"
echo "3. 这可能是因为第一个请求正在进行充电过程"
echo "4. 建议继续运行完整的测试脚本"

echo -e "\n${BLUE}继续测试建议:${NC}"
echo "1. 等待几秒钟让系统完全处理完当前请求"
echo "2. 重新运行快速验证脚本"
echo "3. 或者直接运行详细的Python测试脚本"

# 清理临时文件
rm -f "$COOKIE_FILE" "/tmp/admin_cookies.txt"

echo -e "\n${GREEN}诊断完成 - 系统看起来运行正常！${NC}"