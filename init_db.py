#!/usr/bin/env python3
"""
数据库初始化脚本
创建数据库表和必要的索引
"""

import asyncio
import os
import sys
from loguru import logger

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import init_db, check_db_health_sync, create_tables, engine


def create_directories():
    """
    创建必要的目录结构
    """
    directories = [
        "uploads",
        "uploads/images",
        "uploads/documents",
        "uploads/others",
        "temp"
    ]

    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        logger.info(f"✓ 创建目录: {directory}")


def check_database_connection():
    """
    检查数据库连接
    """
    logger.info("检查数据库连接...")
    if check_db_health_sync():
        logger.info("✓ 数据库连接正常")
        return True
    else:
        logger.error("✗ 数据库连接失败")
        return False


def create_database_tables():
    """
    创建数据库表
    """
    logger.info("创建数据库表...")
    try:
        # 导入所有模型以确保它们被注册

        # 创建所有表
        create_tables()
        logger.info("✓ 数据库表创建成功")

        # 验证表是否创建成功
        with engine.connect() as conn:
            result = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in result.fetchall()]

            expected_tables = ["files", "messages", "hash_tasks"]
            for table in expected_tables:
                if table in tables:
                    logger.info(f"✓ 表 {table} 已创建")
                else:
                    logger.error(f"✗ 表 {table} 创建失败")

        return True
    except Exception as e:
        logger.error(f"✗ 创建数据库表失败: {e}")
        return False


def show_table_info():
    """
    显示表结构信息
    """
    logger.info("\n数据库表结构信息:")
    logger.info("=" * 50)

    try:
        with engine.connect() as conn:
            # 获取所有表名
            result = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in result.fetchall()]

            for table in tables:
                logger.info(f"\n表: {table}")
                logger.info("-" * 30)

                # 获取表结构
                result = conn.execute(f"PRAGMA table_info({table})")
                columns = result.fetchall()

                for col in columns:
                    col_id, name, col_type, not_null, default, pk = col
                    pk_mark = " (PK)" if pk else ""
                    null_mark = " NOT NULL" if not_null else ""
                    default_mark = f" DEFAULT {default}" if default else ""
                    logger.info(f"  {name}: {col_type}{pk_mark}{null_mark}{default_mark}")

                # 获取索引信息
                result = conn.execute(f"PRAGMA index_list({table})")
                indexes = result.fetchall()

                if indexes:
                    logger.info("  索引:")
                    for idx in indexes:
                        idx_name = idx[1]
                        unique = " (UNIQUE)" if idx[2] else ""
                        logger.info(f"    {idx_name}{unique}")

    except Exception as e:
        logger.error(f"获取表信息失败: {e}")


async def async_init():
    """
    异步初始化数据库
    """
    logger.info("异步初始化数据库...")
    try:
        await init_db()
        logger.info("✓ 异步数据库初始化成功")
        return True
    except Exception as e:
        logger.error(f"✗ 异步数据库初始化失败: {e}")
        return False


def main():
    """
    主函数
    """
    logger.info("🚀 开始初始化文件传输助手数据库")
    logger.info("=" * 50)

    # 1. 创建目录结构
    logger.info("\n1. 创建目录结构")
    create_directories()

    # 2. 检查数据库连接
    logger.info("\n2. 检查数据库连接")
    if not check_database_connection():
        logger.error("数据库连接失败，请检查配置")
        return False

    # 3. 创建数据库表
    logger.info("\n3. 创建数据库表")
    if not create_database_tables():
        logger.error("数据库表创建失败")
        return False

    # 4. 异步初始化
    logger.info("\n4. 异步初始化")
    if not asyncio.run(async_init()):
        logger.error("异步初始化失败")
        return False

    # 5. 显示表结构信息
    show_table_info()

    logger.info("\n" + "=" * 50)
    logger.info("🎉 数据库初始化完成！")
    logger.info("\n数据库文件: files.db")
    logger.info("上传目录: uploads/")
    logger.info("临时目录: temp/")

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)