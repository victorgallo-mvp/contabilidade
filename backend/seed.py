"""Popula o banco com clientes fictícios para demonstração.

Uso: python seed.py            (adiciona se o banco estiver vazio)
     python seed.py --reset    (apaga tudo e recria)
"""
import hashlib
import random
import sys
from datetime import datetime, timedelta, timezone
from app.database import engine, Base, SessionLocal
from app import models
from app.models import Cliente, ContaBancaria, Obrigacao, Documento, Evento
from app.auth import garantir_admin_inicial
from app.services import storage
from app.services.obrigacoes import garantir_obrigacoes, competencia_atual, competencia_anterior, descricao_obrigacao, rotulo_competencia

random.seed(7)

CLIENTES = [
    dict(nome="Dr. Rafael Andrade - Clínica Médica", responsavel="Rafael", whatsapp="5531999990001", email="rafael@exemplo.com",
         tipos_ativos=["extrato", "nf_entrada"], contas=[("Itaú", "Conta PJ"), ("Nubank", None)]),
    dict(nome="Dra. Camila Nogueira - Dermatologia", responsavel="Camila", whatsapp="5531999990002", email="camila@exemplo.com",
         tipos_ativos=["extrato"], contas=[("Bradesco", "Conta PJ")]),
    dict(nome="Feeling Comunicação Ltda", responsavel="Iran", whatsapp="5531999990003", email="iran@exemplo.com",
         tipos_ativos=["extrato", "nf_entrada", "recibo"], contas=[("Inter", "Conta PJ"), ("Sicoob", "Conta reserva")]),
    dict(nome="Dr. Marcos Vieira - Ortopedia", responsavel="Marcos", whatsapp="5531999990004", email="marcos@exemplo.com",
         tipos_ativos=["extrato"], contas=[("Santander", None)]),
    dict(nome="Studio Pilates Corpo Leve", responsavel="Juliana", whatsapp="5531999990005", email="juliana@exemplo.com",
         tipos_ativos=["extrato", "recibo"], contas=[("Caixa", "Conta PJ")]),
]


def pdf_ficticio(titulo: str, linhas: list[str]) -> bytes:
    """Gera um PDF mínimo válido, só texto, sem dependências."""
    conteudo = "BT /F1 14 Tf 50 780 Td (" + titulo + ") Tj ET\n"
    y = 750
    for l in linhas:
        conteudo += f"BT /F1 10 Tf 50 {y} Td ({l}) Tj ET\n"
        y -= 16
    stream = conteudo.encode("latin-1", "replace")
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = b"%PDF-1.4\n"
    offsets = []
    for i, o in enumerate(objs, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + o + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return out


def main(reset: bool):
    if reset:
        Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    garantir_admin_inicial(db)
    if db.query(Cliente).count() and not reset:
        print("Banco já tem clientes. Use --reset para recriar.")
        return

    atual = competencia_atual()
    m1 = competencia_anterior(atual)
    m2 = competencia_anterior(m1)
    m3 = competencia_anterior(m2)
    agora = datetime.now(timezone.utc)

    for i, spec in enumerate(CLIENTES):
        c = Cliente(
            nome=spec["nome"], responsavel=spec["responsavel"], whatsapp=spec["whatsapp"], email=spec["email"],
            cnpj=f"{random.randint(10, 99)}.{random.randint(100, 999)}.{random.randint(100, 999)}/0001-{random.randint(10, 99)}",
            slug=f"demo{i + 1}x{random.randint(100, 999)}", mes_inicio=m3, dia_corte=10, tipos_ativos=spec["tipos_ativos"],
        )
        db.add(c)
        db.flush()
        for banco, apelido in spec["contas"]:
            db.add(ContaBancaria(cliente_id=c.id, banco=banco, apelido=apelido))
        db.flush()
        db.refresh(c)
        db.add(Evento(cliente_id=c.id, tipo="cliente_criado", descricao=f"Cliente {c.nome} cadastrado",
                      ator="Pedro", ator_tipo="admin", created_at=agora - timedelta(days=95)))
        garantir_obrigacoes(db, c)
    db.commit()

    # cenários por cliente:
    # 1 Rafael: tudo aceito nos 2 meses antigos, mês passado em análise (enviou ontem)
    # 2 Camila: tudo aceito, em dia
    # 3 Feeling: m3 e m2 aceitos, m1 sem nada (atrasado), foi cobrada 1x
    # 4 Marcos: nada enviado desde m3 (muito atrasado), cobrado 2x
    # 5 Juliana: m2 rejeitado (extrato incompleto), aguardando correção; m1 pendente
    clientes = db.query(Cliente).order_by(Cliente.id).all()

    def enviar(c: Cliente, ob: Obrigacao, quando: datetime, status: str, motivo: str | None = None, ia_alerta: str | None = None):
        rot = descricao_obrigacao(ob)
        nome = f"{rot.replace(' ', '_').replace('(', '').replace(')', '')}_{ob.competencia}.pdf".lower()
        data = pdf_ficticio(f"{rot} - {rotulo_competencia(ob.competencia)}", [
            f"Titular: {c.nome}", f"Periodo: 01/{ob.competencia[5:]}/{ob.competencia[:4]} a 30/{ob.competencia[5:]}/{ob.competencia[:4]}",
            "Saldo inicial: R$ 12.430,55", "Saldo final: R$ 9.871,02", "Documento ficticio para demonstracao.",
        ])
        salvo = storage.salvar(cliente_nome=c.nome, competencia=ob.competencia, tipo_rotulo=models.TIPOS_DOCUMENTO[ob.tipo],
                               nome_arquivo=nome, data=data, mime="application/pdf")
        d = Documento(
            obrigacao_id=ob.id, cliente_id=c.id, nome_arquivo=nome, mime="application/pdf", tamanho=len(data),
            sha256=hashlib.sha256(data).hexdigest(), storage_backend=salvo.backend, storage_ref=salvo.ref,
            enviado_por="cliente", canal="portal", status=status, motivo_rejeicao=motivo, created_at=quando,
            ia_status="alerta" if ia_alerta else "ok", ia_banco=ob.conta.banco if ob.conta else None,
            ia_competencia=ob.competencia, ia_saldo_inicial="R$ 12.430,55", ia_saldo_final="R$ 9.871,02",
            ia_resumo=f"{rot} de {rotulo_competencia(ob.competencia)}, titular {c.nome}.", ia_alerta=ia_alerta,
        )
        if status != "em_analise":
            d.revisado_em = quando + timedelta(hours=random.randint(2, 30))
            d.revisado_por = "Pedro"
        db.add(d)
        db.flush()
        db.add(Evento(cliente_id=c.id, documento_id=d.id, obrigacao_id=ob.id, tipo="acesso_portal",
                      descricao="Cliente abriu o portal", ator="cliente", ator_tipo="cliente", ip="187.10.22.4",
                      created_at=quando - timedelta(minutes=3)))
        db.add(Evento(cliente_id=c.id, documento_id=d.id, obrigacao_id=ob.id, tipo="upload",
                      descricao=f"{rot} de {rotulo_competencia(ob.competencia)}: {nome}", ator="cliente", ator_tipo="cliente",
                      ip="187.10.22.4", meta={"canal": "portal", "sha256": d.sha256, "tamanho": len(data)},
                      lida_admin=(status != "em_analise"), created_at=quando))
        if status == "aceito":
            ob.status = "aceita"
            db.add(Evento(cliente_id=c.id, documento_id=d.id, obrigacao_id=ob.id, tipo="aceite",
                          descricao=f"{rot} de {rotulo_competencia(ob.competencia)} aceito: {nome}", ator="Pedro", ator_tipo="admin",
                          created_at=d.revisado_em))
        elif status == "rejeitado":
            ob.status = "pendente"
            ob.ultima_rejeicao = motivo
            db.add(Evento(cliente_id=c.id, documento_id=d.id, obrigacao_id=ob.id, tipo="rejeicao",
                          descricao=f"{rot} de {rotulo_competencia(ob.competencia)} rejeitado: {motivo}", ator="Pedro", ator_tipo="admin",
                          meta={"motivo": motivo}, created_at=d.revisado_em))
        else:
            ob.status = "em_analise"

    def cobrar(c: Cliente, comp: str, quando: datetime, pend: list[str]):
        db.add(Evento(cliente_id=c.id, tipo="cobranca",
                      descricao=f"Cobrança de {rotulo_competencia(comp)} enviada por WhatsApp ({len(pend)} pendência(s))",
                      ator="Pedro", ator_tipo="admin", created_at=quando,
                      meta={"competencia": comp, "pendencias": pend, "canal": "whatsapp", "descricao": f"{len(pend)} pendência(s)"}))

    def obs_de(c: Cliente, comp: str) -> list[Obrigacao]:
        return [o for o in c.obrigacoes if o.competencia == comp]

    r, cam, fee, mar, jul = clientes

    for comp, dias in ((m3, 70), (m2, 40)):
        for ob in obs_de(r, comp):
            enviar(r, ob, agora - timedelta(days=dias, hours=random.randint(1, 20)), "aceito")
    for ob in obs_de(r, m1):
        enviar(r, ob, agora - timedelta(days=1, hours=2), "em_analise")

    for comp, dias in ((m3, 72), (m2, 41), (m1, 9)):
        for ob in obs_de(cam, comp):
            enviar(cam, ob, agora - timedelta(days=dias, hours=random.randint(1, 20)), "aceito")

    for comp, dias in ((m3, 68), (m2, 38)):
        for ob in obs_de(fee, comp):
            enviar(fee, ob, agora - timedelta(days=dias, hours=random.randint(1, 20)), "aceito")
    cobrar(fee, m1, agora - timedelta(days=4), [descricao_obrigacao(o) for o in obs_de(fee, m1)])

    cobrar(mar, m3, agora - timedelta(days=50), [descricao_obrigacao(o) for o in obs_de(mar, m3)])
    cobrar(mar, m3, agora - timedelta(days=20), [descricao_obrigacao(o) for o in obs_de(mar, m3)])

    for ob in obs_de(jul, m3):
        enviar(jul, ob, agora - timedelta(days=66), "aceito")
    for ob in obs_de(jul, m2):
        if ob.tipo == "extrato":
            enviar(jul, ob, agora - timedelta(days=12), "rejeitado",
                   motivo="Extrato veio só até o dia 15. Precisamos do mês completo.",
                   ia_alerta="Extrato parece incompleto.")
        else:
            enviar(jul, ob, agora - timedelta(days=12), "aceito")

    db.commit()
    print("Seed concluído.")
    for c in clientes:
        print(f"  {c.nome}: /c/{c.slug}")
    print("Login admin: pedro / pedro123")


if __name__ == "__main__":
    main(reset="--reset" in sys.argv)
