from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.db import get_db
from app.core.security import hash_password, verify_password, create_jwt, decode_jwt
from app.models.models import User, ViewerSite, Site, AuthTokenBlacklist
from app.schemas.auth import LoginIn, RegisterIn, TokenOut, UserOut
from app.api.deps import get_current_user, get_current_token, require_roles
from datetime import datetime, timezone

router = APIRouter()


@router.post("/login", response_model=TokenOut)
async def login(data: LoginIn, db: AsyncSession = Depends(get_db)):
    """Authenticate user and return JWT tokens."""
    res = await db.execute(select(User).where(User.email == data.email))
    user = res.scalar_one_or_none()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    site_uids = []
    if user.role == "viewer":
        q = await db.execute(
            select(Site.uid)
            .join(ViewerSite, ViewerSite.site_id == Site.id)
            .where(ViewerSite.user_id == user.id)
        )
        site_uids = [r[0] for r in q.all()]

    access, _, _ = create_jwt(
        user.email, user.role, user.id, site_uids,
        expires_minutes=60, token_type="access"
    )
    refresh, _, _ = create_jwt(
        user.email, user.role, user.id, site_uids,
        expires_minutes=60 * 24 * 7, token_type="refresh"
    )

    return {"access_token": access, "refresh_token": refresh, "token_type": "bearer"}


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)):
    """Get current authenticated user info."""
    site_uids = user._site_uids if user._role == "viewer" else []
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user._role,
        "site_uids": site_uids,
    }


@router.post("/register", dependencies=[Depends(require_roles("admin"))])
async def register_user(payload: RegisterIn, db: AsyncSession = Depends(get_db)):
    """Register new user (admin only)."""
    exists = await db.execute(select(User).where(User.email == payload.email))
    if exists.scalar_one_or_none():
        raise HTTPException(409, "Email sudah digunakan")

    u = User(
        name=payload.name,
        email=payload.email,
        role=payload.role,
        password_hash=hash_password(payload.password),
    )
    db.add(u)
    await db.commit()
    await db.refresh(u)
    return {"ok": True, "id": u.id}


@router.post("/refresh", response_model=TokenOut)
async def refresh(token: str, db: AsyncSession = Depends(get_db)):
    """Refresh access token using refresh token. Old refresh token is rotated (blacklisted)."""
    payload = decode_jwt(token)
    if payload.get("type") != "refresh":
        raise HTTPException(400, "Not a refresh token")

    jti = payload.get("jti")
    # Blacklist check — reject if this refresh token was already used/revoked
    bl = await db.execute(select(AuthTokenBlacklist).where(AuthTokenBlacklist.jti == jti))
    if bl.scalar_one_or_none():
        raise HTTPException(status_code=401, detail="Token sudah tidak berlaku")

    user_id = payload.get("user_id")
    res = await db.execute(select(User).where(User.id == user_id))
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(401, "User not found")

    # Blacklist old refresh token (token rotation)
    exp = payload.get("exp")
    if jti and exp:
        db.add(AuthTokenBlacklist(
            jti=jti,
            user_id=user_id,
            expires_at=datetime.fromtimestamp(exp, tz=timezone.utc),
            reason="rotated",
        ))
        await db.commit()

    site_uids = payload.get("site_uids", [])
    access, _, _ = create_jwt(
        user.email, user.role, user.id, site_uids,
        expires_minutes=60, token_type="access"
    )
    refresh_t, _, _ = create_jwt(
        user.email, user.role, user.id, site_uids,
        expires_minutes=60 * 24 * 7, token_type="refresh"
    )
    return {"access_token": access, "refresh_token": refresh_t, "token_type": "bearer"}


@router.patch("/profile")
async def update_profile(
    payload: dict,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update own name."""
    if "name" in payload and payload["name"]:
        user.name = payload["name"]
        await db.commit()
    return {"ok": True, "name": user.name}


@router.post("/change-password")
async def change_password(
    payload: dict,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Change own password (requires current password verification)."""
    current = payload.get("current_password", "")
    new_pw = payload.get("new_password", "")

    if not verify_password(current, user.password_hash):
        raise HTTPException(400, "Password saat ini salah")

    if len(new_pw) < 8:
        raise HTTPException(400, "Password baru minimal 8 karakter")

    import re
    if not re.search(r'[A-Z]', new_pw):
        raise HTTPException(400, "Password baru harus mengandung huruf kapital")
    if not re.search(r'[0-9]', new_pw):
        raise HTTPException(400, "Password baru harus mengandung angka")

    user.password_hash = hash_password(new_pw)
    await db.commit()
    return {"ok": True}


@router.post("/logout")
async def logout(
    token: str = Depends(get_current_token),
    db: AsyncSession = Depends(get_db),
):
    """Logout user by blacklisting the current access token."""
    try:
        pl = decode_jwt(token)
        jti = pl.get("jti")
        user_id = pl.get("user_id")
        exp = pl.get("exp")

        if jti and user_id and exp:
            db.add(AuthTokenBlacklist(
                jti=jti,
                user_id=user_id,
                expires_at=datetime.fromtimestamp(exp, tz=timezone.utc),
                reason="logout",
            ))
            await db.commit()
    except Exception:
        pass  # Client is already logged out

    return {"ok": True}
