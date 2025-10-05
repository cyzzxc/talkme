"""
消息模型
支持文本和文件消息的统一管理
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Index, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base


class Message(Base):
    """
    消息表
    存储聊天消息，支持文本和文件类型
    """
    __tablename__ = "messages"

    # 主键
    id = Column(Integer, primary_key=True, index=True)

    # 消息类型（text/file）
    message_type = Column(String(20), nullable=False, index=True)

    # 消息内容
    # 对于文本消息：存储文本内容
    # 对于文件消息：存储原始文件名
    content = Column(Text, nullable=True)

    # 关联的文件ID（仅文件消息使用）
    file_id = Column(Integer, ForeignKey("files.id"), nullable=True, index=True)

    # 消息时间戳
    timestamp = Column(DateTime, default=func.now(), nullable=False, index=True)

    # 设备标识（可选）
    device_id = Column(String(100), nullable=True, index=True)

    # 软删除标记
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)

    # 最后更新时间
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # 消息大小（字节，用于统计）
    content_size = Column(Integer, default=0, nullable=False)

    # 消息状态（sent/delivered/read，可扩展）
    status = Column(String(20), default="sent", nullable=False)

    # 外键关系
    file = relationship("File", foreign_keys=[file_id])

    # 创建复合索引
    __table_args__ = (
        # 用于按时间顺序获取消息
        Index("idx_message_time_deleted", "timestamp", "is_deleted"),
        # 用于按设备查询消息
        Index("idx_message_device_time", "device_id", "timestamp"),
        # 用于按消息类型查询
        Index("idx_message_type_time", "message_type", "timestamp"),
        # 用于文件消息查询
        Index("idx_message_file_type", "file_id", "message_type"),
    )

    def __repr__(self):
        if self.message_type == "text":
            content_preview = self.content[:50] + "..." if len(self.content or "") > 50 else self.content
            return f"<Message(id={self.id}, type=text, content='{content_preview}')>"
        else:
            return f"<Message(id={self.id}, type=file, file_id={self.file_id}, filename='{self.content}')>"

    def to_dict(self, include_file_info: bool = True):
        """
        转换为字典格式
        """
        result = {
            "id": self.id,
            "message_type": self.message_type,
            "content": self.content,
            "file_id": self.file_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "device_id": self.device_id,
            "is_deleted": self.is_deleted,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "content_size": self.content_size,
            "status": self.status
        }

        # 如果是文件消息且需要包含文件信息
        if include_file_info and self.message_type == "file" and self.file:
            result["file_info"] = {
                "id": self.file.id,
                "file_hash": self.file.file_hash,
                "stored_name": self.file.stored_name,
                "file_type": self.file.file_type,
                "mime_type": self.file.mime_type,
                "size": self.file.size,
                "hash_status": self.file.hash_status
            }

        return result

    @classmethod
    def create_text_message(cls, content: str, device_id: str = None):
        """
        创建文本消息
        """
        return cls(
            message_type="text",
            content=content,
            device_id=device_id,
            content_size=len(content.encode('utf-8')) if content else 0
        )

    @classmethod
    def create_file_message(cls, file_id: int, original_filename: str, device_id: str = None):
        """
        创建文件消息
        """
        return cls(
            message_type="file",
            content=original_filename,
            file_id=file_id,
            device_id=device_id,
            content_size=len(original_filename.encode('utf-8')) if original_filename else 0
        )

    def mark_as_deleted(self):
        """
        标记消息为已删除
        """
        self.is_deleted = True

    def is_text_message(self) -> bool:
        """
        检查是否为文本消息
        """
        return self.message_type == "text"

    def is_file_message(self) -> bool:
        """
        检查是否为文件消息
        """
        return self.message_type == "file"

    def get_display_content(self) -> str:
        """
        获取用于显示的内容
        """
        if self.is_text_message():
            return self.content or ""
        elif self.is_file_message():
            if self.file:
                file_size = self.format_file_size(self.file.size)
                return f"📎 {self.content} ({file_size})"
            else:
                return f"📎 {self.content} (文件已删除)"
        else:
            return ""

    @staticmethod
    def format_file_size(size_bytes: int) -> str:
        """
        格式化文件大小显示
        """
        if size_bytes < 1024:
            return f"{size_bytes}B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f}KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f}MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f}GB"

    def update_status(self, new_status: str):
        """
        更新消息状态
        """
        self.status = new_status