import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import engine, Base, SessionLocal
from app import models  # noqa: F401  (registra as tabelas)
from app.auth import garantir_admin_inicial
from app.routes import auth, portal, clientes, documentos, kanban, cobrancas, notificacoes

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        garantir_admin_inicial(db)
        vazio = db.query(models.Cliente).count() == 0
    finally:
        db.close()
    if settings.seed_demo and vazio:
        from seed import main as seed_demo
        seed_demo(reset=False)
    yield


app = FastAPI(title="Contabilidade - Gestão de Documentos", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(portal.router)
app.include_router(clientes.router)
app.include_router(documentos.router)
app.include_router(kanban.router)
app.include_router(cobrancas.router)
app.include_router(notificacoes.router)


@app.get("/health")
def health():
    return {"status": "ok"}
