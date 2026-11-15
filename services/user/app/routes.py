from fastapi import APIRouter, Depends, Response
from hotstar_common.security import CurrentUser, get_current_user
from sqlalchemy.orm import Session

from .db import get_db
from .models import UserProfile
from .schemas import ProfileOut, ProfileUpdate

router = APIRouter(prefix="/users", tags=["users"])


def _out(p: UserProfile, cu: CurrentUser) -> ProfileOut:
    data = ProfileOut.model_validate(p)
    data.email, data.username, data.role = cu.email, cu.username, cu.role
    return data


def _get_or_create(db: Session, cu: CurrentUser) -> UserProfile:
    profile = db.get(UserProfile, cu.id)
    if profile is None:
        profile = UserProfile(user_id=cu.id, display_name=cu.username or f"user{cu.id}")
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


@router.get("/me", response_model=ProfileOut, summary="Get my profile (created on first access)")
def get_me(cu: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    return _out(_get_or_create(db, cu), cu)


@router.put("/me", response_model=ProfileOut, summary="Update my profile")
def update_me(body: ProfileUpdate, cu: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = _get_or_create(db, cu)
    for k, v in body.model_dump().items():
        setattr(profile, k, v)
    db.commit()
    db.refresh(profile)
    return _out(profile, cu)


@router.delete("/me", status_code=204, summary="Delete my profile data")
def delete_me(cu: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = db.get(UserProfile, cu.id)
    if profile:
        db.delete(profile)
        db.commit()
    return Response(status_code=204)
