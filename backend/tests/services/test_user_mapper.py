"""
用户字段映射器测试

测试策略：
1. 单元测试：测试每个转换方法
2. 边界测试：测试空值、异常值
3. 集成测试：测试完整转换流程
"""
import pytest
from datetime import datetime
from app.services.mappers.user_mapper import UserFieldMapper


class TestUserFieldMapper:
    """用户字段映射器测试类"""

    @pytest.fixture
    def mapper(self):
        """测试夹具：创建映射器实例"""
        return UserFieldMapper()

    @pytest.fixture
    def sample_user_data(self):
        """测试夹具：样本用户数据"""
        return {
            'id': 'user-123',
            'username': 'testuser',
            'email': 'test@example.com',
            'full_name': 'Test User',
            'nickname': 'Tester',
            'avatar': 'avatar.jpg',
            'gender': 1,
            'mobile': '13800138000',
            'is_active': True,
            'is_superuser': False,
            'created_at': datetime(2023, 1, 1, 12, 0, 0),
            'updated_at': datetime(2023, 1, 2, 12, 0, 0),
            'last_login': datetime(2023, 1, 3, 12, 0, 0),
            'roles': [
                {
                    'code': 'ADMIN',
                    'name': '管理员',
                    'permissions': [
                        {'code': 'user:read'},
                        {'code': 'user:write'}
                    ]
                }
            ]
        }

    def test_convert_user_to_frontend_basic(self, mapper, sample_user_data):
        """测试基础转换功能"""
        result = mapper.convert_user_to_frontend(sample_user_data)

        # 验证字段映射
        assert result['userId'] == 'user-123'
        assert result['username'] == 'testuser'
        assert result['nickname'] == 'Tester'
        assert result['avatar'] == 'avatar.jpg'

        # 验证时间格式转换
        assert 'createTime' in result
        assert isinstance(result['createTime'], str)

        # 验证角色和权限提取
        assert 'roles' in result
        assert 'perms' in result
        assert 'ADMIN' in result['roles']
        assert 'user:read' in result['perms']

    def test_convert_user_to_frontend_missing_nickname(self, mapper):
        """测试昵称缺失时的处理"""
        user_data = {
            'id': 'user-123',
            'username': 'testuser',
            'full_name': 'Test User',
            'avatar': None,
            'is_active': True
        }

        result = mapper.convert_user_to_frontend(user_data)

        # 应该使用full_name作为nickname
        assert result['nickname'] == 'Test User'

        # 如果full_name也为空，使用username
        user_data['full_name'] = None
        result = mapper.convert_user_to_frontend(user_data)
        assert result['nickname'] == 'testuser'

    def test_convert_user_to_frontend_status_conversion(self, mapper):
        """测试状态转换"""
        # 活跃用户
        user_data = {'id': '1', 'username': 'user1', 'is_active': True}
        result = mapper.convert_user_to_frontend(user_data)
        assert result['status'] == 1

        # 非活跃用户
        user_data['is_active'] = False
        result = mapper.convert_user_to_frontend(user_data)
        assert result['status'] == 0

    def test_convert_user_to_frontend_sensitive_data(self, mapper):
        """测试敏感数据清理"""
        user_data = {
            'id': 'user-123',
            'username': 'testuser',
            'hashed_password': 'secret',
            'password': 'plaintext',
            'token': 'jwt-token'
        }

        result = mapper.convert_user_to_frontend(user_data)

        # 敏感字段应该被移除
        assert 'hashed_password' not in result
        assert 'password' not in result
        assert 'token' not in result

    def test_convert_frontend_to_backend(self, mapper):
        """测试前端到后端转换"""
        frontend_data = {
            'userId': 'user-123',
            'userName': 'testuser',
            'email': 'test@example.com',
            'status': 1,
            'createTime': '2023-01-01T12:00:00'
        }

        result = mapper.convert_frontend_to_backend(frontend_data)

        # 验证字段映射
        assert result['id'] == 'user-123'
        assert result['username'] == 'testuser'
        assert result['is_active'] is True

        # 验证前端特有字段被移除
        assert 'status' not in result
        assert 'createTime' not in result

    def test_extract_user_info(self, mapper, sample_user_data):
        """测试提取用户基本信息"""
        result = mapper.extract_user_info(sample_user_data)

        # 验证只包含基本信息
        expected_fields = {'userId', 'username', 'nickname', 'avatar', 'roles', 'perms'}
        assert set(result.keys()) == expected_fields

        # 验证数据正确性
        assert result['userId'] == 'user-123'
        assert result['username'] == 'testuser'
        assert 'ADMIN' in result['roles']

    def test_batch_conversion(self, mapper):
        """测试批量转换"""
        users_data = [
            {'id': '1', 'username': 'user1', 'is_active': True},
            {'id': '2', 'username': 'user2', 'is_active': False}
        ]

        results = mapper.convert_users_to_frontend(users_data)

        assert len(results) == 2
        assert results[0]['userId'] == '1'
        assert results[1]['userId'] == '2'
        assert results[0]['status'] == 1
        assert results[1]['status'] == 0