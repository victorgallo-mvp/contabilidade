from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.models import Usuario

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def hash_senha(senha: str) -> str:
    return pwd_context.hash(senha)


def verificar_senha(senha: str, senha_hash: str) -> bool:
    return pwd_context.verify(senha, senha_hash)


def criar_token(username: str) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    return jwt.encode({"sub": username, "exp": exp}, settings.secret_key, algorithm="HS256")


def get_admin(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> Usuario:
    erro = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sessão inválida")
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        username = payload.get("sub")
    except JWTError:
        raise erro
    user = db.query(Usuario).filter(Usuario.username == username, Usuario.ativo.is_(True)).first()
    if not user:
        raise erro
    return user


def garantir_admin_inicial(db: Session) -> None:
    if db.query(Usuario).count() == 0:
        db.add(Usuario(
            username=settings.admin_username,
            nome=settings.admin_nome,
            senha_hash=hash_senha(settings.admin_password),
        ))
        db.commit()
