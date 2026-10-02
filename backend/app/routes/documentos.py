from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth import get_admin
from app.models import Usuario, Documento
from app.schemas import RevisaoItem, RejeitarIn, DocumentoOut
from app.services import eventos, storage
from app.services.obrigacoes import descricao_obrigacao, rotulo_competencia
from app.services.serializers import obrigacao_out, doc_out
from app.services.whatsapp import mensagem_correcao, link_wa

router = APIRouter(prefix="/admin/documentos", tags=["documentos"], dependencies=[Depends(get_admin)])


def _item(d: Documento) -> RevisaoItem:
    return RevisaoItem(
        documento=doc_out(d),
        obrigacao=obrigacao_out(d.obrigacao, com_documentos=False),
        cliente_nome=d.cliente.nome,
        cliente_slug=d.cliente.slug,
    )


@router.get("/revisao", response_model=list[RevisaoItem])
def fila_revisao(db: Session = Depends(get_db)):
    docs = (db.query(Documento).filter(Documento.status == "em_analise")
            .order_by(Documento.created_at.asc()).all())
    return [_item(d) for d in docs]


@router.get("/{documento_id}", response_model=RevisaoItem)
def obter(documento_id: int, db: Session = Depends(get_db)):
    d = db.get(Documento, documento_id)
    if not d:
        raise HTTPException(status_code=404)
    return _item(d)


@router.get("/{documento_id}/download")
def download(documento_id: int, request: Request, db: Session = Depends(get_db), admin: Usuario = Depends(get_admin)):
    d = db.get(Documento, documento_id)
    if not d:
        raise HTTPException(status_code=404)
    data = storage.ler(d.storage_backend, d.storage_ref)
    eventos.registrar(db, "download", f"{admin.nome} abriu {d.nome_arquivo}", ator=admin.nome, ator_tipo="admin",
                      cliente_id=d.cliente_id, documento_id=d.id, obrigacao_id=d.obrigacao_id, request=request)
    db.commit()
    return Response(content=data, media_type=d.mime,
                    headers={"Content-Disposition": f'inline; filename="{d.nome_arquivo}"'})


@router.post("/{documento_id}/aceitar", response_model=DocumentoOut)
def aceitar(documento_id: int, request: Request, db: Session = Depends(get_db), admin: Usuario = Depends(get_admin)):
    d = db.get(Documento, documento_id)
    if not d:
        raise HTTPException(status_code=404)
    if d.status == "aceito":
        return doc_out(d)
    d.status = "aceito"
    d.motivo_rejeicao = None
    d.revisado_em = datetime.now(timezone.utc)
    d.revisado_por = admin.nome
    ob = d.obrigacao
    ob.status = "aceita"
    ob.ultima_rejeicao = None
    eventos.registrar(db, "aceite", f"{descricao_obrigacao(ob)} de {rotulo_competencia(ob.competencia)} aceito: {d.nome_arquivo}",
                      ator=admin.nome, ator_tipo="admin", cliente_id=d.cliente_id, documento_id=d.id,
                      obrigacao_id=ob.id, request=request)
    db.commit()
    db.refresh(d)
    return doc_out(d)


@router.post("/{documento_id}/rejeitar")
def rejeitar(documento_id: int, body: RejeitarIn, request: Request, db: Session = Depends(get_db),
             admin: Usuario = Depends(get_admin)):
    d = db.get(Documento, documento_id)
    if not d:
        raise HTTPException(status_code=404)
    d.status = "rejeitado"
    d.motivo_rejeicao = body.motivo
    d.revisado_em = datetime.now(timezone.utc)
    d.revisado_por = admin.nome
    ob = d.obrigacao
    # se havia outro documento aceito nessa obrigação, ela continua aceita
    outros_aceitos = any(x.status == "aceito" for x in ob.documentos if x.id != d.id)
    if not outros_aceitos:
        ob.status = "pendente"
        ob.ultima_rejeicao = body.motivo
    eventos.registrar(db, "rejeicao", f"{descricao_obrigacao(ob)} de {rotulo_competencia(ob.competencia)} rejeitado: {body.motivo}",
                      ator=admin.nome, ator_tipo="admin", cliente_id=d.cliente_id, documento_id=d.id,
                      obrigacao_id=ob.id, request=request, meta={"motivo": body.motivo})
    db.commit()
    db.refresh(d)
    c = d.cliente
    msg = mensagem_correcao(c.responsavel or c.nome, ob.competencia, descricao_obrigacao(ob), body.motivo, c.slug)
    return {"documento": doc_out(d), "whatsapp_link": link_wa(c.whatsapp, msg), "mensagem": msg}
