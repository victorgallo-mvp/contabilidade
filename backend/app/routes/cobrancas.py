from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth import get_admin
from app.models import Usuario, Cliente, Obrigacao
from app.schemas import CobrancaIn, CobrancaOut
from app.services import eventos
from app.services.obrigacoes import situacao, descricao_obrigacao, rotulo_competencia
from app.services.whatsapp import mensagem_cobranca, link_wa

router = APIRouter(prefix="/admin/cobrancas", tags=["cobrancas"])


@router.post("/preview", response_model=CobrancaOut)
def preview(body: CobrancaIn, db: Session = Depends(get_db), admin: Usuario = Depends(get_admin)):
    """Só monta a mensagem, sem registrar. Usado para o admin ler/editar antes de enviar."""
    c, pend = _pendencias(body, db)
    msg = body.mensagem or mensagem_cobranca(c.responsavel or c.nome, body.competencia, pend, c.slug)
    return CobrancaOut(link=link_wa(c.whatsapp, msg), mensagem=msg, evento_id=0)


@router.post("", response_model=CobrancaOut)
def registrar_cobranca(body: CobrancaIn, request: Request, db: Session = Depends(get_db),
                       admin: Usuario = Depends(get_admin)):
    """Registra a cobrança e devolve o link do WhatsApp. O envio é feito pelo admin ao clicar."""
    c, pend = _pendencias(body, db)
    msg = body.mensagem or mensagem_cobranca(c.responsavel or c.nome, body.competencia, pend, c.slug)
    ev = eventos.registrar(
        db, "cobranca",
        f"Cobrança de {rotulo_competencia(body.competencia)} enviada por WhatsApp ({len(pend)} pendência(s))",
        ator=admin.nome, ator_tipo="admin", cliente_id=c.id, request=request,
        meta={"competencia": body.competencia, "pendencias": pend, "mensagem": msg, "canal": "whatsapp",
              "descricao": f"{len(pend)} pendência(s)"},
    )
    db.commit()
    return CobrancaOut(link=link_wa(c.whatsapp, msg), mensagem=msg, evento_id=ev.id)


def _pendencias(body: CobrancaIn, db: Session) -> tuple[Cliente, list[str]]:
    c = db.get(Cliente, body.cliente_id)
    if not c:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    obs = db.query(Obrigacao).filter(Obrigacao.cliente_id == c.id, Obrigacao.competencia == body.competencia).all()
    pend = []
    for o in obs:
        s = situacao(o)
        if s in ("atrasada", "aguardando"):
            pend.append(descricao_obrigacao(o))
        elif s == "corrigir":
            pend.append(f"{descricao_obrigacao(o)} (reenviar: {o.ultima_rejeicao})")
    if not pend:
        raise HTTPException(status_code=400, detail="Não há pendências para cobrar nesta competência")
    return c, pend
