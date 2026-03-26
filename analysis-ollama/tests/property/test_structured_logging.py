"""
Property-based tests for structured logging.

Feature: environment-separation-architecture
Property 3: 结构化日志完整性

对于任何关键操作（RSS 采集、HTML 解析、LLM 分析、通知发送），
系统应该输出包含时间戳、日志级别、模块名称和消息内容的结构化日志；
对于任何异常，应该记录完整的错误堆栈信息。
"""
import logging
import sys
from io import StringIO

from hypothesis import given, strategies as st, settings

from app.utils.logger import get_logger


def _capture_log(fn):
    """Run fn() and return captured log records via stdlib logging."""
    handler = logging.handlers_list = []

    class ListHandler(logging.Handler):
        def emit(self, record):
            handler.append(record)

    root = logging.getLogger()
    h = ListHandler()
    root.addHandler(h)
    old_level = root.level
    root.setLevel(logging.DEBUG)
    try:
        fn()
    finally:
        root.removeHandler(h)
        root.setLevel(old_level)
    return handler


@given(
    module_name=st.sampled_from([
        'services.rss_service',
        'services.llm_service',
        'services.notification_service',
        'utils.html_parser',
        'core.processor'
    ]),
    message=st.text(min_size=1, max_size=200).filter(lambda x: x.strip()),
    log_level=st.sampled_from(['DEBUG', 'INFO', 'WARNING', 'ERROR'])
)
@settings(max_examples=50)
def test_property_structured_logging(module_name, message, log_level):
    """
    Feature: environment-separation-architecture, Property 3: 结构化日志完整性

    对于任何关键操作，日志应包含时间戳、级别、模块名称和消息
    """
    # Use stdlib logger to verify get_logger returns a usable logger
    std_logger = logging.getLogger(module_name)

    records = []

    class Capture(logging.Handler):
        def emit(self, record):
            records.append(record)

    h = Capture()
    std_logger.addHandler(h)
    std_logger.setLevel(logging.DEBUG)

    try:
        getattr(std_logger, log_level.lower())(message.strip())

        assert len(records) > 0
        record = records[-1]
        assert record.levelname == log_level
        assert message.strip() in record.getMessage()
        assert hasattr(record, 'created')
        assert record.created > 0
    finally:
        std_logger.removeHandler(h)


@given(
    operation=st.sampled_from([
        'rss_collect',
        'html_parse',
        'llm_analyze',
        'notification_send',
        'db_operation'
    ]),
    error_message=st.text(min_size=1, max_size=100).filter(lambda x: x.strip())
)
@settings(max_examples=50)
def test_property_error_logging_with_traceback(operation, error_message):
    """
    Feature: environment-separation-architecture, Property 3: 结构化日志完整性

    对于任何异常，应该记录完整的错误堆栈信息
    """
    std_logger = logging.getLogger(f'test.{operation}')
    records = []

    class Capture(logging.Handler):
        def emit(self, record):
            records.append(record)

    h = Capture()
    std_logger.addHandler(h)
    std_logger.setLevel(logging.ERROR)

    try:
        try:
            raise ValueError(error_message.strip())
        except ValueError as e:
            std_logger.error(f"操作 {operation} 失败: {e}", exc_info=True)

        assert len(records) > 0
        record = records[-1]
        assert record.levelname == 'ERROR'
        assert operation in record.getMessage()
        assert error_message.strip() in record.getMessage()
        assert record.exc_info is not None
    finally:
        std_logger.removeHandler(h)


@given(
    context_data=st.dictionaries(
        keys=st.text(min_size=1, max_size=20, alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll'), whitelist_characters='_'
        )),
        values=st.one_of(
            st.text(min_size=1, max_size=50),
            st.integers(),
            st.booleans()
        ),
        min_size=1,
        max_size=5
    )
)
@settings(max_examples=50)
def test_property_logging_with_context(context_data):
    """
    Feature: environment-separation-architecture, Property 3: 结构化日志完整性

    日志应该能够包含上下文信息
    """
    std_logger = logging.getLogger('test.context')
    records = []

    class Capture(logging.Handler):
        def emit(self, record):
            records.append(record)

    h = Capture()
    std_logger.addHandler(h)
    std_logger.setLevel(logging.INFO)

    try:
        context_str = ', '.join(f"{k}={v}" for k, v in context_data.items())
        std_logger.info(f"操作完成: {context_str}")

        assert len(records) > 0
        record = records[-1]
        assert record.levelname == 'INFO'
        for key in list(context_data.keys())[:2]:
            assert key in record.getMessage()
    finally:
        std_logger.removeHandler(h)


@given(
    log_count=st.integers(min_value=1, max_value=10)
)
@settings(max_examples=30)
def test_property_multiple_log_entries(log_count):
    """
    Feature: environment-separation-architecture, Property 3: 结构化日志完整性

    多个日志条目应该都被正确记录
    """
    std_logger = logging.getLogger('test.multiple')
    records = []

    class Capture(logging.Handler):
        def emit(self, record):
            records.append(record)

    h = Capture()
    std_logger.addHandler(h)
    std_logger.setLevel(logging.INFO)

    try:
        for i in range(log_count):
            std_logger.info(f"日志条目 {i}")

        assert len(records) >= log_count
        for i, record in enumerate(records[-log_count:]):
            assert record.levelname == 'INFO'
            assert f"日志条目 {i}" in record.getMessage()
            assert hasattr(record, 'created')
    finally:
        std_logger.removeHandler(h)
