from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError

from core.jwt import decode_token
from models.users import AuthRole
import traceback

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = decode_token(token)
        user_id_raw = payload.get("sub")
        role: str | None = payload.get("role")

        if user_id_raw is None or role is None:
            raise HTTPException(status_code=401, detail="Invalid token")

        try:
            user_id = int(user_id_raw)
        except (TypeError, ValueError):
            raise HTTPException(status_code=401, detail="Invalid token")

        return {
            "user_id": user_id,
            "role": role
        }

    except JWTError:
        print("JWTError encountered while decoding token")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token validation failed",
            headers={"WWW-Authenticate": "Bearer"},
        )


def require_roles(*allowed_roles: AuthRole):
    def _checker(current_user: dict = Depends(get_current_user)):
        role = current_user.get("role")
        if role not in {r.value for r in allowed_roles}:
            raise HTTPException(status_code=403, detail="Not authorized")
        return current_user

    return _checker
