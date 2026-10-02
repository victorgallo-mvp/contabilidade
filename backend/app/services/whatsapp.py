"""Monta links wa.me com mensagem pronta. Não envia nada: quem clica e envia é o escritório."""
import re
from urllib.parse import quote
from app.config import settings
from app.services.obrigacoes import rotulo_competencia


def numero_limpo(whatsapp: str | None) -> str | None:
    if not whatsapp:
        return None
    digitos = re.sub(r"\D", "", whatsapp)
    if not digitos:
        return None
    if not digitos.startswith("55"):
        digitos = "55" + digitos
    return digitos


def link_portal(slug: str) -> str:
    return f"{settings.frontend_url.rstrip('/')}/c/{slug}"


def mensagem_cobranca(nome_cliente: str, competencia: str, pendencias: list[str], slug: str) -> str:
    primeiro_nome = nome_cliente.split()[0] if nome_cliente else ""
    itens = "\n".join(f"• {p}" for p in pendencias)
    return (
        f"Olá {primeiro_nome}, tudo bem?\n\n"
        f"Ainda está faltando a documentação de {rotulo_competencia(competencia)} para fecharmos a contabilidade:\n"
        f"{itens}\n\n"
        f"Pode enviar pelo seu portal, leva menos de 1 minuto:\n{link_portal(slug)}\n\n"
        f"Qualquer dúvida é só chamar. Obrigado!"
    )


def mensagem_correcao(nome_cliente: str, competencia: str, descricao: str, motivo: str, slug: str) -> str:
    primeiro_nome = nome_cliente.split()[0] if nome_cliente else ""
    return (
        f"Olá {primeiro_nome}, tudo bem?\n\n"
        f"Precisamos de um ajuste no documento *{descricao}* de {rotulo_competencia(competencia)}:\n"
        f"{motivo}\n\n"
        f"Pode reenviar pelo portal:\n{link_portal(slug)}\n\n"
        f"Obrigado!"
    )


def link_wa(whatsapp: str | None, mensagem: str) -> str:
    numero = numero_limpo(whatsapp)
    base = f"https://wa.me/{numero}" if numero else "https://wa.me/"
    return f"{base}?text={quote(mensagem)}"
