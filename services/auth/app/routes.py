from datetime import timedelta

from fastapi import APIRouter, Depends, Query, Response
from hotstar_common.db import utcnow
from hotstar_common.errors import ConflictError, ForbiddenError, NotFoundError, UnauthorizedError
from hotstar_common.pagination import make_page
from hotstar_common.security import CurrentUser, get_current_user, require_admin
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .db import get_db
from .models import RefreshToken, User
from .passwords import hash_password, verify_password
from .schemas import AdminUserUpdate, AuthStats, ChangePasswordIn, LoginIn, RefreshIn, RegisterIn, TokenOut, UserOut
from .service import issue_tokens, revoke_all, rotate

router = APIRouter(prefix="/auth", tags=["auth"])
admin = APIRouter(prefix="/auth/admin", tags=["auth-admin"], dependencies=[Depends(require_admin)])


@router.post("/register", response_model=TokenOut, status_code=201, summary="Register a new viewer account")
def register(body: RegisterIn, db: Session = Depends(get_db)):
    email = body.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise ConflictError("An account with this email already exists", code="email_taken")
    if db.scalar(select(User).where(func.lower(User.username) == body.username.lower())):
        raise ConflictError("This username is already taken", code="username_taken")
    user = User(email=email, username=body.username, password_hash=hash_password(body.password), role="user")
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictError("Email or username already in use", code="duplicate")
    return issue_tokens(db, user)


@router.post("/login", response_model=TokenOut, summary="Login with email and password")
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == body.email.strip().lower()))
    ok = verify_password(body.password, user.password_hash if user else None)
    if not user or not ok:
        raise UnauthorizedError("Invalid email or password", code="invalid_credentials")
    if not user.is_active:
        raise UnauthorizedError("This account has been disabled", code="account_disabled")
    user.last_login_at = utcnow()
    db.commit()
    return issue_tokens(db, user)


@router.post("/refresh", response_model=TokenOut, summary="Rotate refresh token and get a new access token")
def refresh(body: RefreshIn, db: Session = Depends(get_db)):
    return rotate(db, body.refresh_token)


@router.post("/logout", status_code=204, summary="Revoke a refresh token")
def logout(body: RefreshIn, db: Session = Depends(get_db)):
    from hotstar_common.security import decode_token

    try:
        row = db.get(RefreshToken, decode_token(body.refresh_token, "refresh")["jti"])
    except UnauthorizedError:
        row = None
    if row and not row.revoked:
        row.revoked = True
        db.commit()
    return Response(status_code=204)


@router.get("/me", response_model=UserOut, summary="Current account")
def me(cu: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    user = db.get(User, cu.id)
    if not user or not user.is_active:
        raise UnauthorizedError("Account not found or disabled", code="account_disabled")
    return user


@router.post("/change-password", status_code=204, summary="Change password (revokes all sessions)")
def change_password(body: ChangePasswordIn, cu: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    user = db.get(User, cu.id)
    if not user or not verify_password(body.current_password, user.password_hash):
        raise UnauthorizedError("Current password is incorrect", code="invalid_credentials")
    user.password_hash = hash_password(body.new_password)
    db.commit()
    revoke_all(db, user.id)
    return Response(status_code=204)


@admin.get("/users", summary="List users")
def list_users(
    q: str | None = Query(None, max_length=100),
    role: str | None = Query(None, pattern="^(user|admin)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    stmt = select(User)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(User.email.like(like), User.username.like(like)))
    if role:
        stmt = stmt.where(User.role == role)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.order_by(User.id.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    return make_page([UserOut.model_validate(r) for r in rows], total, page, page_size)


@admin.patch("/users/{user_id}", response_model=UserOut, summary="Change a user's role or active flag")
def update_user(user_id: int, body: AdminUserUpdate, cu: CurrentUser = Depends(require_admin), db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise NotFoundError("User not found")
    if user.id == cu.id and (body.role not in (None, user.role) or body.is_active is False):
        raise ForbiddenError("You cannot demote or deactivate your own account", code="self_modification")
    if body.role is not None:
        user.role = body.role
    if body.is_active is not None:
        user.is_active = body.is_active
    db.commit()
    if body.is_active is False:
        revoke_all(db, user.id)
    return user


@admin.delete("/users/{user_id}", status_code=204, summary="Delete a user")
def delete_user(user_id: int, cu: CurrentUser = Depends(require_admin), db: Session = Depends(get_db)):
    if user_id == cu.id:
        raise ForbiddenError("You cannot delete your own account", code="self_modification")
    user = db.get(User, user_id)
    if not user:
        raise NotFoundError("User not found")
    db.query(RefreshToken).filter(RefreshToken.user_id == user_id).delete()
    db.delete(user)
    db.commit()
    return Response(status_code=204)


@admin.get("/stats", response_model=AuthStats, summary="User statistics")
def stats(db: Session = Depends(get_db)):
    week = utcnow() - timedelta(days=7)
    count = lambda *w: db.scalar(select(func.count()).select_from(User).where(*w)) or 0  # noqa: E731
    return AuthStats(total_users=count(), admins=count(User.role == "admin"), active_users=count(User.is_active.is_(True)), new_last_7_days=count(User.created_at >= week))
