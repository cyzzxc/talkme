"""
应用配置模块
集中管理所有配置参数
"""

import os
from typing import List
from dotenv import load_dotenv
from loguru import logger

# 加载.env文件
load_dotenv()


class Settings:
    """
    应用设置类
    从环境变量读取配置，提供默认值
    """

    # 应用基础配置
    APP_HOST: str = os.getenv("APP_HOST", "0.0.0.0")
    APP_PORT: int = int(os.getenv("APP_PORT", "8000"))
    APP_SECRET: str = os.getenv("APP_SECRET", "changeme")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    # 数据库配置
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./files.db")

    # 文件存储配置
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./uploads")
    TEMP_DIR: str = os.getenv("TEMP_DIR", "./temp")
    MAX_FILE_SIZE: int = int(os.getenv("MAX_FILE_SIZE", "104857600"))  # 100MB

    # 安全配置
    CORS_ORIGINS: List[str] = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:3000,http://localhost:8080"
    ).split(",")

    # 文件去重配置
    HASH_ALGORITHM: str = os.getenv("HASH_ALGORITHM", "sha256")
    ENABLE_FILE_DEDUP: bool = os.getenv("ENABLE_FILE_DEDUP", "true").lower() == "true"

    # 异步任务配置
    MAX_HASH_WORKERS: int = int(os.getenv("MAX_HASH_WORKERS", "2"))
    HASH_CHUNK_SIZE: int = int(os.getenv("HASH_CHUNK_SIZE", "65536"))  # 64KB

    # 文件类型配置
    ALLOWED_EXTENSIONS: List[str] = os.getenv(
        "ALLOWED_EXTENSIONS",
        "jpg,jpeg,png,gif,pdf,txt,doc,docx,zip,rar,mp4,mp3"
    ).split(",")

    # 清理配置
    FILE_EXPIRE_DAYS: int = int(os.getenv("FILE_EXPIRE_DAYS", "7"))
    AUTO_CLEANUP: bool = os.getenv("AUTO_CLEANUP", "true").lower() == "true"
    CLEANUP_INTERVAL_HOURS: int = int(os.getenv("CLEANUP_INTERVAL_HOURS", "24"))

    # WebSocket 配置
    WS_HEARTBEAT_INTERVAL: int = int(os.getenv("WS_HEARTBEAT_INTERVAL", "30"))
    WS_MAX_CONNECTIONS: int = int(os.getenv("WS_MAX_CONNECTIONS", "100"))

    @classmethod
    def get_upload_path(cls, file_type: str) -> str:
        """
        获取指定文件类型的上传路径
        """
        type_dirs = {
            "image": "images",
            "document": "documents",
            "other": "others"
        }
        subdir = type_dirs.get(file_type, "others")
        return os.path.join(cls.UPLOAD_DIR, subdir)

    @classmethod
    def ensure_directories(cls):
        """
        确保所有必要目录存在
        """
        directories = [
            cls.UPLOAD_DIR,
            cls.TEMP_DIR,
            cls.get_upload_path("image"),
            cls.get_upload_path("document"),
            cls.get_upload_path("other")
        ]

        for directory in directories:
            os.makedirs(directory, exist_ok=True)

    @classmethod
    def is_allowed_extension(cls, filename: str) -> bool:
        """
        检查文件扩展名是否允许
        """
        if not filename or "." not in filename:
            return False

        extension = filename.rsplit(".", 1)[1].lower()
        return extension in cls.ALLOWED_EXTENSIONS

    @classmethod
    def validate_config(cls) -> List[str]:
        """
        验证配置的有效性
        返回错误信息列表
        """
        errors = []

        # 检查必要的配置
        if cls.APP_SECRET in ["changeme", ""]:
            errors.append("APP_SECRET 需要设置为安全的密码")

        if cls.MAX_FILE_SIZE <= 0:
            errors.append("MAX_FILE_SIZE 必须大于 0")

        if cls.MAX_HASH_WORKERS <= 0:
            errors.append("MAX_HASH_WORKERS 必须大于 0")

        # 检查目录权限
        try:
            cls.ensure_directories()
        except Exception as e:
            errors.append(f"无法创建目录: {e}")

        return errors


# 创建全局设置实例
settings = Settings()

# 验证配置
config_errors = settings.validate_config()
if config_errors:
    logger.error("配置验证失败:")
    for error in config_errors:
        logger.error(f"  - {error}")
    if not settings.DEBUG:
        raise ValueError("配置验证失败，请检查配置")
    else:
        logger.warning("DEBUG 模式下继续运行")