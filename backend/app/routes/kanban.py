from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth import get_admin
from app.models import Cliente, Obrigacao, Evento
from app.schemas import KanbanOut, KanbanCard, DashboardOut
from app.services.obrigacoes import (
    garantir_todas, situacao, vencimento, rotulo_competencia, coluna_do_card,
    competencia_atual, competencia_anterior,
)
from app.services.serializers import obrigacao_out

router = APIRouter(prefix="/admin", tags=["kanban"], dependencies=[Depends(get_admin)])


@router.get("/kanban", response_model=KanbanOut)
def kanban(competencia: str | None = None, db: Session = Depends(get_db)):
    garantir_todas(db)
    q = db.query(Obrigacao).join(Cliente).filter(Cliente.ativo.is_(True))
    if competencia and competencia != "todas":
        q = q.filter(Obrigacao.competencia == competencia)
    obs = q.order_by(Obrigacao.competencia.desc(), Cliente.nome).all()

    competencias = sorted({c[0] for c in db.query(Obrigacao.competencia).distinct().all()}, reverse=True)

    # última cobrança por (cliente, competência)
    cobrancas = (
        db.query(Evento.cliente_id, Evento.meta, Evento.created_at)
        .filter(Evento.tipo == "cobranca").order_by(Evento.created_at.desc()).all()
    )
    ult: dict[tuple[int, str], datetime] = {}
    cont: dict[tuple[int, str], int] = {}
    for cid, meta, dt in cobrancas:
        comp = (meta or {}).get("competencia")
        if not comp:
            continue
        chave = (cid, comp)
        ult.setdefault(chave, dt)
        cont[chave] = cont.get(chave, 0) + 1

    grupos: dict[tuple[int, str], list[Obrigacao]] = {}
    for o in obs:
        grupos.setdefault((o.cliente_id, o.competencia), []).append(o)

    hoje = datetime.now(timezone.utc).date()
    colunas: dict[str, list[KanbanCard]] = {"atrasado": [], "aguardando": [], "em_analise": [], "concluido": []}
    for (cid, comp), lista in grupos.items():
        c = lista[0].cliente
        outs = [obrigacao_out(o) for o in lista]
        col = coluna_do_card([o.situacao for o in outs])
        venc = vencimento(comp, c.dia_corte)
        colunas[col].append(KanbanCard(
            cliente_id=cid, cliente_nome=c.nome, cliente_slug=c.slug, whatsapp=c.whatsapp,
            competencia=comp, competencia_rotulo=rotulo_competencia(comp), coluna=col,
            vencimento=venc.isoformat(), dias_atraso=max(0, (hoje - venc).days),
            obrigacoes=outs, ultima_cobranca=ult.get((cid, comp)), total_cobrancas=cont.get((cid, comp), 0),
        ))
    # atrasados primeiro os mais antigos
    colunas["atrasado"].sort(key=lambda k: (-k.dias_atraso, k.cliente_nome))
    for k in ("aguardando", "em_analise", "concluido"):
        colunas[k].sort(key=lambda x: (x.competencia, x.cliente_nome), reverse=(k == "concluido"))

    resumo = {k: len(v) for k, v in colunas.items()}
    return KanbanOut(competencias=competencias, colunas=colunas, resumo=resumo)


@router.get("/dashboard", response_model=DashboardOut)
def dashboard(db: Session = Depends(get_db)):
    garantir_todas(db)
    obs = db.query(Obrigacao).join(Cliente).filter(Cliente.ativo.is_(True)).all()
    cont = {"atrasada": 0, "corrigir": 0, "em_analise": 0, "aguardando": 0, "aceita": 0}
    clientes_atraso = set()
    ref = competencia_anterior(competencia_atual())
    aceitas_mes = 0
    for o in obs:
        s = situacao(o)
        cont[s] += 1
        if s in ("atrasada", "corrigir"):
            clientes_atraso.add(o.cliente_id)
        if s == "aceita" and o.competencia == ref:
            aceitas_mes += 1
    nao_lidas = db.query(func.count(Evento.id)).filter(Evento.lida_admin.is_(False)).scalar() or 0
    return DashboardOut(
        clientes_ativos=db.query(func.count(Cliente.id)).filter(Cliente.ativo.is_(True)).scalar() or 0,
        atrasadas=cont["atrasada"] + cont["corrigir"],
        em_analise=cont["em_analise"],
        aguardando=cont["aguardando"],
        aceitas_mes=aceitas_mes,
        clientes_com_atraso=len(clientes_atraso),
        notificacoes=nao_lidas,
    )
