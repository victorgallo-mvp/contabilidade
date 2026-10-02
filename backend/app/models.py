"""Modelo de dados.

Conceitos:
- Cliente: empresa atendida pela contabilidade. Acessa o portal por um slug fixo.
- ContaBancaria: cada conta gera uma obrigação de extrato por mês.
- Obrigacao: o que é esperado de um cliente numa competência (AAAA-MM),
  por tipo de documento e (para extrato) por conta.
- Documento: arquivo enviado contra uma obrigação. Um mesmo obrigação pode ter
  vários documentos (reenvio após rejeição).
- Evento: log só de inserção. É o resguardo jurídico do escritório.
"""
from datetime import datetime, timezone
from sqlalchemy import (
    String, Integer, Boolean, DateTime, ForeignKey, Text, JSON, UniqueConstraint, Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


TIPOS_DOCUMENTO = {
    "extrato": "Extrato bancário",
    "nf_entrada": "Notas fiscais de entrada",
    "recibo": "Recibos e comprovantes",
}

STATUS_OBRIGACAO = ("pendente", "em_analise", "aceita")
STATUS_DOCUMENTO = ("em_analise", "aceito", "rejeitado")
CANAIS = ("portal", "whatsapp", "email", "outro")


class Usuario(Base):
    __tablename__ = "usuarios"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True)
    nome: Mapped[str] = mapped_column(String(100))
    senha_hash: Mapped[str] = mapped_column(String(200))
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class Cliente(Base):
    __tablename__ = "clientes"
    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(150))
    cnpj: Mapped[str | None] = mapped_column(String(20), nullable=True)
    responsavel: Mapped[str | None] = mapped_column(String(100), nullable=True)
    whatsapp: Mapped[str | None] = mapped_column(String(20), nullable=True)  # só dígitos, com DDI
    email: Mapped[str | None] = mapped_column(String(150), nullable=True)
    slug: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    # competência a partir da qual as obrigações são geradas (AAAA-MM)
    mes_inicio: Mapped[str] = mapped_column(String(7))
    dia_corte: Mapped[int] = mapped_column(Integer, default=10)
    # lista de tipos ativos, ex: ["extrato", "nf_entrada"]
    tipos_ativos: Mapped[list] = mapped_column(JSON, default=list)
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)
    drive_folder_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    contas: Mapped[list["ContaBancaria"]] = relationship(back_populates="cliente", cascade="all, delete-orphan")
    obrigacoes: Mapped[list["Obrigacao"]] = relationship(back_populates="cliente", cascade="all, delete-orphan")


class ContaBancaria(Base):
    __tablename__ = "contas_bancarias"
    id: Mapped[int] = mapped_column(primary_key=True)
    cliente_id: Mapped[int] = mapped_column(ForeignKey("clientes.id", ondelete="CASCADE"), index=True)
    banco: Mapped[str] = mapped_column(String(80))
    apelido: Mapped[str | None] = mapped_column(String(80), nullable=True)  # ex: "Conta PJ", "Nubank"
    ativa: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    cliente: Mapped["Cliente"] = relationship(back_populates="contas")

    @property
    def rotulo(self) -> str:
        return f"{self.banco} ({self.apelido})" if self.apelido else self.banco


class Obrigacao(Base):
    __tablename__ = "obrigacoes"
    __table_args__ = (
        UniqueConstraint("cliente_id", "tipo", "conta_id", "competencia", name="uq_obrigacao"),
        Index("ix_obrigacao_cliente_comp", "cliente_id", "competencia"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    cliente_id: Mapped[int] = mapped_column(ForeignKey("clientes.id", ondelete="CASCADE"))
    tipo: Mapped[str] = mapped_column(String(30))
    conta_id: Mapped[int | None] = mapped_column(ForeignKey("contas_bancarias.id", ondelete="CASCADE"), nullable=True)
    competencia: Mapped[str] = mapped_column(String(7), index=True)  # AAAA-MM
    status: Mapped[str] = mapped_column(String(20), default="pendente")
    ultima_rejeicao: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)

    cliente: Mapped["Cliente"] = relationship(back_populates="obrigacoes")
    conta: Mapped["ContaBancaria | None"] = relationship()
    documentos: Mapped[list["Documento"]] = relationship(back_populates="obrigacao", cascade="all, delete-orphan")


class Documento(Base):
    __tablename__ = "documentos"
    id: Mapped[int] = mapped_column(primary_key=True)
    obrigacao_id: Mapped[int] = mapped_column(ForeignKey("obrigacoes.id", ondelete="CASCADE"), index=True)
    cliente_id: Mapped[int] = mapped_column(ForeignKey("clientes.id", ondelete="CASCADE"), index=True)
    nome_arquivo: Mapped[str] = mapped_column(String(255))
    mime: Mapped[str] = mapped_column(String(100))
    tamanho: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    storage_backend: Mapped[str] = mapped_column(String(20))
    storage_ref: Mapped[str] = mapped_column(String(500))  # caminho local ou file id do Drive
    drive_link: Mapped[str | None] = mapped_column(String(500), nullable=True)
    enviado_por: Mapped[str] = mapped_column(String(20))  # cliente | admin
    enviado_por_nome: Mapped[str | None] = mapped_column(String(100), nullable=True)
    canal: Mapped[str] = mapped_column(String(20), default="portal")
    status: Mapped[str] = mapped_column(String(20), default="em_analise")
    motivo_rejeicao: Mapped[str | None] = mapped_column(Text, nullable=True)
    revisado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revisado_por: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # resultado da leitura por IA
    ia_status: Mapped[str] = mapped_column(String(20), default="pendente")  # pendente | ok | alerta | erro | pulado
    ia_banco: Mapped[str | None] = mapped_column(String(80), nullable=True)
    ia_periodo_inicio: Mapped[str | None] = mapped_column(String(10), nullable=True)
    ia_periodo_fim: Mapped[str | None] = mapped_column(String(10), nullable=True)
    ia_competencia: Mapped[str | None] = mapped_column(String(7), nullable=True)
    ia_saldo_inicial: Mapped[str | None] = mapped_column(String(30), nullable=True)
    ia_saldo_final: Mapped[str | None] = mapped_column(String(30), nullable=True)
    ia_resumo: Mapped[str | None] = mapped_column(Text, nullable=True)
    ia_alerta: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, index=True)

    obrigacao: Mapped["Obrigacao"] = relationship(back_populates="documentos")
    cliente: Mapped["Cliente"] = relationship()


class Evento(Base):
    """Log imutável. Nunca é editado nem apagado pela aplicação."""
    __tablename__ = "eventos"
    __table_args__ = (Index("ix_evento_cliente_data", "cliente_id", "created_at"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    cliente_id: Mapped[int | None] = mapped_column(ForeignKey("clientes.id", ondelete="SET NULL"), nullable=True)
    documento_id: Mapped[int | None] = mapped_column(ForeignKey("documentos.id", ondelete="SET NULL"), nullable=True)
    obrigacao_id: Mapped[int | None] = mapped_column(ForeignKey("obrigacoes.id", ondelete="SET NULL"), nullable=True)
    tipo: Mapped[str] = mapped_column(String(40), index=True)
    descricao: Mapped[str] = mapped_column(Text)
    ator: Mapped[str] = mapped_column(String(100))  # "cliente" ou nome do admin
    ator_tipo: Mapped[str] = mapped_column(String(20))  # cliente | admin | sistema
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(300), nullable=True)
    meta: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    lida_admin: Mapped[bool] = mapped_column(Boolean, default=True)  # False só nos eventos que viram notificação
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, index=True)

    cliente: Mapped["Cliente | None"] = relationship()
    documento: Mapped["Documento | None"] = relationship()


TIPOS_EVENTO = {
    "acesso_portal": "Cliente acessou o portal",
    "upload": "Documento enviado",
    "upload_admin": "Documento anexado pelo escritório",
    "download": "Documento baixado",
    "aceite": "Documento aceito",
    "rejeicao": "Documento rejeitado",
    "cobranca": "Cobrança enviada",
    "cliente_criado": "Cliente cadastrado",
    "cliente_alterado": "Cadastro alterado",
    "ia_leitura": "Leitura automática do documento",
}
