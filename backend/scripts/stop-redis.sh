#!/bin/bash
cd /Users/wutao/code/full-stack-fastapi-template/backend
echo "停止 Redis 容器..."
docker-compose -f docker-compose.dev.yml down
