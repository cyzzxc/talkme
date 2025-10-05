"""
文件模型
支持文件去重和引用计数管理
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Index
from sqlalchemy.sql import func
from ..database import Base


class File(Base):
    """
    文件表
    存储文件的元数据信息，支持基于哈希值的去重
    """
    __tablename__ = "files"

    # 主键
    id = Column(Integer, primary_key=True, index=True)

    # 文件哈希值，用于去重（SHA256）
    file_hash = Column(String(64), nullable=False, index=True, unique=True)

    # 存储文件名（UUID格式）
    stored_name = Column(String(255), nullable=False, unique=True)

    # 文件类型分类（image/document/other）
    file_type = Column(String(50), nullable=False, index=True)

    # MIME类型
    mime_type = Column(String(255), nullable=False)

    # 文件大小（字节）
    size = Column(Integer, nullable=False, index=True)

    # 首次上传时间
    first_upload_time = Column(DateTime, default=func.now(), nullable=False)

    # 引用计数（有多少消息引用此文件）
    reference_count = Column(Integer, default=1, nullable=False)

    # 软删除标记
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)

    # 哈希计算状态（pending/completed/failed）
    hash_status = Column(String(20), default="pending", nullable=False, index=True)

    # 文件路径（相对于上传目录）
    file_path = Column(String(500), nullable=True)

    # 最后更新时间
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # 创建复合索引
    __table_args__ = (
        # 用于快速查找可删除的文件
        Index("idx_file_ref_deleted", "reference_count", "is_deleted"),
        # 用于文件类型和大小的查询
        Index("idx_file_type_size", "file_type", "size"),
        # 用于哈希状态查询
        Index("idx_hash_status_created", "hash_status", "first_upload_time"),
    )

    def __repr__(self):
        return f"<File(id={self.id}, hash={self.file_hash[:8]}..., size={self.size}, refs={self.reference_count})>"

    def to_dict(self):
        """
        转换为字典格式
        """
        return {
            "id": self.id,
            "file_hash": self.file_hash,
            "stored_name": self.stored_name,
            "file_type": self.file_type,
            "mime_type": self.mime_type,
            "size": self.size,
            "first_upload_time": self.first_upload_time.isoformat() if self.first_upload_time else None,
            "reference_count": self.reference_count,
            "is_deleted": self.is_deleted,
            "hash_status": self.hash_status,
            "file_path": self.file_path,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

    @classmethod
    def get_file_type_from_mime(cls, mime_type: str) -> str:
        """
        根据MIME类型确定文件分类
        """
        if mime_type.startswith("image/"):
            return "image"
        elif mime_type in [
            "application/pdf",
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/vnd.ms-excel",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.ms-powerpoint",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            "text/plain",
            "text/csv"
        ]:
            return "document"
        else:
            return "other"

    def increment_reference(self):
        """
        增加引用计数
        """
        self.reference_count += 1

    def decrement_reference(self):
        """
        减少引用计数
        """
        if self.reference_count > 0:
            self.reference_count -= 1

    def can_be_deleted(self) -> bool:
        """
        检查文件是否可以被删除
        """
        return self.reference_count <= 0 or self.is_deleted

    def mark_as_deleted(self):
        """
        标记文件为已删除
        """
        self.is_deleted = True

    def get_storage_path(self, upload_dir: str) -> str:
        """
        获取文件的完整存储路径
        """
        import os
        if self.file_path:
            return os.path.join(upload_dir, self.file_path)
        else:
            # 兼容旧的存储方式
            return os.path.join(upload_dir, self.file_type + "s", self.stored_name)