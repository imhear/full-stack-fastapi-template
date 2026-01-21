"""
验证码服务层
backend/app/services/captcha_service.py
"""
import random
import string
import base64
from typing import Dict, Optional
from fastapi import HTTPException

from app.services.redis_service import RedisService


class CaptchaService:
    """验证码服务（专门处理验证码相关业务）"""

    def __init__(self, redis_service: RedisService):
        self.redis_service = redis_service

    async def generate_captcha(self) -> Dict[str, str]:
        """生成验证码（复用你现有方案的逻辑）"""
        try:
            # 生成验证码（4位数字）
            captcha_code = ''.join(random.choices(string.digits, k=4))

            # 生成唯一ID
            captcha_id = ''.join(random.choices(
                string.ascii_letters + string.digits,
                k=16
            ))

            # 存储到Redis，5分钟过期
            await self.redis_service.cache_captcha(captcha_id, captcha_code, 300)

            # 生成SVG验证码图片
            svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" width="120" height="40">
                <rect width="120" height="40" fill="#f5f5f5"/>
                <rect x="5" y="5" width="110" height="30" rx="4" fill="white" stroke="#e0e0e0" stroke-width="1"/>
                <text x="60" y="25" text-anchor="middle" font-family="Arial" font-size="20" font-weight="bold" fill="#333">
                    {captcha_code}
                </text>
                <!-- 添加一些干扰线 -->
                <line x1="10" y1="15" x2="110" y2="30" stroke="#ccc" stroke-width="1" opacity="0.6"/>
                <line x1="20" y1="35" x2="100" y2="10" stroke="#ccc" stroke-width="1" opacity="0.6"/>
                <line x1="40" y1="8" x2="80" y2="32" stroke="#ccc" stroke-width="1" opacity="0.6"/>
            </svg>'''

            # 转换为base64
            captcha_base64 = f"data:image/svg+xml;base64,{base64.b64encode(svg_content.encode()).decode()}"

            return {
                "captchaId": captcha_id,
                "captchaBase64": captcha_base64
            }

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"生成验证码失败: {str(e)}"
            )

    async def verify_captcha(self, captcha_id: str, captcha_code: str) -> bool:
        """验证验证码"""
        if not captcha_id or not captcha_code:
            return False

        # 获取存储的验证码
        stored_captcha = await self.redis_service.get_captcha(captcha_id)
        if not stored_captcha:
            return False

        # 验证码不区分大小写比较
        if stored_captcha.upper() != captcha_code.upper():
            # 记录验证失败次数
            await self.redis_service.incr(f"captcha_fail:{captcha_id}")
            await self.redis_service.expire(f"captcha_fail:{captcha_id}", 300)
            return False

        # 验证成功后删除验证码
        await self.redis_service.delete(f"captcha:{captcha_id}")
        return True

    async def check_login_security(self, username: str) -> Dict[str, any]:
        """检查登录安全状态（失败次数、是否锁定）"""
        failures = await self.redis_service.record_login_failure(username)
        is_locked = await self.redis_service.is_account_locked(username)

        return {
            "failures": failures,
            "is_locked": is_locked,
            "max_attempts": 5
        }