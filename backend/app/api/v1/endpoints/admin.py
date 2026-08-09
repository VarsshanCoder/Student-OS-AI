from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_
from sqlalchemy.orm import selectinload
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from uuid import uuid4
from app.core.database import get_db
from app.dependencies import get_current_admin_user, RequiresRole
from app.core.security import get_password_hash
from app.models.user import User
from app.models.note import Note
from app.models.document import Document
from app.models.study_plan import StudyPlan, StudyBlock
from app.models.academic_profile import AcademicProfile
from app.models.attendance import AttendanceRecord
from app.models.subject import Subject
from app.models.audit_log import AdminAuditLog
from app.models.connect import UserConnection

router = APIRouter()

class ResetPasswordRequest(BaseModel):
    new_password: str = Field(min_length=6, description="New password for user")

class RoleUpdateRequest(BaseModel):
    role: str = Field(..., description="Role: SUPER_ADMIN, ADMIN, MODERATOR, STUDENT")

async def log_admin_action(
    db: AsyncSession,
    admin_id: str,
    action_type: str,
    target_user_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    req: Optional[Request] = None
):
    try:
        ip = req.client.host if req and req.client else None
        agent = req.headers.get("user-agent") if req else None
        audit = AdminAuditLog(
            id=str(uuid4()),
            admin_id=str(admin_id),
            action_type=action_type,
            target_user_id=str(target_user_id) if target_user_id else None,
            details_json=details or {},
            ip_address=ip,
            user_agent=agent
        )
        db.add(audit)
        await db.commit()
    except Exception as e:
        print(f"Failed to record audit log: {e}")

@router.get("/stats")
async def get_admin_stats(
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    total_users = (await db.execute(select(func.count(User.id)))).scalar() or 0
    total_notes = (await db.execute(select(func.count(Note.id)))).scalar() or 0
    total_pdfs = (await db.execute(select(func.count(Document.id)))).scalar() or 0
    total_study_plans = (await db.execute(select(func.count(StudyPlan.id)))).scalar() or 0
    total_subjects = (await db.execute(select(func.count(Subject.id)))).scalar() or 0

    return {
        "total_users": total_users,
        "total_notes": total_notes,
        "total_pdfs": total_pdfs,
        "total_study_plans": total_study_plans,
        "total_subjects": total_subjects,
    }

@router.get("/users")
async def get_all_users(
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(
        select(User)
        .options(selectinload(User.academic_profiles))
        .order_by(User.created_at.desc())
    )
    users = res.scalars().all()

    user_list = []
    for u in users:
        notes_cnt = (await db.execute(select(func.count(Note.id)).where(Note.user_id == u.id))).scalar() or 0
        pdfs_cnt = (await db.execute(select(func.count(Document.id)).where(Document.user_id == u.id))).scalar() or 0
        plans_cnt = (await db.execute(select(func.count(StudyPlan.id)).where(StudyPlan.user_id == u.id))).scalar() or 0
        
        prof = u.academic_profiles[0] if u.academic_profiles else None
        
        user_list.append({
            "id": u.id,
            "email": u.email,
            "full_name": u.full_name,
            "is_admin": u.is_admin,
            "role": getattr(u, "role", "STUDENT"),
            "is_active": u.is_active,
            "subscription_tier": u.subscription_tier,
            "onboarding_completed": u.onboarding_completed,
            "institution_name": prof.institution_name if prof else None,
            "education_level": prof.education_level if prof else None,
            "notes_count": notes_cnt,
            "pdfs_count": pdfs_cnt,
            "study_plans_count": plans_cnt,
            "created_at": u.created_at,
            "last_login_at": u.last_login_at,
        })

    return user_list

@router.get("/users/{user_id}/inspect")
async def inspect_user_full_data(
    user_id: str,
    request: Request,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(
        select(User)
        .options(
            selectinload(User.academic_profiles),
            selectinload(User.notes),
            selectinload(User.study_plans).selectinload(StudyPlan.blocks),
            selectinload(User.attendance_records)
        )
        .where(User.id == user_id)
    )
    target_user = res.scalars().first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    pdf_res = await db.execute(select(Document).where(Document.user_id == user_id))
    user_pdfs = pdf_res.scalars().all()

    subj_res = await db.execute(select(Subject).where(Subject.user_id == user_id))
    user_subjs = [s.name for s in subj_res.scalars().all()]

    conn_res = await db.execute(
        select(UserConnection)
        .where(or_(UserConnection.requester_id == user_id, UserConnection.addressee_id == user_id))
    )
    connections_cnt = len(conn_res.scalars().all())

    prof = target_user.academic_profiles[0] if target_user.academic_profiles else None

    # Log audit entry
    await log_admin_action(db, admin_user.id, "USER_VIEWED", user_id, {"email": target_user.email}, request)

    return {
        "user_info": {
            "id": target_user.id,
            "email": target_user.email,
            "full_name": target_user.full_name,
            "is_admin": target_user.is_admin,
            "role": getattr(target_user, "role", "STUDENT"),
            "is_active": target_user.is_active,
            "subscription_tier": target_user.subscription_tier,
            "created_at": target_user.created_at,
            "last_login_at": target_user.last_login_at,
            "onboarding_completed": target_user.onboarding_completed,
            "institution_name": prof.institution_name if prof else None,
            "education_level": prof.education_level if prof else None,
            "field": prof.field if prof else None,
            "specialization": prof.specialization if prof else None,
            "subjects": user_subjs,
            "connections_count": connections_cnt,
        },
        "notes": [
            {
                "id": n.id,
                "title": n.title,
                "content": n.content,
                "source": n.source,
                "word_count": n.word_count,
                "created_at": n.created_at,
            }
            for n in target_user.notes
        ],
        "pdfs": [
            {
                "id": p.id,
                "filename": p.filename,
                "page_count": p.page_count,
                "file_size": p.file_size,
                "created_at": p.created_at,
            }
            for p in user_pdfs
        ],
        "study_plans": [
            {
                "id": sp.id,
                "title": sp.title,
                "start_date": sp.start_date,
                "end_date": sp.end_date,
                "blocks_count": len(sp.blocks),
            }
            for sp in target_user.study_plans
        ],
    }

@router.patch("/users/{user_id}/suspend")
async def suspend_user_account(
    user_id: str,
    request: Request,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    if str(admin_user.id) == user_id:
        raise HTTPException(status_code=400, detail="Cannot suspend your own account")

    res = await db.execute(select(User).where(User.id == user_id))
    target_user = res.scalars().first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    target_user.is_active = False
    await db.commit()

    await log_admin_action(db, admin_user.id, "USER_SUSPENDED", user_id, {"email": target_user.email}, request)
    return {"message": f"Account {target_user.email} suspended successfully"}

@router.patch("/users/{user_id}/restore")
async def restore_user_account(
    user_id: str,
    request: Request,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(select(User).where(User.id == user_id))
    target_user = res.scalars().first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    target_user.is_active = True
    await db.commit()

    await log_admin_action(db, admin_user.id, "USER_RESTORED", user_id, {"email": target_user.email}, request)
    return {"message": f"Account {target_user.email} restored successfully"}

@router.patch("/users/{user_id}/role")
async def update_user_role(
    user_id: str,
    req: RoleUpdateRequest,
    request: Request,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    if req.role not in ["SUPER_ADMIN", "ADMIN", "MODERATOR", "STUDENT"]:
        raise HTTPException(status_code=400, detail="Invalid role specified")

    res = await db.execute(select(User).where(User.id == user_id))
    target_user = res.scalars().first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    old_role = getattr(target_user, "role", "STUDENT")
    target_user.role = req.role
    target_user.is_admin = (req.role in ["SUPER_ADMIN", "ADMIN"])
    await db.commit()

    await log_admin_action(db, admin_user.id, "ROLE_CHANGED", user_id, {"old_role": old_role, "new_role": req.role}, request)
    return {"message": f"Role for {target_user.email} updated to {req.role}"}

@router.post("/users/{user_id}/reset-password")
async def reset_user_password_by_admin(
    user_id: str,
    req: ResetPasswordRequest,
    request: Request,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(select(User).where(User.id == user_id))
    target_user = res.scalars().first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    target_user.password_hash = get_password_hash(req.new_password)
    await db.commit()

    await log_admin_action(db, admin_user.id, "USER_PASSWORD_RESET", user_id, {"email": target_user.email}, request)
    return {"message": f"Password for {target_user.email} updated successfully"}

@router.delete("/users/{user_id}")
async def delete_user_by_admin(
    user_id: str,
    request: Request,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    if str(admin_user.id) == user_id:
        raise HTTPException(status_code=400, detail="Cannot delete your own admin account")

    res = await db.execute(select(User).where(User.id == user_id))
    target_user = res.scalars().first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    target_email = target_user.email
    await db.delete(target_user)
    await db.commit()

    await log_admin_action(db, admin_user.id, "USER_DELETED", user_id, {"email": target_email}, request)
    return {"message": f"User {target_email} and all associated data deleted successfully"}

@router.get("/audit-logs")
async def get_platform_audit_logs(
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(
        select(AdminAuditLog)
        .order_by(AdminAuditLog.created_at.desc())
        .limit(100)
    )
    logs = res.scalars().all()
    out = []
    for l in logs:
        adm_res = await db.execute(select(User).where(User.id == l.admin_id))
        adm = adm_res.scalars().first()
        out.append({
            "id": l.id,
            "admin_email": adm.email if adm else "System",
            "action_type": l.action_type,
            "target_user_id": l.target_user_id,
            "details": l.details_json,
            "ip_address": l.ip_address,
            "created_at": l.created_at
        })
    return out
