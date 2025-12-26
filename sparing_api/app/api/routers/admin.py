from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.db import get_db
from app.api.deps import get_current_user, require_roles
from app.models.models import User, Site, ViewerSite

router = APIRouter()

@router.post("/viewer-sites", dependencies=[Depends(require_roles("admin"))])
async def assign_viewer(payload: dict, db: AsyncSession = Depends(get_db)):
    # payload: user_id (viewer), site_uid
    user_id = int(payload["user_id"])
    site_uid = payload["site_uid"]
    u = (await db.execute(select(User).where(User.id==user_id))).scalar_one_or_none()
    if not u or u.role != "viewer":
        raise HTTPException(400, "Not a viewer")
    s = (await db.execute(select(Site).where(Site.uid==site_uid))).scalar_one_or_none()
    if not s:
        raise HTTPException(400, "Invalid site_uid")
    exists = (await db.execute(select(ViewerSite).where(ViewerSite.user_id==u.id, ViewerSite.site_id==s.id))).scalar_one_or_none()
    if exists:
        return {"ok": True}
    db.add(ViewerSite(user_id=u.id, site_id=s.id)); await db.commit()
    return {"ok": True}

@router.delete("/viewer-sites", dependencies=[Depends(require_roles("admin"))])
async def unassign_viewer(payload: dict, db: AsyncSession = Depends(get_db)):
    # payload: user_id (viewer), site_uid
    user_id = int(payload["user_id"])
    site_uid = payload["site_uid"]
    u = (await db.execute(select(User).where(User.id==user_id))).scalar_one_or_none()
    if not u or u.role != "viewer":
        raise HTTPException(400, "Not a viewer")
    s = (await db.execute(select(Site).where(Site.uid==site_uid))).scalar_one_or_none()
    if not s:
        raise HTTPException(400, "Invalid site_uid")
    vs = (await db.execute(select(ViewerSite).where(ViewerSite.user_id==u.id, ViewerSite.site_id==s.id))).scalar_one_or_none()
    if not vs:
        return {"ok": True}
    await db.delete(vs); await db.commit()
    return {"ok": True}

# @router.get("/viewer-sites", dependencies=[Depends(require_roles("admin"))])
# async def list_viewer_sites(db: AsyncSession = Depends(get_db)):
#     result = await db.execute(select(User).where(User.role=="viewer"))
#     viewer_sites = result.scalars().all()
#     return {"viewer_sites": [{"user_id": vs.user_id, "site_id": vs.site_id} for vs in viewer_sites]}

# Di backend, ubah endpoint ini
@router.get("/viewer-sites", dependencies=[Depends(require_roles("viewer", "operator", "admin"))])
async def list_viewer_sites(current_user = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    # Jika viewer/operator, filter by user_id mereka
    if current_user.role in ["viewer", "operator"]:
        result = await db.execute(
            select(ViewerSite).where(ViewerSite.user_id == current_user.id)
        )
    else:  # admin
        result = await db.execute(select(ViewerSite))
    
    viewer_sites = result.scalars().all()
    return {"viewer_sites": [{"user_id": vs.user_id, "site_id": vs.site_id} for vs in viewer_sites]}


@router.get("/viewers", dependencies=[Depends(require_roles("admin"))])
async def list_viewers(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.role=="viewer"))
    viewers = result.scalars().all()
    return {"viewers": [{"id": v.id,  "email": v.email} for v in viewers]}

@router.get("/users", dependencies=[Depends(require_roles("admin"))])
async def list_users(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User))
    users = result.scalars().all()
    return {"users": [{"id": u.id, "name": u.name, "email": u.email, "role": u.role, "created_at": u.created_at} for u in users]}

@router.post("/users", dependencies=[Depends(require_roles("admin"))])
async def create_user(payload: dict, db: AsyncSession = Depends(get_db)):
    # payload: name, email, password, role
    from app.core.security import hash_password
    name = payload.get("name", "")
    email = payload["email"]
    password = payload["password"]
    role = payload.get("role", "viewer")
    if role not in ["admin", "operator", "viewer"]:
        raise HTTPException(400, "Invalid role")
    existing_user = (await db.execute(select(User).where(User.email==email))).scalar_one_or_none()
    if existing_user:
        raise HTTPException(400, "Email already exists")
    hashed_password = hash_password(password)
    new_user = User(name=name, email=email, password_hash=hashed_password, role=role)
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return {"id": new_user.id, "name": new_user.name, "email": new_user.email, "role": new_user.role}

@router.patch("/users/{user_id}", dependencies=[Depends(require_roles("admin"))])
async def update_user(user_id: int, payload: dict, db: AsyncSession = Depends(get_db)):
    # payload: name (optional), email (optional), password (optional), role (optional)
    from app.core.security import hash_password
    u = (await db.execute(select(User).where(User.id==user_id))).scalar_one_or_none()
    if not u:
        raise HTTPException(404, "User not found")
    if "name" in payload:
        u.name = payload["name"]
    if "email" in payload:
        u.email = payload["email"]
    if "password" in payload:
        u.password_hash = hash_password(payload["password"])
    if "role" in payload:
        role = payload["role"]
        if role not in ["admin", "operator", "viewer"]:
            raise HTTPException(400, "Invalid role")
        u.role = role
    db.add(u)
    await db.commit()
    await db.refresh(u)
    return {"id": u.id, "name": u.name, "email": u.email, "role": u.role}

@router.delete("/users/{user_id}", dependencies=[Depends(require_roles("admin"))])
async def delete_user(user_id: int, db: AsyncSession = Depends(get_db)):
    u = (await db.execute(select(User).where(User.id==user_id))).scalar_one_or_none()
    if not u:
        raise HTTPException(404, "User not found")
    await db.delete(u)
    await db.commit()
    return {"ok": True}
    


