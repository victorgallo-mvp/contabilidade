from app.models import Obrigacao, Documento, Evento, TIPOS_EVENTO
from app.schemas import ObrigacaoOut, DocumentoOut, EventoOut
from app.services.obrigacoes import situacao, vencimento, rotulo_competencia, descricao_obrigacao


def doc_out(d: Documento) -> DocumentoOut:
    return DocumentoOut.model_validate(d)


def obrigacao_out(o: Obrigacao, com_documentos: bool = True) -> ObrigacaoOut:
    return ObrigacaoOut(
        id=o.id,
        cliente_id=o.cliente_id,
        tipo=o.tipo,
        conta_id=o.conta_id,
        competencia=o.competencia,
        competencia_rotulo=rotulo_competencia(o.competencia),
        descricao=descricao_obrigacao(o),
        status=o.status,
        situacao=situacao(o),
        vencimento=vencimento(o.competencia, o.cliente.dia_corte).isoformat(),
        ultima_rejeicao=o.ultima_rejeicao,
        documentos=[doc_out(d) for d in sorted(o.documentos, key=lambda d: d.created_at, reverse=True)] if com_documentos else [],
    )


def evento_out(e: Evento) -> EventoOut:
    ob = e.documento.obrigacao if e.documento else None
    if ob is None and e.obrigacao_id:
        # evento de cobrança pode não ter documento; obrigação vem via meta
        pass
    return EventoOut(
        id=e.id,
        cliente_id=e.cliente_id,
        cliente_nome=e.cliente.nome if e.cliente else None,
        documento_id=e.documento_id,
        documento_nome=e.documento.nome_arquivo if e.documento else None,
        obrigacao_id=e.obrigacao_id,
        obrigacao_descricao=descricao_obrigacao(ob) if ob else (e.meta or {}).get("descricao"),
        competencia=ob.competencia if ob else (e.meta or {}).get("competencia"),
        tipo=e.tipo,
        tipo_rotulo=TIPOS_EVENTO.get(e.tipo, e.tipo),
        descricao=e.descricao,
        ator=e.ator,
        ator_tipo=e.ator_tipo,
        ip=e.ip,
        meta=e.meta,
        lida_admin=e.lida_admin,
        created_at=e.created_at,
    )
