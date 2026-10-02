import csv
import io
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth import get_admin
from app.models import Evento, Documento, Obrigacao
from app.schemas import NotificacoesOut, EventoOut
from app.services.serializers import evento_out

router = APIRouter(prefix="/admin", tags=["notificacoes"], dependencies=[Depends(get_admin)])


@router.get("/notificacoes", response_model=NotificacoesOut)
def notificacoes(db: Session = Depends(get_db)):
    nao_lidas = db.query(func.count(Evento.id)).filter(Evento.lida_admin.is_(False)).scalar() or 0
    itens = (db.query(Evento).filter(Evento.tipo == "upload")
             .order_by(Evento.created_at.desc()).limit(30).all())
    return NotificacoesOut(nao_lidas=nao_lidas, itens=[evento_out(e) for e in itens])


@router.post("/notificacoes/lidas")
def marcar_lidas(ids: list[int] | None = None, db: Session = Depends(get_db)):
    q = db.query(Evento).filter(Evento.lida_admin.is_(False))
    if ids:
        q = q.filter(Evento.id.in_(ids))
    q.update({Evento.lida_admin: True}, synchronize_session=False)
    db.commit()
    return {"ok": True}


def _query_historico(
    db: Session, cliente_id: int | None, tipo_evento: str | None, tipo_documento: str | None,
    competencia: str | None, inicio: str | None, fim: str | None, busca: str | None,
):
    q = db.query(Evento).outerjoin(Documento, Evento.documento_id == Documento.id)
    q = q.outerjoin(Obrigacao, Documento.obrigacao_id == Obrigacao.id)
    if cliente_id:
        q = q.filter(Evento.cliente_id == cliente_id)
    if tipo_evento and tipo_evento != "todos":
        q = q.filter(Evento.tipo == tipo_evento)
    if tipo_documento and tipo_documento != "todos":
        q = q.filter(Obrigacao.tipo == tipo_documento)
    if competencia and competencia != "todas":
        q = q.filter((Obrigacao.competencia == competencia) | (Evento.meta["competencia"].as_string() == competencia))
    if inicio:
        q = q.filter(Evento.created_at >= datetime.fromisoformat(inicio).replace(tzinfo=timezone.utc))
    if fim:
        q = q.filter(Evento.created_at < datetime.fromisoformat(fim).replace(tzinfo=timezone.utc) + timedelta(days=1))
    if busca:
        like = f"%{busca}%"
        q = q.filter((Evento.descricao.ilike(like)) | (Documento.nome_arquivo.ilike(like)))
    return q.order_by(Evento.created_at.desc())


@router.get("/historico", response_model=list[EventoOut])
def historico(
    db: Session = Depends(get_db),
    cliente_id: int | None = None, tipo_evento: str | None = None, tipo_documento: str | None = None,
    competencia: str | None = None, inicio: str | None = None, fim: str | None = None, busca: str | None = None,
    limit: int = Query(200, le=1000), offset: int = 0,
):
    q = _query_historico(db, cliente_id, tipo_evento, tipo_documento, competencia, inicio, fim, busca)
    return [evento_out(e) for e in q.offset(offset).limit(limit).all()]


@router.get("/historico.csv")
def historico_csv(
    db: Session = Depends(get_db),
    cliente_id: int | None = None, tipo_evento: str | None = None, tipo_documento: str | None = None,
    competencia: str | None = None, inicio: str | None = None, fim: str | None = None, busca: str | None = None,
):
    q = _query_historico(db, cliente_id, tipo_evento, tipo_documento, competencia, inicio, fim, busca)
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow(["data_hora", "cliente", "evento", "descricao", "documento", "pendencia", "competencia", "ator", "ip", "sha256"])
    for e in q.limit(20000).all():
        o = evento_out(e)
        w.writerow([
            o.created_at.isoformat(), o.cliente_nome or "", o.tipo_rotulo, o.descricao, o.documento_nome or "",
            o.obrigacao_descricao or "", o.competencia or "", o.ator, o.ip or "", (o.meta or {}).get("sha256", ""),
        ])
    buf.seek(0)
    nome = f"historico_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
    return StreamingResponse(iter(["﻿" + buf.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": f'attachment; filename="{nome}"'})
