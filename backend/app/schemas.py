from datetime import datetime
from pydantic import BaseModel, Field


# ---------- auth ----------

class LoginOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    nome: str


# ---------- clientes ----------

class ContaIn(BaseModel):
    banco: str = Field(min_length=1, max_length=80)
    apelido: str | None = Field(default=None, max_length=80)
    ativa: bool = True


class ContaOut(ContaIn):
    id: int
    rotulo: str

    class Config:
        from_attributes = True


class ClienteIn(BaseModel):
    nome: str = Field(min_length=1, max_length=150)
    cnpj: str | None = None
    responsavel: str | None = None
    whatsapp: str | None = None
    email: str | None = None
    mes_inicio: str = Field(pattern=r"^\d{4}-\d{2}$")
    dia_corte: int = Field(default=10, ge=1, le=28)
    tipos_ativos: list[str] = Field(default_factory=lambda: ["extrato"])
    observacoes: str | None = None
    ativo: bool = True


class ClienteOut(ClienteIn):
    id: int
    slug: str
    link_portal: str
    contas: list[ContaOut] = []
    created_at: datetime
    # resumo de pendências (preenchido na listagem)
    pendentes: int = 0
    atrasadas: int = 0
    em_analise: int = 0

    class Config:
        from_attributes = True


# ---------- obrigações / documentos ----------

class DocumentoOut(BaseModel):
    id: int
    obrigacao_id: int
    cliente_id: int
    nome_arquivo: str
    mime: str
    tamanho: int
    sha256: str
    enviado_por: str
    enviado_por_nome: str | None
    canal: str
    status: str
    motivo_rejeicao: str | None
    revisado_em: datetime | None
    revisado_por: str | None
    ia_status: str
    ia_banco: str | None
    ia_competencia: str | None
    ia_periodo_inicio: str | None
    ia_periodo_fim: str | None
    ia_saldo_inicial: str | None
    ia_saldo_final: str | None
    ia_resumo: str | None
    ia_alerta: str | None
    drive_link: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class ObrigacaoOut(BaseModel):
    id: int
    cliente_id: int
    tipo: str
    conta_id: int | None
    competencia: str
    competencia_rotulo: str
    descricao: str
    status: str
    situacao: str
    vencimento: str
    ultima_rejeicao: str | None
    documentos: list[DocumentoOut] = []


class RevisaoItem(BaseModel):
    documento: DocumentoOut
    obrigacao: ObrigacaoOut
    cliente_nome: str
    cliente_slug: str


class RejeitarIn(BaseModel):
    motivo: str = Field(min_length=3, max_length=1000)


# ---------- kanban ----------

class KanbanCard(BaseModel):
    cliente_id: int
    cliente_nome: str
    cliente_slug: str
    whatsapp: str | None
    competencia: str
    competencia_rotulo: str
    coluna: str
    vencimento: str
    dias_atraso: int
    obrigacoes: list[ObrigacaoOut]
    ultima_cobranca: datetime | None
    total_cobrancas: int


class KanbanOut(BaseModel):
    competencias: list[str]
    colunas: dict[str, list[KanbanCard]]
    resumo: dict[str, int]


# ---------- cobrança ----------

class CobrancaIn(BaseModel):
    cliente_id: int
    competencia: str = Field(pattern=r"^\d{4}-\d{2}$")
    mensagem: str | None = None  # se o admin editou o texto padrão


class CobrancaOut(BaseModel):
    link: str
    mensagem: str
    evento_id: int


# ---------- portal ----------

class PortalCompetencia(BaseModel):
    competencia: str
    rotulo: str
    vencimento: str
    obrigacoes: list[ObrigacaoOut]
    completa: bool


class PortalOut(BaseModel):
    cliente_nome: str
    responsavel: str | None
    competencias: list[PortalCompetencia]
    historico: list[DocumentoOut]


# ---------- notificações / histórico ----------

class EventoOut(BaseModel):
    id: int
    cliente_id: int | None
    cliente_nome: str | None
    documento_id: int | None
    documento_nome: str | None
    obrigacao_id: int | None
    obrigacao_descricao: str | None
    competencia: str | None
    tipo: str
    tipo_rotulo: str
    descricao: str
    ator: str
    ator_tipo: str
    ip: str | None
    meta: dict | None
    lida_admin: bool
    created_at: datetime


class NotificacoesOut(BaseModel):
    nao_lidas: int
    itens: list[EventoOut]


class DashboardOut(BaseModel):
    clientes_ativos: int
    atrasadas: int
    em_analise: int
    aguardando: int
    aceitas_mes: int
    clientes_com_atraso: int
    notificacoes: int
