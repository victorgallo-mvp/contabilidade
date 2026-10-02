# Gestão de documentos — Contabilidade

Plataforma para o escritório receber extratos, notas de entrada e recibos dos clientes todo mês, com registro de cada envio, cobrança e revisão.

- **Portal do cliente** (`/c/{slug}`): link fixo por cliente, sem senha. Mostra o que falta em cada mês e recebe o upload.
- **Painel do escritório**: kanban de pendências por cliente e mês, fila de revisão (aceitar/rejeitar), cobrança via WhatsApp com registro, histórico completo filtrável com export CSV, notificação de novos envios.
- **Leitura automática**: Claude lê o PDF e confirma banco, período e saldos. Só alerta; nunca move ou aceita sozinho.
- **Arquivos**: Google Drive (pastas `Cliente/Ano/Mês/Tipo`) ou disco local. Banco guarda metadados, hash SHA-256 e o log imutável de eventos.

## Rodar local

Backend (Python 3.12, Postgres local):

```bash
cd backend
python3.12 -m venv venv && ./venv/bin/pip install -r requirements.txt
cp .env.example .env            # ajuste DATABASE_URL se precisar
createdb contabilidade_pedro
./venv/bin/python seed.py --reset   # 5 clientes fictícios
./venv/bin/uvicorn app.main:app --reload --port 8000
```

Frontend:

```bash
cd frontend
npm install
cp .env.example .env            # VITE_API_URL=http://localhost:8000
npm run dev
```

Login do painel: `pedro` / `pedro123` (troque via `ADMIN_USERNAME` / `ADMIN_PASSWORD` antes do primeiro boot em produção).

## Deploy

**Railway (backend)**: serviço a partir de `backend/` (Dockerfile). Adicione um Postgres e configure:

| Variável | Valor |
|---|---|
| `DATABASE_URL` | `postgresql+psycopg://…` (Railway entrega `postgresql://`; troque o prefixo) |
| `SECRET_KEY` | string longa aleatória |
| `CORS_ORIGINS` | URL do frontend na Vercel |
| `FRONTEND_URL` | URL do frontend na Vercel (usada nos links enviados por WhatsApp) |
| `ADMIN_USERNAME`, `ADMIN_PASSWORD`, `ADMIN_NOME` | acesso do superadmin |
| `STORAGE_BACKEND` | `drive` em produção |
| `DRIVE_ROOT_FOLDER_ID` | id da pasta raiz no Drive, compartilhada com a service account |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | conteúdo do JSON da service account |
| `ANTHROPIC_API_KEY` | chave para a leitura automática (vazio desliga) |

**Vercel (frontend)**: projeto a partir de `frontend/`, framework Vite, variável `VITE_API_URL` com a URL do Railway.

## Regras de negócio

- Competência `AAAA-MM` vence no `dia_corte` do mês seguinte. Depois disso é **atrasada**.
- Obrigações são geradas automaticamente a partir da configuração do cliente (tipos ativos × contas bancárias × meses desde `mes_inicio`).
- Extrato gera uma pendência por conta bancária ativa.
- Documento rejeitado volta a pendência para **corrigir**, com o motivo visível ao cliente no portal.
- Só o escritório aceita ou rejeita. O cliente pode reenviar enquanto não for aceito.
- Nenhum evento é editado ou apagado.
