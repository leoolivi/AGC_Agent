"""Folders API — upload structure, list, update, and delete folders."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, require_owner
from app.db.models import Folder, Document

router = APIRouter(prefix="/folders", tags=["folders"])


class FolderCreate(BaseModel):
    name: str
    parent_id: str | None = None


class FolderUpdate(BaseModel):
    name: str | None = None
    parent_id: str | None = None


class FolderResponse(BaseModel):
    id: str
    user_id: str
    name: str
    parent_id: str | None
    created_at: str

    model_config = {"from_attributes": True}


async def _has_cycle(session: AsyncSession, folder_id: uuid.UUID, target_parent_id: uuid.UUID) -> bool:
    """Check if setting target_parent_id as parent of folder_id creates a cycle."""
    if folder_id == target_parent_id:
        return True
    current_id = target_parent_id
    while current_id is not None:
        res = await session.execute(
            select(Folder.parent_id).where(Folder.id == current_id)
        )
        parent = res.scalar_one_or_none()
        if parent == folder_id:
            return True
        current_id = parent
    return False


@router.post("", response_model=FolderResponse, status_code=status.HTTP_201_CREATED)
async def create_folder(
    body: FolderCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> Folder:
    user_uuid = uuid.UUID(user["sub"])
    
    parent_uuid = None
    if body.parent_id:
        try:
            parent_uuid = uuid.UUID(body.parent_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid parent_id UUID format")
        
        parent = await db.get(Folder, parent_uuid)
        if parent is None:
            raise HTTPException(status_code=404, detail="Parent folder not found")
        require_owner(str(parent.user_id), user)

    # Prevent duplicate folder names in the same folder level for this user
    existing_query = select(Folder).where(
        Folder.user_id == user_uuid,
        Folder.parent_id == parent_uuid,
        Folder.name == body.name
    )
    existing_res = await db.execute(existing_query)
    if existing_res.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"A folder named '{body.name}' already exists in this directory"
        )

    folder = Folder(
        user_id=user_uuid,
        name=body.name,
        parent_id=parent_uuid
    )
    db.add(folder)
    await db.commit()
    await db.refresh(folder)
    return folder


@router.get("", response_model=list[FolderResponse])
async def list_folders(
    parent_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> list[Folder]:
    user_uuid = uuid.UUID(user["sub"])
    
    query = select(Folder).where(Folder.user_id == user_uuid)
    if parent_id == "root":
        query = query.where(Folder.parent_id == None)
    elif parent_id is not None:
        try:
            parent_uuid = uuid.UUID(parent_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid parent_id UUID format")
        query = query.where(Folder.parent_id == parent_uuid)
        
    result = await db.execute(query.order_by(Folder.name.asc()))
    return list(result.scalars().all())


@router.patch("/{folder_id}", response_model=FolderResponse)
async def update_folder(
    folder_id: str,
    body: FolderUpdate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> Folder:
    folder_uuid = uuid.UUID(folder_id)
    folder = await db.get(Folder, folder_uuid)
    if folder is None:
        raise HTTPException(status_code=404, detail="Folder not found")
    require_owner(str(folder.user_id), user)

    if body.name is not None:
        folder.name = body.name

    if body.parent_id is not None:
        if body.parent_id == "root":
            folder.parent_id = None
        else:
            try:
                parent_uuid = uuid.UUID(body.parent_id)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid parent_id UUID format")
            
            parent = await db.get(Folder, parent_uuid)
            if parent is None:
                raise HTTPException(status_code=404, detail="Parent folder not found")
            require_owner(str(parent.user_id), user)
            
            # Prevent self-referencing and cycles
            if await _has_cycle(db, folder_uuid, parent_uuid):
                raise HTTPException(
                    status_code=400,
                    detail="Cannot move folder: target destination creates a circular dependency"
                )
            folder.parent_id = parent_uuid

    await db.commit()
    await db.refresh(folder)
    return folder


@router.get("/{folder_id}", response_model=FolderResponse)
async def get_folder(
    folder_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> Folder:
    folder = await db.get(Folder, uuid.UUID(folder_id))
    if folder is None:
        raise HTTPException(status_code=404, detail="Folder not found")
    require_owner(str(folder.user_id), user)
    return folder


@router.delete("/{folder_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_folder(
    folder_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    folder = await db.get(Folder, uuid.UUID(folder_id))
    if folder is None:
        raise HTTPException(status_code=404, detail="Folder not found")
    require_owner(str(folder.user_id), user)
    
    await db.delete(folder)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
