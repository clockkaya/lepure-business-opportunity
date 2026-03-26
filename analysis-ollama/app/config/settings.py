"""
配置管理

使用 Pydantic 进行环境变量验证和配置管理
"""
import sys
import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from pydantic import field_validator, ValidationError
from pydantic_settings import BaseSettings

# 根据 ENV 环境变量加载对应的配置文件
# 默认为 dev 环境
env = os.getenv('ENV', 'dev')
# 从 app/config/settings.py 向上两级到项目根目录
project_root = Path(__file__).parent.parent.parent
env_file = project_root / f'.env.{env}'

if env_file.exists():
    load_dotenv(env_file)
    print(f"已加载配置文件: {env_file}")
else:
    print(f"警告: 配置文件 {env_file} 不存在，将使用环境变量")
    load_dotenv()  # 尝试加载默认的 .env 文件

class Settings(BaseSettings):
    """
    应用配置类
    
    从环境变量加载配置并进行验证
    """
    # 应用设置
    ENV: str = "dev"
    POLL_INTERVAL_MINUTES: int = 60  # 轮询间隔（分钟），仅在未配置 CRON_SCHEDULE 时使用
    CRON_SCHEDULE: Optional[str] = None  # Cron 定时任务，例如 "10:30,14:30" 表示每天 10:30 和 14:30 执行
    RSS_FETCH_LIMIT: int = 100  # RSS API 每次获取的文章数量限制

    # WeWe-RSS 源
    WEWE_RSS_URL: str
    AUTH_CODE: str
    
    # 数据库
    DB_HOST: str
    DB_PORT: int
    DB_USER: str
    DB_PASSWORD: str
    DB_NAME: str = "analysis_ollama"
    
    # AI 引擎
    OLLAMA_BASE_URL: str
    MODEL_NAME: str
    
    # 通知
    WECOM_WEBHOOK_URL: str = ""
    
    # 日志
    LOG_LEVEL: str = "INFO"

    @field_validator("WEWE_RSS_URL")
    @classmethod
    def validate_wewe_rss_url(cls, v: str) -> str:
        """验证 WeWe-RSS URL"""
        if not v or not v.strip():
            raise ValueError("WEWE_RSS_URL 是必需的。请在 .env 文件中设置（例如：WEWE_RSS_URL=http://localhost:4000）")
        return v.strip()

    @field_validator("AUTH_CODE")
    @classmethod
    def validate_auth_code(cls, v: str) -> str:
        """验证认证代码"""
        if not v or not v.strip():
            raise ValueError("AUTH_CODE 是必需的。请在 .env 文件中设置（例如：AUTH_CODE=123567）")
        return v.strip()

    @field_validator("DB_HOST")
    @classmethod
    def validate_db_host(cls, v: str) -> str:
        """验证数据库主机"""
        if not v or not v.strip():
            raise ValueError("DB_HOST 是必需的。请在 .env 文件中设置（例如：DB_HOST=127.0.0.1）")
        return v.strip()

    @field_validator("DB_USER")
    @classmethod
    def validate_db_user(cls, v: str) -> str:
        """验证数据库用户"""
        if not v or not v.strip():
            raise ValueError("DB_USER 是必需的。请在 .env 文件中设置（例如：DB_USER=root）")
        return v.strip()

    @field_validator("DB_PASSWORD")
    @classmethod
    def validate_db_password(cls, v: str) -> str:
        """验证数据库密码"""
        if not v or not v.strip():
            raise ValueError("DB_PASSWORD 是必需的。请在 .env 文件中设置（例如：DB_PASSWORD=your_password）")
        return v.strip()

    @field_validator("OLLAMA_BASE_URL")
    @classmethod
    def validate_ollama_base_url(cls, v: str) -> str:
        """验证 Ollama 服务地址"""
        if not v or not v.strip():
            raise ValueError("OLLAMA_BASE_URL 是必需的。请在 .env 文件中设置（例如：OLLAMA_BASE_URL=http://192.168.10.43:11434）")
        return v.strip()

    @field_validator("MODEL_NAME")
    @classmethod
    def validate_model_name(cls, v: str) -> str:
        """验证模型名称"""
        if not v or not v.strip():
            raise ValueError("MODEL_NAME 是必需的。请在 .env 文件中设置（例如：MODEL_NAME=deepseek-r1:32b）")
        return v.strip()

    @field_validator("WECOM_WEBHOOK_URL")
    @classmethod
    def validate_wecom_webhook_url(cls, v: str) -> str:
        """验证企业微信 Webhook URL（可选）"""
        # 允许为空，跳过企业微信通知
        if not v or not v.strip() or v.strip() == "placeholder":
            return ""
        return v.strip()

    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """验证日志级别"""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"LOG_LEVEL 必须是以下之一 {valid_levels}。得到: {v}")
        return v_upper

    @property
    def database_url(self) -> str:
        """生成数据库连接 URL"""
        return f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"


def load_settings() -> Settings:
    """
    从环境变量加载并验证配置
    
    Returns:
        Settings: 验证后的配置对象
        
    Raises:
        SystemExit: 如果配置验证失败
    """
    try:
        return Settings()
    except ValidationError as e:
        print("=" * 80)
        print("配置错误：缺少或无效的必需环境变量")
        print("=" * 80)
        print()
        
        for error in e.errors():
            field = ".".join(str(loc) for loc in error["loc"])
            message = error["msg"]
            print(f"❌ {field}: {message}")
            print()
        
        print("=" * 80)
        print("请检查您的 .env 文件，确保所有必需的变量都已设置。")
        print("参考 .env.example 获取完整的必需变量列表。")
        print("=" * 80)
        sys.exit(1)


settings = load_settings()
