"""Leitura automática do documento com Claude.

Só confirma: banco, período coberto e saldos. Se o que o cliente escolheu
(tipo, conta, competência) não bate com o que está no arquivo, gera um alerta
para a revisão humana. Nunca move nem reclassifica o documento sozinha.
"""
import base64
import logging
from pydantic import BaseModel
from app.config import settings

log = logging.getLogger(__name__)


class LeituraDocumento(BaseModel):
    tipo_identificado: str  # extrato | nf_entrada | recibo | outro | ilegivel
    banco: str | None = None
    periodo_inicio: str | None = None  # AAAA-MM-DD
    periodo_fim: str | None = None  # AAAA-MM-DD
    competencia: str | None = None  # AAAA-MM predominante
    saldo_inicial: str | None = None
    saldo_final: str | None = None
    titular: str | None = None
    resumo: str
    parece_completo: bool
    observacoes: str | None = None


PROMPT = """Você recebe um documento enviado por um cliente de um escritório de contabilidade no Brasil.
O cliente declarou que este arquivo é: tipo "{tipo}", competência {competencia}{conta}.

Leia o documento e extraia os campos do esquema. Regras:
- tipo_identificado: o que o arquivo realmente é (extrato, nf_entrada, recibo, outro, ilegivel).
- Para extrato: banco, titular, período coberto (data inicial e final), saldo inicial e final como texto no formato brasileiro.
- competencia: o mês AAAA-MM que o documento cobre predominantemente.
- parece_completo: false se o extrato parece parcial (ex.: cobre só metade do mês, páginas faltando, cortado).
- resumo: uma frase curta em português descrevendo o documento.
- observacoes: qualquer coisa que a contabilidade deva conferir. Deixe null se não houver.
Não invente valores. Se um campo não estiver no documento, deixe null."""


def _cliente():
    import anthropic
    return anthropic.Anthropic(api_key=settings.anthropic_api_key)


def analisar(data: bytes, mime: str, *, tipo: str, competencia: str, conta_rotulo: str | None) -> LeituraDocumento | None:
    """Retorna a leitura ou None quando a IA está desligada / arquivo não suportado."""
    if not settings.anthropic_api_key:
        return None
    if mime == "application/pdf":
        bloco = {"type": "document", "source": {"type": "base64", "media_type": "application/pdf",
                                                 "data": base64.b64encode(data).decode()}}
    elif mime in ("image/jpeg", "image/png", "image/webp", "image/gif"):
        bloco = {"type": "image", "source": {"type": "base64", "media_type": mime,
                                              "data": base64.b64encode(data).decode()}}
    else:
        return None

    prompt = PROMPT.format(
        tipo=tipo, competencia=competencia,
        conta=f', conta "{conta_rotulo}"' if conta_rotulo else "",
    )
    client = _cliente()
    resp = client.messages.parse(
        model=settings.anthropic_model,
        max_tokens=2000,
        output_config={"effort": "low"},
        messages=[{"role": "user", "content": [bloco, {"type": "text", "text": prompt}]}],
        output_format=LeituraDocumento,
    )
    if resp.stop_reason == "refusal":
        log.warning("Leitura recusada pelo modelo")
        return None
    return resp.parsed_output


def alerta_para(leitura: LeituraDocumento, *, tipo: str, competencia: str) -> str | None:
    """Compara a leitura com o que o cliente declarou e devolve um alerta curto, ou None."""
    problemas = []
    if leitura.tipo_identificado == "ilegivel":
        problemas.append("Arquivo ilegível ou vazio.")
    elif leitura.tipo_identificado not in (tipo, "outro"):
        problemas.append(f"Parece ser {leitura.tipo_identificado}, mas foi enviado como {tipo}.")
    if leitura.competencia and leitura.competencia != competencia:
        problemas.append(f"Documento cobre {leitura.competencia}, mas foi enviado para {competencia}.")
    if tipo == "extrato" and not leitura.parece_completo:
        problemas.append("Extrato parece incompleto.")
    if leitura.observacoes:
        problemas.append(leitura.observacoes)
    return " ".join(problemas) if problemas else None
