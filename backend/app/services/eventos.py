from fastapi import Request
from sqlalchemy.orm import Session
from app.models import Evento


def _ip(request: Request | None) -> str | None:
    if request is None:
        return None
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()[:64]
    return request.client.host if request.client else None


def registrar(
    db: Session,
    tipo: str,
    descricao: str,
    *,
    ator: str,
    ator_tipo: str,
    cliente_id: int | None = None,
    documento_id: int | None = None,
    obrigacao_id: int | None = None,
    request: Request | None = None,
    meta: dict | None = None,
    notificar: bool = False,
) -> Evento:
    ev = Evento(
        cliente_id=cliente_id,
        documento_id=documento_id,
        obrigacao_id=obrigacao_id,
        tipo=tipo,
        descricao=descricao,
        ator=ator,
        ator_tipo=ator_tipo,
        ip=_ip(request),
        user_agent=(request.headers.get("user-agent", "")[:300] if request else None),
        meta=meta,
        lida_admin=not notificar,
    )
    db.add(ev)
    db.flush()
    return ev
