
from fastapi import Request, Depends, HTTPException, status
from sqlalchemy.orm import Session
from db_models import User
from utils.security import SECRET_KEY, ALGORITHM
import logging
from database import get_db  # Importe ta fonction get_db
logger = logging.getLogger(__name__)

# Route Où l'Utilisateur PEUT Être Connecté (Optionnel)
# Exemple: Page d'accueil, page publique
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
# Dans le même fichier que get_user_from_cookie


# Route Où l'Utilisateur DOIT Être Connecté
# Utilise get_current_user (lance une erreur 401 si pas connecté)
def get_current_user_using_from_cookie(
    request: Request,
    db: Session = Depends(get_db)
) -> User:
    """Dépendance FastAPI pour récupérer l'utilisateur connecté"""
    user = get_user_from_cookie(request, db)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    return user





def get_current_user(
    request: Request,
    db: Session = Depends(get_db)
) -> User:
    """Récupère l'utilisateur connecté (requis)"""
    token = request.cookies.get("access_token")
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    try:
        from jose import jwt
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id_str = payload.get("sub")
        
        if user_id_str:
            user_id = int(user_id_str)
            user = db.query(User).filter(User.id == user_id).first()
            
            if user:
                return user
    except Exception as e:
        logger.error(f"Token error: {e}")
    
    # Si on arrive ici, le token est invalide ou l'user n'existe pas
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication"
    )