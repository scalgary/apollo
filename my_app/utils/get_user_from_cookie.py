
from fastapi import Request
from sqlalchemy.orm import Session
from db_models import User
from utils.security import SECRET_KEY, ALGORITHM
import logging

logger = logging.getLogger(__name__)

def get_user_from_cookie(request: Request, db: Session):
    """Récupère l'utilisateur depuis le cookie JWT"""
    token = request.cookies.get("access_token")
    
    if not token:
        return None
    
    try:
        from jose import jwt
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id_str = payload.get("sub")
        
        if user_id_str:
            user_id = int(user_id_str)
            user = db.query(User).filter(User.id == user_id).first()
            return user
    except Exception as e:
        logger.error(f"Token error: {e}")
    
    return None
