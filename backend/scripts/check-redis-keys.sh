#!/bin/bash
echo "=== Redis 键值查看工具 ==="

# 获取 captchaId（从参数或上次的响应）
CAPTCHA_ID="$1"
if [ -z "$CAPTCHA_ID" ]; then
    echo "请提供 captchaId，或者上次的验证码ID是: F2e6ZH9ibzOTWANb"
    read -p "输入 captchaId (直接回车使用默认): " INPUT_ID
    CAPTCHA_ID="${INPUT_ID:-F2e6ZH9ibzOTWANb}"
fi

echo ""
echo "正在检查验证码键: app:captcha:$CAPTCHA_ID"

# 查看键是否存在
echo "1. 检查键是否存在:"
docker-compose -f docker-compose.dev.yml exec redis redis-cli EXISTS "app:captcha:$CAPTCHA_ID"

# 查看键的类型
echo "2. 键的类型:"
docker-compose -f docker-compose.dev.yml exec redis redis-cli TYPE "app:captcha:$CAPTCHA_ID"

# 查看键的值
echo "3. 键的值:"
docker-compose -f docker-compose.dev.yml exec redis redis-cli GET "app:captcha:$CAPTCHA_ID"

# 查看键的剩余时间
echo "4. 剩余生存时间 (秒):"
docker-compose -f docker-compose.dev.yml exec redis redis-cli TTL "app:captcha:$CAPTCHA_ID"

echo ""
echo "5. 查看所有验证码键:"
docker-compose -f docker-compose.dev.yml exec redis redis-cli KEYS "app:captcha:*"

echo ""
echo "6. 查看所有键（带 app: 前缀）:"
docker-compose -f docker-compose.dev.yml exec redis redis-cli KEYS "app:*"

echo ""
echo "=== 完成 ==="
