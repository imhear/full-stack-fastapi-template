#!/bin/bash
cd /Users/wutao/code/full-stack-fastapi-template/backend

echo "启动 Redis 容器..."
docker-compose -f docker-compose.dev.yml up -d redis

echo "等待 Redis 启动..."
sleep 3

echo "测试 Redis 连接..."
if docker-compose -f docker-compose.dev.yml exec redis redis-cli ping | grep -q "PONG"; then
    echo "✅ Redis 启动成功"
    echo "连接信息:"
    echo "  Host: localhost"
    echo "  Port: 6379"
    echo "  DB: 0"
else
    echo "❌ Redis 启动失败"
    docker-compose -f docker-compose.dev.yml logs redis
fi
