#!/bin/bash
echo "=== Redis 集成验证 ==="
echo ""

echo "1. 检查容器状态..."
if docker-compose -f docker-compose.dev.yml ps | grep -q "Up"; then
    echo "✅ Redis 容器正在运行"
else
    echo "❌ Redis 容器未运行"
fi

echo ""
echo "2. 检查端口监听..."
if netstat -an | grep 6379 | grep -q LISTEN; then
    echo "✅ Redis 端口 6379 正在监听"
else
    echo "⚠️  Redis 端口未在宿主机监听（Docker 内部网络正常）"
fi

echo ""
echo "3. 测试 Redis 连接..."
if docker exec fastapi-redis redis-cli ping 2>/dev/null | grep -q PONG; then
    echo "✅ Redis 连接正常"
    
    # 测试数据操作
    docker exec fastapi-redis redis-cli set verify:test "success" > /dev/null 2>&1
    result=$(docker exec fastapi-redis redis-cli get verify:test 2>/dev/null)
    if [ "$result" = "success" ]; then
        echo "✅ Redis 数据操作正常"
    else
        echo "⚠️  Redis 数据操作可能有问题"
    fi
    docker exec fastapi-redis redis-cli del verify:test > /dev/null 2>&1
else
    echo "❌ Redis 连接失败"
fi

echo ""
echo "4. 检查镜像来源..."
docker images | grep "localhost:5001/redis" | awk '{print "✅ Redis 镜像来自私有库: "$1":"$2}'

echo ""
echo "5. 检查数据持久化..."
if docker volume ls | grep -q "redis-data"; then
    echo "✅ Redis 数据卷存在，数据将持久化"
else
    echo "⚠️  Redis 数据卷不存在"
fi

echo ""
echo "=== 验证完成 ==="
echo "你的后端应用可以使用以下配置连接 Redis:"
echo "  Host: localhost"
echo "  Port: 6379"
echo "  DB: 0"
echo "  密码: 无"
