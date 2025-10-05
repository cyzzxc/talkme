"""
哈希任务模型
管理异步文件哈希计算任务
"""

from datetime import datetime, UTC
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Index, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base


class HashTask(Base):
    """
    哈希计算任务表
    管理文件的异步哈希计算过程
    """
    __tablename__ = "hash_tasks"

    # 主键
    id = Column(Integer, primary_key=True, index=True)

    # 关联的文件ID
    file_id = Column(Integer, ForeignKey("files.id"), nullable=False, index=True)

    # 任务状态（pending/processing/completed/failed）
    status = Column(String(20), default="pending", nullable=False, index=True)

    # 任务创建时间
    created_at = Column(DateTime, default=func.now(), nullable=False, index=True)

    # 任务开始处理时间
    started_at = Column(DateTime, nullable=True)

    # 任务完成时间
    completed_at = Column(DateTime, nullable=True)

    # 错误信息（失败时记录）
    error_message = Column(Text, nullable=True)

    # 处理进度（0-100）
    progress = Column(Integer, default=0, nullable=False)

    # 重试次数
    retry_count = Column(Integer, default=0, nullable=False)

    # 最大重试次数
    max_retries = Column(Integer, default=3, nullable=False)

    # 任务优先级（数值越小优先级越高）
    priority = Column(Integer, default=100, nullable=False)

    # 工作节点ID（用于分布式处理）
    worker_id = Column(String(100), nullable=True)

    # 最后更新时间
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # 外键关系
    file = relationship("File", foreign_keys=[file_id])

    # 创建复合索引
    __table_args__ = (
        # 用于任务队列处理
        Index("idx_task_status_priority", "status", "priority", "created_at"),
        # 用于任务监控
        Index("idx_task_created_status", "created_at", "status"),
        # 用于清理完成的任务
        Index("idx_task_completed_time", "status", "completed_at"),
        # 用于重试任务查询
        Index("idx_task_retry_status", "retry_count", "status", "updated_at"),
    )

    def __repr__(self):
        return f"<HashTask(id={self.id}, file_id={self.file_id}, status={self.status}, progress={self.progress}%)>"

    def to_dict(self):
        """
        转换为字典格式
        """
        return {
            "id": self.id,
            "file_id": self.file_id,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message,
            "progress": self.progress,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "priority": self.priority,
            "worker_id": self.worker_id,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

    def mark_as_processing(self, worker_id: str = None):
        """
        标记任务为处理中
        """
        self.status = "processing"
        self.started_at = func.now()
        self.worker_id = worker_id

    def mark_as_completed(self):
        """
        标记任务为已完成
        """
        self.status = "completed"
        self.completed_at = func.now()
        self.progress = 100

    def mark_as_failed(self, error_message: str = None):
        """
        标记任务为失败
        """
        self.status = "failed"
        self.completed_at = func.now()
        self.error_message = error_message

    def can_retry(self) -> bool:
        """
        检查任务是否可以重试
        """
        return self.retry_count < self.max_retries and self.status == "failed"

    def increment_retry(self):
        """
        增加重试次数并重置状态
        """
        if self.can_retry():
            self.retry_count += 1
            self.status = "pending"
            self.started_at = None
            self.completed_at = None
            self.error_message = None
            self.progress = 0
            self.worker_id = None

    def update_progress(self, progress: int):
        """
        更新任务进度
        """
        self.progress = max(0, min(100, progress))

    def is_pending(self) -> bool:
        """
        检查任务是否待处理
        """
        return self.status == "pending"

    def is_processing(self) -> bool:
        """
        检查任务是否处理中
        """
        return self.status == "processing"

    def is_completed(self) -> bool:
        """
        检查任务是否已完成
        """
        return self.status == "completed"

    def is_failed(self) -> bool:
        """
        检查任务是否失败
        """
        return self.status == "failed"

    def get_duration(self) -> float:
        """
        获取任务执行时长（秒）
        """
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        elif self.started_at:
            return (datetime.now(UTC) - self.started_at).total_seconds()
        return 0.0

    def get_age(self) -> float:
        """
        获取任务创建时长（秒）
        """
        return (datetime.now(UTC) - self.created_at).total_seconds()

    @classmethod
    def create_task(cls, file_id: int, priority: int = 100):
        """
        创建新的哈希计算任务
        """
        return cls(
            file_id=file_id,
            priority=priority
        )