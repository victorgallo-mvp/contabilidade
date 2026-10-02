import secrets
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth import get_admin
from app.models import Usuario, Cliente, ContaBancaria, Obrigacao, TIPOS_DOCUMENTO
from app.schemas import ClienteIn, ClienteOut, ContaIn, ContaOut, ObrigacaoOut, DocumentoOut
from app.services import eventos
from app.services.obrigacoes import garantir_obrigacoes, situacao
from app.services.serializers import obrigacao_out, doc_out
from app.services.whatsapp import link_portal
from app.routes.portal import receber_documento, processar_ia

router = APIRouter(prefix="/admin/clientes", tags=["clientes"], dependencies=[Depends(get_admin)])


def _slug_novo(db: Session) -> str:
    while True:
        s = secrets.token_urlsafe(6).replace("-", "x").replace("_", "y").lower()[:8]
        if not db.query(Cliente).filter(Cliente.slug == s).first():
            return s


def _out(c: Cliente, resumo: dict | None = None) -> ClienteOut:
    o = ClienteOut(
        id=c.id, nome=c.nome, cnpj=c.cnpj, responsavel=c.responsavel, whatsapp=c.whatsapp, email=c.email,
        mes_inicio=c.mes_inicio, dia_corte=c.dia_corte, tipos_ativos=c.tipos_ativos or [],
        observacoes=c.observacoes, ativo=c.ativo, slug=c.slug, link_portal=link_portal(c.slug),
        contas=[ContaOut(id=k.id, banco=k.banco, apelido=k.apelido, ativa=k.ativa, rotulo=k.rotulo) for k in c.contas],
        created_at=c.created_at,
    )
    if resumo:
        o.pendentes = resumo.get("pendentes", 0)
        o.atrasadas = resumo.get("atrasadas", 0)
        o.em_analise = resumo.get("em_analise", 0)
    return o


def _validar_tipos(tipos: list[str]) -> list[str]:
    invalidos = [t for t in tipos if t not in TIPOS_DOCUMENTO]
    if invalidos:
        raise HTTPException(status_code=400, detail=f"Tipo de documento inválido: {', '.join(invalidos)}")
    return tipos


@router.get("", response_model=list[ClienteOut])
def listar(db: Session = Depends(get_db), incluir_inativos: bool = False):
    q = db.query(Cliente)
    if not incluir_inativos:
        q = q.filter(Cliente.ativo.is_(True))
    clientes = q.order_by(Cliente.nome).all()
    for c in clientes:
        garantir_obrigacoes(db, c)
    db.commit()
    saida = []
    for c in clientes:
        resumo = {"pendentes": 0, "atrasadas": 0, "em_analise": 0}
        for ob in c.obrigacoes:
            s = situacao(ob)
            if s in ("atrasada", "corrigir"):
                resumo["atrasadas"] += 1
                resumo["pendentes"] += 1
            elif s == "aguardando":
                resumo["pendentes"] += 1
            elif s == "em_analise":
                resumo["em_analise"] += 1
        saida.append(_out(c, resumo))
    return saida


@router.post("", response_model=ClienteOut, status_code=201)
def criar(body: ClienteIn, request: Request, db: Session = Depends(get_db), admin: Usuario = Depends(get_admin)):
    _validar_tipos(body.tipos_ativos)
    c = Cliente(**body.model_dump(), slug=_slug_novo(db))
    db.add(c)
    db.flush()
    eventos.registrar(db, "cliente_criado", f"Cliente {c.nome} cadastrado", ator=admin.nome, ator_tipo="admin",
                      cliente_id=c.id, request=request)
    garantir_obrigacoes(db, c)
    db.commit()
    db.refresh(c)
    return _out(c)


@router.get("/{cliente_id}", response_model=ClienteOut)
def obter(cliente_id: int, db: Session = Depends(get_db)):
    c = db.get(Cliente, cliente_id)
    if not c:
        raise HTTPException(status_code=404)
    return _out(c)


@router.put("/{cliente_id}", response_model=ClienteOut)
def atualizar(cliente_id: int, body: ClienteIn, request: Request, db: Session = Depends(get_db),
              admin: Usuario = Depends(get_admin)):
    c = db.get(Cliente, cliente_id)
    if not c:
        raise HTTPException(status_code=404)
    _validar_tipos(body.tipos_ativos)
    antes = {"tipos_ativos": c.tipos_ativos, "mes_inicio": c.mes_inicio, "dia_corte": c.dia_corte, "ativo": c.ativo}
    for k, v in body.model_dump().items():
        setattr(c, k, v)
    db.flush()
    eventos.registrar(db, "cliente_alterado", f"Cadastro de {c.nome} alterado", ator=admin.nome, ator_tipo="admin",
                      cliente_id=c.id, request=request, meta={"antes": antes})
    garantir_obrigacoes(db, c)
    db.commit()
    db.refresh(c)
    return _out(c)


@router.post("/{cliente_id}/contas", response_model=ContaOut, status_code=201)
def criar_conta(cliente_id: int, body: ContaIn, request: Request, db: Session = Depends(get_db),
                admin: Usuario = Depends(get_admin)):
    c = db.get(Cliente, cliente_id)
    if not c:
        raise HTTPException(status_code=404)
    k = ContaBancaria(cliente_id=c.id, **body.model_dump())
    db.add(k)
    db.flush()
    eventos.registrar(db, "cliente_alterado", f"Conta {k.rotulo} adicionada", ator=admin.nome, ator_tipo="admin",
                      cliente_id=c.id, request=request)
    db.refresh(c)
    garantir_obrigacoes(db, c)
    db.commit()
    return ContaOut(id=k.id, banco=k.banco, apelido=k.apelido, ativa=k.ativa, rotulo=k.rotulo)


@router.put("/{cliente_id}/contas/{conta_id}", response_model=ContaOut)
def atualizar_conta(cliente_id: int, conta_id: int, body: ContaIn, request: Request,
                    db: Session = Depends(get_db), admin: Usuario = Depends(get_admin)):
    k = db.query(ContaBancaria).filter(ContaBancaria.id == conta_id, ContaBancaria.cliente_id == cliente_id).first()
    if not k:
        raise HTTPException(status_code=404)
    for f, v in body.model_dump().items():
        setattr(k, f, v)
    eventos.registrar(db, "cliente_alterado", f"Conta {k.rotulo} alterada", ator=admin.nome, ator_tipo="admin",
                      cliente_id=cliente_id, request=request)
    db.commit()
    return ContaOut(id=k.id, banco=k.banco, apelido=k.apelido, ativa=k.ativa, rotulo=k.rotulo)


@router.delete("/{cliente_id}/contas/{conta_id}", status_code=204)
def remover_conta(cliente_id: int, conta_id: int, request: Request, db: Session = Depends(get_db),
                  admin: Usuario = Depends(get_admin)):
    k = db.query(ContaBancaria).filter(ContaBancaria.id == conta_id, ContaBancaria.cliente_id == cliente_id).first()
    if not k:
        raise HTTPException(status_code=404)
    tem_docs = db.query(Obrigacao).filter(Obrigacao.conta_id == k.id, Obrigacao.status != "pendente").count()
    if tem_docs:
        # nunca apaga histórico: só desativa
        k.ativa = False
        eventos.registrar(db, "cliente_alterado", f"Conta {k.rotulo} desativada", ator=admin.nome, ator_tipo="admin",
                          cliente_id=cliente_id, request=request)
    else:
        db.query(Obrigacao).filter(Obrigacao.conta_id == k.id).delete()
        eventos.registrar(db, "cliente_alterado", f"Conta {k.rotulo} removida", ator=admin.nome, ator_tipo="admin",
                          cliente_id=cliente_id, request=request)
        db.delete(k)
    db.commit()


@router.get("/{cliente_id}/obrigacoes", response_model=list[ObrigacaoOut])
def obrigacoes(cliente_id: int, db: Session = Depends(get_db)):
    c = db.get(Cliente, cliente_id)
    if not c:
        raise HTTPException(status_code=404)
    garantir_obrigacoes(db, c)
    db.commit()
    obs = (db.query(Obrigacao).filter(Obrigacao.cliente_id == c.id)
           .order_by(Obrigacao.competencia.desc(), Obrigacao.tipo, Obrigacao.conta_id).all())
    return [obrigacao_out(o) for o in obs]


@router.post("/{cliente_id}/upload", response_model=DocumentoOut)
async def upload_em_nome(
    cliente_id: int, request: Request, background: BackgroundTasks,
    obrigacao_id: int = Form(...), canal: str = Form("whatsapp"), arquivo: UploadFile = File(...),
    db: Session = Depends(get_db), admin: Usuario = Depends(get_admin),
):
    c = db.get(Cliente, cliente_id)
    if not c:
        raise HTTPException(status_code=404)
    ob = db.query(Obrigacao).filter(Obrigacao.id == obrigacao_id, Obrigacao.cliente_id == c.id).first()
    if not ob:
        raise HTTPException(status_code=404, detail="Pendência não encontrada")
    if canal not in ("whatsapp", "email", "outro", "portal"):
        canal = "outro"
    data = await arquivo.read()
    d = receber_documento(db, cliente=c, obrigacao=ob, arquivo=arquivo, data=data,
                          enviado_por="admin", enviado_por_nome=admin.nome, canal=canal, request=request)
    db.commit()
    db.refresh(d)
    background.add_task(processar_ia, d.id)
    return doc_out(d)
