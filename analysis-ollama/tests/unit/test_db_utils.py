"""
Unit tests for database utilities.
"""
import pytest
from unittest.mock import patch, MagicMock
from app.utils.db_utils import (
    check_db_health,
    get_pool_status
)


def test_check_db_health_success():
    """测试数据库健康检查成功"""
    mock_engine = MagicMock()
    mock_conn = MagicMock()
    mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
    mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

    result = check_db_health(mock_engine)
    assert result is True


def test_check_db_health_failure():
    """测试数据库健康检查失败"""
    mock_engine = MagicMock()
    mock_engine.connect.side_effect = Exception("Connection refused")

    result = check_db_health(mock_engine)
    assert result is False


def test_get_pool_status():
    """测试获取连接池状态"""
    mock_engine = MagicMock()
    mock_pool = MagicMock()
    mock_pool.size.return_value = 5
    mock_pool.checkedin.return_value = 4
    mock_pool.checkedout.return_value = 1
    mock_pool.overflow.return_value = 0
    mock_engine.pool = mock_pool

    status = get_pool_status(mock_engine)
    assert isinstance(status, dict)
    assert status['pool_size'] == 5
    assert status['checked_in'] == 4
    assert status['checked_out'] == 1
    assert status['overflow'] == 0


def test_create_db_engine_config():
    """测试 create_db_engine 使用正确的 MySQL 参数"""
    # 通过 patch create_engine 并跳过 event 注册来验证参数
    with patch('app.utils.db_utils.create_engine') as mock_create, \
         patch('app.utils.db_utils.event.listens_for'):
        from app.utils.db_utils import create_db_engine
        mock_create.return_value = MagicMock()

        create_db_engine("mysql+pymysql://user:pass@127.0.0.1:3306/db", echo=False)

        call_kwargs = mock_create.call_args[1]
        assert call_kwargs['connect_args']['connect_timeout'] == 30
        assert call_kwargs['connect_args']['charset'] == 'utf8mb4'
        assert call_kwargs['pool_pre_ping'] is True
        assert call_kwargs['pool_size'] == 5
        assert call_kwargs['max_overflow'] == 10
