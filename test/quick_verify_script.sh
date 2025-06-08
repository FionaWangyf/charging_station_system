#!/bin/bash

# 充电桩管理系统 - 快速验证脚本
# 用于检查系统基本功能是否正常

set -e

BASE_URL=${1:-"http://localhost:5001"}
COOKIE_FILE="/tmp/charging_test_cookies.txt"
ADMIN_COOKIE_FILE="/tmp/charging_admin_cookies.txt"

echo "======================================"
echo "充电桩管理系统快速验证测试"
echo "服务器地址: $BASE_URL"
echo "======================================"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 测试结果统计
TOTAL_TESTS=0
PASSED_TESTS=0

# 测试函数
test_api() {
    local test_name="$1"
    local method="$2"
    local url="$3"
    local data="$4"
    local expected_status="$5"
    local cookie_file="$6"
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    echo -n "测试 $TOTAL_TESTS: $test_name ... "
    
    if [ -n "$data" ]; then
        if [ -n "$cookie_file" ]; then
            response=$(curl -s -w "%{http_code}" -X "$method" \
                -H "Content-Type: application/json" \
                -d "$data" \
                -b "$cookie_file" \
                -c "$cookie_file" \
                "$url" 2>/dev/null)
        else
            response=$(curl -s -w "%{http_code}" -X "$method" \
                -H "Content-Type: application/json" \
                -d "$data" \
                "$url" 2>/dev/null)
        fi
    else
        if [ -n "$cookie_file" ]; then
            response=$(curl -s -w "%{http_code}" -X "$method" \
                -b "$cookie_file" \
                -c "$cookie_file" \
                "$url" 2>/dev/null)
        else
            response=$(curl -s -w "%{http_code}" -X "$method" \
                "$url" 2>/dev/null)
        fi
    fi
    
    status_code="${response: -3}"
    body="${response%???}"
    
    if [ "$status_code" = "$expected_status" ]; then
        echo -e "${GREEN}✅ 通过${NC} (HTTP $status_code)"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        return 0
    else
        echo -e "${RED}❌ 失败${NC} (期望: $expected_status, 实际: $status_code)"
        echo "响应内容: $body"
        return 1
    fi
}

# 清理函数
cleanup() {
    rm -f "$COOKIE_FILE" "$ADMIN_COOKIE_FILE"
}

# 设置退出时清理
trap cleanup EXIT

echo -e "\n${YELLOW}1. 系统健康检查${NC}"
test_api "系统健康状态" "GET" "$BASE_URL/health" "" "200"

echo -e "\n${YELLOW}2. 用户注册与登录${NC}"
test_api "用户注册" "POST" "$BASE_URL/api/user/register" \
    '{"car_id":"京TEST01","username":"quicktest","password":"test123","car_capacity":60.0}' \
    "201"

test_api "用户登录" "POST" "$BASE_URL/api/user/login" \
    '{"username":"quicktest","password":"test123"}' \
    "200" "$COOKIE_FILE"

test_api "获取用户信息" "GET" "$BASE_URL/api/user/profile" \
    "" "200" "$COOKIE_FILE"

echo -e "\n${YELLOW}3. 管理员功能${NC}"
test_api "管理员登录" "POST" "$BASE_URL/api/user/login" \
    '{"username":"admin","password":"admin123"}' \
    "200" "$ADMIN_COOKIE_FILE"

test_api "管理员系统概览" "GET" "$BASE_URL/api/admin/overview" \
    "" "200" "$ADMIN_COOKIE_FILE"

test_api "查看充电桩状态" "GET" "$BASE_URL/api/admin/piles/status" \
    "" "200" "$ADMIN_COOKIE_FILE"

echo -e "\n${YELLOW}4. 充电请求${NC}"
test_api "提交快充请求" "POST" "$BASE_URL/api/charging/request" \
    '{"charging_mode":"fast","requested_amount":25.0}' \
    "201" "$COOKIE_FILE"

test_api "查询充电状态" "GET" "$BASE_URL/api/charging/status" \
    "" "200" "$COOKIE_FILE"

test_api "查询系统状态" "GET" "$BASE_URL/api/charging/system-status" \
    "" "200"

echo -e "\n${YELLOW}5. 计费系统${NC}"
test_api "获取电价配置" "GET" "$BASE_URL/api/billing/rates" \
    "" "200"

test_api "计算充电费用" "POST" "$BASE_URL/api/billing/calculate" \
    '{"start_time":"2025-06-07T10:00:00","end_time":"2025-06-07T11:00:00","power_consumed":25.0}' \
    "200" "$COOKIE_FILE"

echo -e "\n${YELLOW}6. 统计功能${NC}"
test_api "统计概览" "GET" "$BASE_URL/api/statistics/overview" \
    "" "200" "$ADMIN_COOKIE_FILE"

test_api "日统计数据" "GET" "$BASE_URL/api/statistics/daily?days=7" \
    "" "200" "$ADMIN_COOKIE_FILE"

echo -e "\n${YELLOW}7. 异常处理测试${NC}"
test_api "重复充电请求" "POST" "$BASE_URL/api/charging/request" \
    '{"charging_mode":"fast","requested_amount":20.0}' \
    "400" "$COOKIE_FILE"

test_api "无效参数" "POST" "$BASE_URL/api/charging/request" \
    '{"charging_mode":"invalid","requested_amount":-10}' \
    "400" "$COOKIE_FILE"

# 测试结果汇总
echo ""
echo "======================================"
echo "测试结果汇总"
echo "======================================"
echo "总测试数: $TOTAL_TESTS"
echo -e "通过数: ${GREEN}$PASSED_TESTS${NC}"
echo -e "失败数: ${RED}$((TOTAL_TESTS - PASSED_TESTS))${NC}"

success_rate=$(echo "scale=1; $PASSED_TESTS * 100 / $TOTAL_TESTS" | bc)
echo "通过率: $success_rate%"

if [ "$PASSED_TESTS" = "$TOTAL_TESTS" ]; then
    echo -e "\n${GREEN}🎉 所有测试通过！系统功能正常${NC}"
    exit 0
else
    echo -e "\n${YELLOW}⚠️ 部分测试失败，请检查系统状态${NC}"
    exit 1
fi