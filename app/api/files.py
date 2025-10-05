"""
文件相关API
支持文件上传、下载、去重等功能
"""

import os
import uuid
import hashlib
import mimetypes
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel

from ..database import get_async_db
from ..models import File as FileModel, Message
from ..config import settings
from .auth import require_auth

router = APIRouter(prefix="/api/files", tags=["文件管理"])


class FileUploadResponse(BaseModel):
    """文件上传响应模型"""
    file_id: int
    filename: str
    size: int
    file_type: str
    mime_type: str
    hash_status: str
    is_duplicate: bool = False
    message: str


class FileInfoResponse(BaseModel):
    """文件信息响应模型"""
    id: int
    filename: str
    file_hash: str
    stored_name: str
    file_type: str
    mime_type: str
    size: int
    first_upload_time: str
    reference_count: int
    hash_status: str


class FileListResponse(BaseModel):
    """文件列表响应模型"""
    files: List[FileInfoResponse]
    total: int
    page: int
    page_size: int


async def calculate_file_hash(file_path: str, chunk_size: int = 65536) -> str:
    """
    计算文件SHA256哈希值
    """
    hasher = hashlib.sha256()

    with open(file_path, 'rb') as f:
        while chunk := f.read(chunk_size):
            hasher.update(chunk)

    return hasher.hexdigest()


async def save_uploaded_file(upload_file: UploadFile, file_type: str) -> tuple[str, str]:
    """
    保存上传的文件
    返回 (存储文件名, 文件路径)
    """
    # 生成唯一的存储文件名
    file_extension = ""
    if upload_file.filename and "." in upload_file.filename:
        file_extension = "." + upload_file.filename.rsplit(".", 1)[1].lower()

    stored_name = f"{uuid.uuid4()}{file_extension}"

    # 确定存储目录
    upload_dir = settings.get_upload_path(file_type)
    os.makedirs(upload_dir, exist_ok=True)

    file_path = os.path.join(upload_dir, stored_name)

    # 保存文件
    content = await upload_file.read()
    with open(file_path, 'wb') as f:
        f.write(content)

    return stored_name, file_path


@router.post("/upload", response_model=FileUploadResponse, summary="上传文件")
async def upload_file(
    file: UploadFile = File(...),
    device_id: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_async_db),
    authenticated: bool = Depends(require_auth)
):
    """
    上传文件
    支持文件去重和异步哈希计算
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="文件名不能为空"
        )

    # 检查文件大小
    file_size = 0
    content = await file.read()
    file_size = len(content)

    if file_size > settings.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"文件大小超过限制 ({settings.MAX_FILE_SIZE} 字节)"
        )

    # 检查文件扩展名
    if not settings.is_allowed_extension(file.filename):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不支持的文件类型"
        )

    # 重置文件指针
    await file.seek(0)

    # 确定MIME类型和文件分类
    mime_type = file.content_type or mimetypes.guess_type(file.filename)[0] or "application/octet-stream"
    file_type = FileModel.get_file_type_from_mime(mime_type)

    # 保存文件到临时位置
    temp_stored_name = f"temp_{uuid.uuid4()}.tmp"
    temp_path = os.path.join(settings.TEMP_DIR, temp_stored_name)
    os.makedirs(settings.TEMP_DIR, exist_ok=True)

    with open(temp_path, 'wb') as f:
        f.write(content)

    try:
        # 快速计算哈希值检查去重
        file_hash = await calculate_file_hash(temp_path)

        # 检查是否已存在相同哈希的文件
        existing_file_stmt = select(FileModel).where(
            FileModel.file_hash == file_hash,
            ~FileModel.is_deleted
        )
        result = await db.execute(existing_file_stmt)
        existing_file = result.scalar_one_or_none()

        if existing_file:
            # 文件已存在，增加引用计数
            existing_file.increment_reference()
            await db.commit()

            # 删除临时文件
            os.unlink(temp_path)

            return FileUploadResponse(
                file_id=existing_file.id,
                filename=file.filename,
                size=existing_file.size,
                file_type=existing_file.file_type,
                mime_type=existing_file.mime_type,
                hash_status=existing_file.hash_status,
                is_duplicate=True,
                message="文件已存在，秒传成功"
            )

        # 新文件，保存到正式位置
        stored_name, final_path = await save_uploaded_file(file, file_type)

        # 移动文件从临时位置到正式位置
        os.rename(temp_path, final_path)

        # 创建文件记录
        new_file = FileModel(
            file_hash=file_hash,
            stored_name=stored_name,
            file_type=file_type,
            mime_type=mime_type,
            size=file_size,
            hash_status="completed",  # 已经计算过哈希
            file_path=os.path.join(file_type + "s", stored_name)
        )

        db.add(new_file)
        await db.commit()
        await db.refresh(new_file)

        return FileUploadResponse(
            file_id=new_file.id,
            filename=file.filename,
            size=new_file.size,
            file_type=new_file.file_type,
            mime_type=new_file.mime_type,
            hash_status=new_file.hash_status,
            is_duplicate=False,
            message="文件上传成功"
        )

    except Exception as e:
        # 清理临时文件
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"文件上传失败: {str(e)}"
        )


@router.get("/{file_id}/download", summary="下载文件")
async def download_file(
    file_id: int,
    db: AsyncSession = Depends(get_async_db),
    authenticated: bool = Depends(require_auth)
):
    """
    下载文件
    """
    # 查询文件记录
    stmt = select(FileModel).where(
        FileModel.id == file_id,
        ~FileModel.is_deleted
    )
    result = await db.execute(stmt)
    file_record = result.scalar_one_or_none()

    if not file_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文件不存在"
        )

    # 构建文件路径
    file_path = file_record.get_storage_path(settings.UPLOAD_DIR)

    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文件已被删除"
        )

    # 返回文件
    return FileResponse(
        path=file_path,
        media_type=file_record.mime_type,
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{file_record.stored_name}"
        }
    )


@router.get("/{file_id}/info", response_model=FileInfoResponse, summary="获取文件信息")
async def get_file_info(
    file_id: int,
    db: AsyncSession = Depends(get_async_db),
    authenticated: bool = Depends(require_auth)
):
    """
    获取文件详细信息
    """
    stmt = select(FileModel).where(
        FileModel.id == file_id,
        ~FileModel.is_deleted
    )
    result = await db.execute(stmt)
    file_record = result.scalar_one_or_none()

    if not file_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文件不存在"
        )

    return FileInfoResponse(
        id=file_record.id,
        filename=file_record.stored_name,
        file_hash=file_record.file_hash,
        stored_name=file_record.stored_name,
        file_type=file_record.file_type,
        mime_type=file_record.mime_type,
        size=file_record.size,
        first_upload_time=file_record.first_upload_time.isoformat(),
        reference_count=file_record.reference_count,
        hash_status=file_record.hash_status
    )


@router.get("/", response_model=FileListResponse, summary="获取文件列表")
async def get_files(
    page: int = 1,
    page_size: int = 20,
    file_type: Optional[str] = None,
    db: AsyncSession = Depends(get_async_db),
    authenticated: bool = Depends(require_auth)
):
    """
    获取文件列表
    支持分页和按类型过滤
    """
    # 构建查询
    stmt = select(FileModel).where(~FileModel.is_deleted)

    if file_type:
        stmt = stmt.where(FileModel.file_type == file_type)

    # 计算总数
    count_stmt = select(func.count(FileModel.id)).where(~FileModel.is_deleted)
    if file_type:
        count_stmt = count_stmt.where(FileModel.file_type == file_type)

    total_result = await db.execute(count_stmt)
    total = total_result.scalar()

    # 分页查询
    stmt = stmt.order_by(FileModel.first_upload_time.desc())
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(stmt)
    files = result.scalars().all()

    # 转换为响应格式
    file_list = [
        FileInfoResponse(
            id=f.id,
            filename=f.stored_name,
            file_hash=f.file_hash,
            stored_name=f.stored_name,
            file_type=f.file_type,
            mime_type=f.mime_type,
            size=f.size,
            first_upload_time=f.first_upload_time.isoformat(),
            reference_count=f.reference_count,
            hash_status=f.hash_status
        )
        for f in files
    ]

    return FileListResponse(
        files=file_list,
        total=total,
        page=page,
        page_size=page_size
    )


@router.delete("/{file_id}", summary="删除文件")
async def delete_file(
    file_id: int,
    db: AsyncSession = Depends(get_async_db),
    authenticated: bool = Depends(require_auth)
):
    """
    删除文件（软删除）
    只有当引用计数为0时才会真正删除
    """
    stmt = select(FileModel).where(
        FileModel.id == file_id,
        ~FileModel.is_deleted
    )
    result = await db.execute(stmt)
    file_record = result.scalar_one_or_none()

    if not file_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文件不存在"
        )

    # 检查是否有消息引用此文件
    message_count_stmt = select(func.count(Message.id)).where(
        Message.file_id == file_id,
        ~Message.is_deleted
    )
    count_result = await db.execute(message_count_stmt)
    message_count = count_result.scalar()

    if message_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"文件正在被 {message_count} 条消息引用，无法删除"
        )

    # 软删除文件
    file_record.mark_as_deleted()
    await db.commit()

    return {"message": "文件已删除"}


@router.get("/stats", summary="获取文件统计信息")
async def get_file_stats(
    db: AsyncSession = Depends(get_async_db),
    authenticated: bool = Depends(require_auth)
):
    """
    获取文件存储统计信息
    """
    # 文件总数
    total_files_stmt = select(func.count(FileModel.id)).where(~FileModel.is_deleted)
    total_files_result = await db.execute(total_files_stmt)
    total_files = total_files_result.scalar()

    # 总存储大小
    total_size_stmt = select(func.sum(FileModel.size)).where(~FileModel.is_deleted)
    total_size_result = await db.execute(total_size_stmt)
    total_size = total_size_result.scalar() or 0

    # 按类型统计
    type_stats_stmt = select(
        FileModel.file_type,
        func.count(FileModel.id).label('count'),
        func.sum(FileModel.size).label('size')
    ).where(~FileModel.is_deleted).group_by(FileModel.file_type)

    type_stats_result = await db.execute(type_stats_stmt)
    type_stats = {
        row.file_type: {
            'count': row.count,
            'size': row.size or 0
        }
        for row in type_stats_result
    }

    return {
        "total_files": total_files,
        "total_size": total_size,
        "total_size_formatted": Message.format_file_size(total_size),
        "type_stats": type_stats
    }