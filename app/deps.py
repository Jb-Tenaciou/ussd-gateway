import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AuditLog, Role, User
from app.security import decode_token

bearer = HTTPBearer(auto_error=False)


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)
) -> User:
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Authentification requise")
    try:
        payload = decode_token(creds.credentials)
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Jeton invalide ou expiré") from None
    user = db.get(User, int(payload["sub"]))
    if not user or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Utilisateur inactif ou inconnu")
    return user


def require_roles(*roles: Role):
    allowed = {r.value for r in roles}

    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Accès refusé pour ce rôle")
        return user

    return checker


def audit(db: Session, actor: User | None, action: str, rtype: str, rid, result: str = "OK") -> None:
    """Ne jamais y mettre de mot de passe, PIN ou secret."""
    db.add(AuditLog(actor_user_id=actor.id if actor else None, action=action,
                    resource_type=rtype, resource_id=str(rid) if rid is not None else None, result=result))
    db.commit()


staff = require_roles(Role.ADMIN, Role.OPERATOR)
admin_only = require_roles(Role.ADMIN)
