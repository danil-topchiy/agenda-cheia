# Hackthon Pix Test UI

UI local para testar a `agenda-cheia-pix-api`.

Ela permite:

- criar cobranca Pix chamando `POST /charges` da API Pix;
- consultar o status da cobranca criada;
- receber webhooks em `POST /webhooks/woovi`;
- exibir em tempo real o stream dos webhooks recebidos;
- encaminhar o webhook recebido para `POST /webhooks/woovi` da API Pix;
- simular pagamento ou expiracao sem depender da Woovi.

## Setup

```bash
cd hackthon-pix-test-ui
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
```

Edite `.env` se a API Pix estiver em outra porta:

```bash
PIX_API_BASE_URL=http://127.0.0.1:8000
PUBLIC_BASE_URL=http://127.0.0.1:8010
FORWARD_WEBHOOK_TO_PIX_API=true
```

## Executar

Em um terminal, suba a API Pix:

```bash
cd ../agenda-cheia/agenda-cheia-pix-api
WOOVI_WEBHOOK_VERIFY_SIGNATURE=false uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Use `WOOVI_WEBHOOK_VERIFY_SIGNATURE=false` para as simulacoes locais de pagamento/expiracao funcionarem sem assinatura Woovi real.

Em outro terminal, suba a UI:

```bash
cd ../../hackthon-pix-test-ui
uvicorn app.main:app --host 127.0.0.1 --port 8010 --reload
```

Acesse:

```text
http://127.0.0.1:8010
```

## Webhook

Cadastre na Woovi ou no túnel público a URL:

```text
POST http://127.0.0.1:8010/webhooks/woovi
```

Para ambiente externo, use `ngrok` ou Cloudflare Tunnel e atualize:

```bash
PUBLIC_BASE_URL=https://sua-url-publica
```

A UI registra o webhook, mostra no stream e encaminha para:

```text
<PIX_API_BASE_URL>/webhooks/woovi
```

Headers encaminhados:

- `Authorization`
- `x-webhook-signature`
- `Content-Type`

## Testes

```bash
pytest
```
