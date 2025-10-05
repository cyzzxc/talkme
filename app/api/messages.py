"""
消息相关API
支持文本和文件消息的发送、接收、删除
"""

from typing import List, Optional
from datetime import datetime, UTC

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload
from pydantic import BaseModel

from ..database import get_async_db
from ..models import Message, File as FileModel
from .auth import require_auth

router = APIRouter(prefix="/api/messages", tags=["消息管理"])


class TextMessageRequest(BaseModel):
    """发送文本消息请求模型"""
    content: str
    device_id: Optional[str] = None


class FileMessageRequest(BaseModel):
    """发送文件消息请求模型"""
    file_id: int
    original_filename: str
    device_id: Optional[str] = None


class MessageResponse(BaseModel):
    """消息响应模型"""
    id: int
    message_type: str
    content: str
    file_id: Optional[int] = None
    timestamp: str
    device_id: Optional[str] = None
    is_deleted: bool
    status: str
    file_info: Optional[dict] = None
    display_content: str


class MessageListResponse(BaseModel):
    """消息列表响应模型"""
    messages: List[MessageResponse]
    total: int
    page: int
    page_size: int


class FileUploadMessageResponse(BaseModel):
    """文件上传并发送消息响应模型"""
    message_id: int
    file_id: int
    filename: str
    is_duplicate: bool
    message: str


@router.post("/text", response_model=MessageResponse, summary="发送文本消息")
async def send_text_message(
    request: TextMessageRequest,
    db: AsyncSession = Depends(get_async_db),
    authenticated: bool = Depends(require_auth)
):
    """
    发送文本消息
    """
    if not request.content.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="消息内容不能为空"
        )

    # 创建文本消息
    message = Message.create_text_message(
        content=request.content,
        device_id=request.device_id
    )

    db.add(message)
    await db.commit()
    await db.refresh(message)

    return MessageResponse(
        id=message.id,
        message_type=message.message_type,
        content=message.content,
        file_id=message.file_id,
        timestamp=message.timestamp.isoformat(),
        device_id=message.device_id,
        is_deleted=message.is_deleted,
        status=message.status,
        display_content=message.get_display_content()
    )


@router.post("/file", response_model=MessageResponse, summary="发送文件消息")
async def send_file_message(
    request: FileMessageRequest,
    db: AsyncSession = Depends(get_async_db),
    authenticated: bool = Depends(require_auth)
):
    """
    发送文件消息
    """
    # 验证文件是否存在
    file_stmt = select(FileModel).where(
        FileModel.id == request.file_id,
        not FileModel.is_deleted
    )
    file_result = await db.execute(file_stmt)
    file_record = file_result.scalar_one_or_none()

    if not file_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文件不存在"
        )

    # 增加文件引用计数
    file_record.increment_reference()

    # 创建文件消息
    message = Message.create_file_message(
        file_id=request.file_id,
        original_filename=request.original_filename,
        device_id=request.device_id
    )

    db.add(message)
    await db.commit()
    await db.refresh(message)

    # 加载文件信息
    await db.refresh(message, ['file'])

    return MessageResponse(
        id=message.id,
        message_type=message.message_type,
        content=message.content,
        file_id=message.file_id,
        timestamp=message.timestamp.isoformat(),
        device_id=message.device_id,
        is_deleted=message.is_deleted,
        status=message.status,
        file_info=message.file.to_dict() if message.file else None,
        display_content=message.get_display_content()
    )


@router.post("/upload-and-send", response_model=FileUploadMessageResponse, summary="上传文件并发送消息")
async def upload_and_send_file(
    file: UploadFile = File(...),
    device_id: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_async_db),
    authenticated: bool = Depends(require_auth)
):
    """
    上传文件并立即发送文件消息
    这是一个便捷接口，组合了文件上传和消息发送
    """
    # 这里需要调用文件上传API的逻辑
    # 为了避免循环依赖，我们重新实现上传逻辑的简化版本
    from .files import upload_file as upload_file_func

    # 上传文件
    upload_response = await upload_file_func(file, device_id, db, authenticated)

    # 发送文件消息
    message_request = FileMessageRequest(
        file_id=upload_response.file_id,
        original_filename=file.filename,
        device_id=device_id
    )

    message_response = await send_file_message(message_request, db, authenticated)

    return FileUploadMessageResponse(
        message_id=message_response.id,
        file_id=upload_response.file_id,
        filename=file.filename,
        is_duplicate=upload_response.is_duplicate,
        message="文件上传并发送成功"
    )


@router.get("/", response_model=MessageListResponse, summary="获取消息列表")
async def get_messages(
    page: int = 1,
    page_size: int = 50,
    message_type: Optional[str] = None,
    device_id: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    db: AsyncSession = Depends(get_async_db),
    authenticated: bool = Depends(require_auth)
):
    """
    获取消息列表
    支持分页、按类型过滤、按设备过滤、按时间范围过滤
    """
    # 构建查询条件
    conditions = [not Message.is_deleted]

    if message_type:
        conditions.append(Message.message_type == message_type)

    if device_id:
        conditions.append(Message.device_id == device_id)

    if start_time:
        conditions.append(Message.timestamp >= start_time)

    if end_time:
        conditions.append(Message.timestamp <= end_time)

    # 构建查询
    stmt = select(Message).where(and_(*conditions))

    # 预加载文件信息
    stmt = stmt.options(selectinload(Message.file))

    # 计算总数
    count_stmt = select(func.count(Message.id)).where(and_(*conditions))
    total_result = await db.execute(count_stmt)
    total = total_result.scalar()

    # 分页查询，按时间倒序
    stmt = stmt.order_by(Message.timestamp.desc())
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(stmt)
    messages = result.scalars().all()

    # 转换为响应格式
    message_list = []
    for msg in messages:
        file_info = None
        if msg.file:
            file_info = {
                "id": msg.file.id,
                "stored_name": msg.file.stored_name,
                "file_type": msg.file.file_type,
                "mime_type": msg.file.mime_type,
                "size": msg.file.size,
                "hash_status": msg.file.hash_status
            }

        message_list.append(MessageResponse(
            id=msg.id,
            message_type=msg.message_type,
            content=msg.content,
            file_id=msg.file_id,
            timestamp=msg.timestamp.isoformat(),
            device_id=msg.device_id,
            is_deleted=msg.is_deleted,
            status=msg.status,
            file_info=file_info,
            display_content=msg.get_display_content()
        ))

    return MessageListResponse(
        messages=message_list,
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/{message_id}", response_model=MessageResponse, summary="获取单条消息")
async def get_message(
    message_id: int,
    db: AsyncSession = Depends(get_async_db),
    authenticated: bool = Depends(require_auth)
):
    """
    获取单条消息详情
    """
    stmt = select(Message).where(
        Message.id == message_id,
        not Message.is_deleted
    ).options(selectinload(Message.file))

    result = await db.execute(stmt)
    message = result.scalar_one_or_none()

    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="消息不存在"
        )

    file_info = None
    if message.file:
        file_info = message.file.to_dict()

    return MessageResponse(
        id=message.id,
        message_type=message.message_type,
        content=message.content,
        file_id=message.file_id,
        timestamp=message.timestamp.isoformat(),
        device_id=message.device_id,
        is_deleted=message.is_deleted,
        status=message.status,
        file_info=file_info,
        display_content=message.get_display_content()
    )


@router.delete("/{message_id}", summary="删除消息")
async def delete_message(
    message_id: int,
    db: AsyncSession = Depends(get_async_db),
    authenticated: bool = Depends(require_auth)
):
    """
    删除消息（软删除）
    如果是文件消息，会减少文件的引用计数
    """
    stmt = select(Message).where(
        Message.id == message_id,
        not Message.is_deleted
    ).options(selectinload(Message.file))

    result = await db.execute(stmt)
    message = result.scalar_one_or_none()

    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="消息不存在"
        )

    # 如果是文件消息，减少文件引用计数
    if message.is_file_message() and message.file:
        message.file.decrement_reference()

    # 软删除消息
    message.mark_as_deleted()

    await db.commit()

    return {"message": "消息已删除"}


@router.put("/{message_id}/status", summary="更新消息状态")
async def update_message_status(
    message_id: int,
    new_status: str,
    db: AsyncSession = Depends(get_async_db),
    authenticated: bool = Depends(require_auth)
):
    """
    更新消息状态
    """
    valid_statuses = ["sent", "delivered", "read"]
    if new_status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"无效的状态值，允许的值: {valid_statuses}"
        )

    stmt = select(Message).where(
        Message.id == message_id,
        not Message.is_deleted
    )
    result = await db.execute(stmt)
    message = result.scalar_one_or_none()

    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="消息不存在"
        )

    message.update_status(new_status)
    await db.commit()

    return {"message": f"消息状态已更新为: {new_status}"}


@router.get("/stats/summary", summary="获取消息统计摘要")
async def get_message_stats(
    db: AsyncSession = Depends(get_async_db),
    authenticated: bool = Depends(require_auth)
):
    """
    获取消息统计信息
    """
    # 总消息数
    total_messages_stmt = select(func.count(Message.id)).where(not Message.is_deleted)
    total_messages_result = await db.execute(total_messages_stmt)
    total_messages = total_messages_result.scalar()

    # 按类型统计
    type_stats_stmt = select(
        Message.message_type,
        func.count(Message.id).label('count')
    ).where(not Message.is_deleted).group_by(Message.message_type)

    type_stats_result = await db.execute(type_stats_stmt)
    type_stats = {row.message_type: row.count for row in type_stats_result}

    # 按设备统计
    device_stats_stmt = select(
        Message.device_id,
        func.count(Message.id).label('count')
    ).where(
        not Message.is_deleted,
        Message.device_id.isnot(None)
    ).group_by(Message.device_id)

    device_stats_result = await db.execute(device_stats_stmt)
    device_stats = {row.device_id: row.count for row in device_stats_result}

    # 今日消息数
    today = datetime.now(UTC).date()
    today_messages_stmt = select(func.count(Message.id)).where(
        not Message.is_deleted,
        func.date(Message.timestamp) == today
    )
    today_messages_result = await db.execute(today_messages_stmt)
    today_messages = today_messages_result.scalar()

    return {
        "total_messages": total_messages,
        "today_messages": today_messages,
        "type_stats": type_stats,
        "device_stats": device_stats
    }