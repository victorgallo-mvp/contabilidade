"""Geração e classificação de obrigações.

Regra de prazo: a competência AAAA-MM vence no dia `dia_corte` do mês seguinte.
Ex.: extrato de 2026-08 com corte 10 vence em 2026-09-10.
"""
from datetime import date, datetime, timezone
from sqlalchemy.orm import Session
from app.models import Cliente, ContaBancaria, Obrigacao, TIPOS_DOCUMENTO


def competencia_atual(hoje: date | None = None) -> str:
    hoje = hoje or datetime.now(timezone.utc).date()
    return f"{hoje.year:04d}-{hoje.month:02d}"


def competencia_anterior(comp: str) -> str:
    ano, mes = map(int, comp.split("-"))
    if mes == 1:
        return f"{ano - 1:04d}-12"
    return f"{ano:04d}-{mes - 1:02d}"


def proxima_competencia(comp: str) -> str:
    ano, mes = map(int, comp.split("-"))
    if mes == 12:
        return f"{ano + 1:04d}-01"
    return f"{ano:04d}-{mes + 1:02d}"


def iter_competencias(inicio: str, fim: str):
    c = inicio
    while c <= fim:
        yield c
        c = proxima_competencia(c)


def vencimento(competencia: str, dia_corte: int) -> date:
    prox = proxima_competencia(competencia)
    ano, mes = map(int, prox.split("-"))
    # protege contra dia 31 em mês curto
    from calendar import monthrange
    dia = min(dia_corte, monthrange(ano, mes)[1])
    return date(ano, mes, dia)


def rotulo_competencia(comp: str) -> str:
    meses = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
    ano, mes = comp.split("-")
    return f"{meses[int(mes) - 1]}/{ano}"


def garantir_obrigacoes(db: Session, cliente: Cliente, ate: str | None = None) -> int:
    """Cria as obrigações faltantes do cliente até a competência `ate` (default: mês anterior ao atual).

    O mês corrente ainda não fechou, então a última competência esperada é a anterior.
    Retorna quantas obrigações foram criadas.
    """
    if not cliente.ativo:
        return 0
    ate = ate or competencia_anterior(competencia_atual())
    if cliente.mes_inicio > ate:
        return 0

    existentes = {
        (o.tipo, o.conta_id, o.competencia)
        for o in db.query(Obrigacao).filter(Obrigacao.cliente_id == cliente.id).all()
    }
    contas_ativas = [c for c in cliente.contas if c.ativa]
    criadas = 0
    for comp in iter_competencias(cliente.mes_inicio, ate):
        for tipo in cliente.tipos_ativos or []:
            if tipo not in TIPOS_DOCUMENTO:
                continue
            if tipo == "extrato":
                for conta in contas_ativas:
                    chave = (tipo, conta.id, comp)
                    if chave not in existentes:
                        db.add(Obrigacao(cliente_id=cliente.id, tipo=tipo, conta_id=conta.id, competencia=comp))
                        existentes.add(chave)
                        criadas += 1
            else:
                chave = (tipo, None, comp)
                if chave not in existentes:
                    db.add(Obrigacao(cliente_id=cliente.id, tipo=tipo, conta_id=None, competencia=comp))
                    existentes.add(chave)
                    criadas += 1
    if criadas:
        db.flush()
    return criadas


def garantir_todas(db: Session) -> int:
    total = 0
    for cliente in db.query(Cliente).filter(Cliente.ativo.is_(True)).all():
        total += garantir_obrigacoes(db, cliente)
    if total:
        db.commit()
    return total


def situacao(ob: Obrigacao, hoje: date | None = None) -> str:
    """Situação derivada: aguardando | atrasada | corrigir | em_analise | aceita."""
    hoje = hoje or datetime.now(timezone.utc).date()
    if ob.status == "aceita":
        return "aceita"
    if ob.status == "em_analise":
        return "em_analise"
    if ob.ultima_rejeicao:
        return "corrigir"
    venc = vencimento(ob.competencia, ob.cliente.dia_corte if ob.cliente else 10)
    return "atrasada" if hoje > venc else "aguardando"


def descricao_obrigacao(ob: Obrigacao) -> str:
    base = TIPOS_DOCUMENTO.get(ob.tipo, ob.tipo)
    if ob.tipo == "extrato" and ob.conta:
        return f"Extrato {ob.conta.rotulo}"
    return base


# prioridade para decidir a coluna do card no kanban
_PRIORIDADE = {"atrasada": 0, "corrigir": 0, "em_analise": 1, "aguardando": 2, "aceita": 3}
_COLUNA = {"atrasada": "atrasado", "corrigir": "atrasado", "em_analise": "em_analise", "aguardando": "aguardando", "aceita": "concluido"}


def coluna_do_card(situacoes: list[str]) -> str:
    if not situacoes:
        return "concluido"
    pior = min(situacoes, key=lambda s: _PRIORIDADE[s])
    return _COLUNA[pior]
