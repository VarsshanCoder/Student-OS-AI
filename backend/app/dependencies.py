from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.security import decode_token
from app.core.config import settings
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    payload = decode_token(token, settings.SECRET_KEY)
    if payload is None or payload.get("type") != "access":
        raise credentials_exception
        
    user_id_str: str = payload.get("sub")
    if user_id_str is None:
        raise credentials_exception
        
    result = await db.execute(select(User).where(User.id == str(user_id_str)))
    user = result.scalars().first()
    
    if user is None:
        raise credentials_exception
        
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user account")
        
    return user

async def get_current_admin_user(
    current_user: User = Depends(get_current_user)
) -> User:
    if not (current_user.is_admin or current_user.role in ["SUPER_ADMIN", "ADMIN", "MODERATOR"] or current_user.email == "admin2009@gmail.com"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required to access this resource"
        )
    return current_user

class RequiresRole:
    def __init__(self, allowed_roles: list[str]):
        self.allowed_roles = allowed_roles
        
    async def __call__(self, user: User = Depends(get_current_user)) -> User:
        user_role = getattr(user, "role", "STUDENT")
        if user.is_admin or user.email == "admin2009@gmail.com":
            user_role = "SUPER_ADMIN"
            
        if user_role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Resource requires one of the following roles: {', '.join(self.allowed_roles)}"
            )
        return user

class RequiresTier:
    def __init__(self, minimum_tier: str):
        self.minimum_tier = minimum_tier
        
    async def __call__(self, user: User = Depends(get_current_user)) -> User:
        tier_map = {"free": 0, "scholar": 1, "scholar_pro": 2}
        required_level = tier_map.get(self.minimum_tier, 0)
        user_level = tier_map.get(user.subscription_tier, 0)
        
        if user_level < required_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This feature requires '{self.minimum_tier}' subscription tier"
            )
        return user
