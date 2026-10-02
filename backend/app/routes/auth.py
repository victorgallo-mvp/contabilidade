from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Usuario
from app.auth import verificar_senha, criar_token, get_admin
from app.schemas import LoginOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginOut)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(Usuario).filter(Usuario.username == form.username.strip().lower()).first()
    if not user or not user.ativo or not verificar_senha(form.password, user.senha_hash):
        raise HTTPException(status_code=401, detail="Usuário ou senha incorretos")
    return LoginOut(access_token=criar_token(user.username), nome=user.nome)


@router.get("/me")
def me(user: Usuario = Depends(get_admin)):
    return {"username": user.username, "nome": user.nome}
