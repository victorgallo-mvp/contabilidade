"""Portal do cliente. Acesso pelo slug fixo, sem login."""
import hashlib
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import Response
from sqlalchemy.orm import Session
from app.database import get_db, SessionLocal
from app.models import Cliente, Obrigacao, Documento, TIPOS_DOCUMENTO
from app.schemas import PortalOut, PortalCompetencia, DocumentoOut
from app.services import eventos, storage, ia
from app.services.obrigacoes import garantir_obrigacoes, rotulo_competencia, vencimento, situacao, descricao_obrigacao
from app.services.serializers import obrigacao_out, doc_out

router = APIRouter(prefix="/portal", tags=["portal"])

MIMES_ACEITOS = {
    "application/pdf", "image/jpeg", "image/png", "image/webp",
    "application/vnd.ms-excel", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "text/csv", "application/octet-stream",
}
TAMANHO_MAX = 25 * 1024 * 1024


def _cliente(slug: str, db: Session) -> Cliente:
    c = db.query(Cliente).filter(Cliente.slug == slug, Cliente.ativo.is_(True)).first()
    if not c:
        raise HTTPException(status_code=404, detail="Link inválido. Confirme com a contabilidade.")
    return c


def _montar_portal(c: Cliente, db: Session) -> PortalOut:
    garantir_obrigacoes(db, c)
    db.commit()
    obs = (
        db.query(Obrigacao).filter(Obrigacao.cliente_id == c.id)
        .order_by(Obrigacao.competencia.desc(), Obrigacao.tipo, Obrigacao.conta_id).all()
    )
    por_comp: dict[str, list[Obrigacao]] = {}
    for o in obs:
        por_comp.setdefault(o.competencia, []).append(o)
    competencias = []
    for comp, lista in por_comp.items():
        outs = [obrigacao_out(o) for o in lista]
        competencias.append(PortalCompetencia(
            competencia=comp,
            rotulo=rotulo_competencia(comp),
            vencimento=vencimento(comp, c.dia_corte).isoformat(),
            obrigacoes=outs,
            completa=all(o.situacao == "aceita" for o in outs),
        ))
    historico = (
        db.query(Documento).filter(Documento.cliente_id == c.id)
        .order_by(Documento.created_at.desc()).limit(200).all()
    )
    return PortalOut(
        cliente_nome=c.nome,
        responsavel=c.responsavel,
        competencias=competencias,
        historico=[doc_out(d) for d in historico],
    )


@router.get("/{slug}", response_model=PortalOut)
def abrir_portal(slug: str, request: Request, db: Session = Depends(get_db)):
    c = _cliente(slug, db)
    eventos.registrar(db, "acesso_portal", "Cliente abriu o portal", ator="cliente", ator_tipo="cliente",
                      cliente_id=c.id, request=request)
    out = _montar_portal(c, db)
    db.commit()
    return out


def processar_ia(documento_id: int) -> None:
    """Roda em background após o upload. Nunca derruba a requisição."""
    db = SessionLocal()
    try:
        d = db.get(Documento, documento_id)
        if not d:
            return
        ob = d.obrigacao
        try:
            data = storage.ler(d.storage_backend, d.storage_ref)
            leitura = ia.analisar(
                data, d.mime, tipo=ob.tipo, competencia=ob.competencia,
                conta_rotulo=ob.conta.rotulo if ob.conta else None,
            )
        except Exception as e:  # noqa: BLE001
            d.ia_status = "erro"
            d.ia_alerta = f"Falha na leitura automática: {type(e).__name__}"
            db.commit()
            return
        if leitura is None:
            d.ia_status = "pulado"
            db.commit()
            return
        d.ia_banco = leitura.banco
        d.ia_periodo_inicio = leitura.periodo_inicio
        d.ia_periodo_fim = leitura.periodo_fim
        d.ia_competencia = leitura.competencia
        d.ia_saldo_inicial = leitura.saldo_inicial
        d.ia_saldo_final = leitura.saldo_final
        d.ia_resumo = leitura.resumo
        alerta = ia.alerta_para(leitura, tipo=ob.tipo, competencia=ob.competencia)
        d.ia_alerta = alerta
        d.ia_status = "alerta" if alerta else "ok"
        eventos.registrar(
            db, "ia_leitura", alerta or leitura.resumo, ator="sistema", ator_tipo="sistema",
            cliente_id=d.cliente_id, documento_id=d.id, obrigacao_id=ob.id,
            meta={"banco": leitura.banco, "competencia": leitura.competencia},
        )
        db.commit()
    finally:
        db.close()


def receber_documento(
    db: Session, *, cliente: Cliente, obrigacao: Obrigacao, arquivo: UploadFile, data: bytes,
    enviado_por: str, enviado_por_nome: str | None, canal: str, request: Request | None,
) -> Documento:
    """Usado pelo portal e pelo upload em nome do cliente feito pelo admin."""
    if len(data) == 0:
        raise HTTPException(status_code=400, detail="Arquivo vazio")
    if len(data) > TAMANHO_MAX:
        raise HTTPException(status_code=400, detail="Arquivo acima de 25 MB")
    mime = arquivo.content_type or "application/octet-stream"
    nome = arquivo.filename or "documento"
    if mime not in MIMES_ACEITOS and not nome.lower().endswith((".pdf", ".jpg", ".jpeg", ".png", ".ofx", ".xls", ".xlsx", ".csv")):
        raise HTTPException(status_code=400, detail="Formato não aceito. Envie PDF, imagem, OFX ou planilha.")
    if nome.lower().endswith(".pdf"):
        mime = "application/pdf"

    salvo = storage.salvar(
        cliente_nome=cliente.nome, competencia=obrigacao.competencia,
        tipo_rotulo=TIPOS_DOCUMENTO.get(obrigacao.tipo, obrigacao.tipo),
        nome_arquivo=nome, data=data, mime=mime,
    )
    d = Documento(
        obrigacao_id=obrigacao.id, cliente_id=cliente.id, nome_arquivo=nome, mime=mime,
        tamanho=len(data), sha256=hashlib.sha256(data).hexdigest(),
        storage_backend=salvo.backend, storage_ref=salvo.ref, drive_link=salvo.link,
        enviado_por=enviado_por, enviado_por_nome=enviado_por_nome, canal=canal, status="em_analise",
    )
    db.add(d)
    obrigacao.status = "em_analise"
    db.flush()
    eventos.registrar(
        db, "upload" if enviado_por == "cliente" else "upload_admin",
        f"{descricao_obrigacao(obrigacao)} de {rotulo_competencia(obrigacao.competencia)}: {nome}",
        ator=enviado_por_nome or "cliente", ator_tipo=enviado_por,
        cliente_id=cliente.id, documento_id=d.id, obrigacao_id=obrigacao.id, request=request,
        meta={"canal": canal, "sha256": d.sha256, "tamanho": len(data)},
        notificar=(enviado_por == "cliente"),
    )
    return d


@router.post("/{slug}/upload", response_model=DocumentoOut)
async def upload(
    slug: str, request: Request, background: BackgroundTasks,
    obrigacao_id: int = Form(...), arquivo: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    c = _cliente(slug, db)
    ob = db.query(Obrigacao).filter(Obrigacao.id == obrigacao_id, Obrigacao.cliente_id == c.id).first()
    if not ob:
        raise HTTPException(status_code=404, detail="Pendência não encontrada")
    if ob.status == "aceita":
        raise HTTPException(status_code=400, detail="Este documento já foi aceito pela contabilidade")
    data = await arquivo.read()
    d = receber_documento(db, cliente=c, obrigacao=ob, arquivo=arquivo, data=data,
                          enviado_por="cliente", enviado_por_nome=None, canal="portal", request=request)
    db.commit()
    db.refresh(d)
    background.add_task(processar_ia, d.id)
    return doc_out(d)


@router.get("/{slug}/documentos/{documento_id}/download")
def download_proprio(slug: str, documento_id: int, request: Request, db: Session = Depends(get_db)):
    c = _cliente(slug, db)
    d = db.query(Documento).filter(Documento.id == documento_id, Documento.cliente_id == c.id).first()
    if not d:
        raise HTTPException(status_code=404)
    data = storage.ler(d.storage_backend, d.storage_ref)
    eventos.registrar(db, "download", f"Cliente baixou {d.nome_arquivo}", ator="cliente", ator_tipo="cliente",
                      cliente_id=c.id, documento_id=d.id, obrigacao_id=d.obrigacao_id, request=request)
    db.commit()
    return Response(content=data, media_type=d.mime,
                    headers={"Content-Disposition": f'inline; filename="{d.nome_arquivo}"'})
