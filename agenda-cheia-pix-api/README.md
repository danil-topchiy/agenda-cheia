# Agenda Cheia Pix API

API FastAPI para criar cobrancas Pix na Woovi com QR Code e receber webhooks de confirmacao de pagamento.

## O que foi implementado

- `POST /charges`: cria cobranca Pix na Woovi usando `POST /api/v1/charge`.
- `GET /charges/{correlationID}`: consulta o registro local da cobranca.
- `POST /webhooks`: cadastra dinamicamente uma URL de webhook na Woovi usando `POST /api/v1/webhook`.
- `POST /webhooks/woovi`: recebe eventos da Woovi e atualiza o status local.
- SQLite local para armazenar cobrancas e eventos recebidos.
- Validacao opcional do header `Authorization` do webhook.
- Validacao recomendada de `x-webhook-signature` via chaves publicas da Woovi.

## Configuracao

```bash
cd agenda-cheia-pix-api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
```

Edite `.env`:

```bash
WOOVI_APP_ID=seu_app_id_woovi
WOOVI_API_BASE_URL=https://api.woovi.com
DATABASE_PATH=data/agenda_cheia_pix.db
WOOVI_WEBHOOK_AUTHORIZATION=um_token_opcional_para_o_webhook
WOOVI_WEBHOOK_VERIFY_SIGNATURE=true
```

Para sandbox, use:

```bash
WOOVI_API_BASE_URL=https://api.woovi-sandbox.com
```

## Executar

```bash
uvicorn app.main:app --reload
```

Swagger local:

```text
http://127.0.0.1:8000/docs
```

## Criar cobranca

```bash
curl -X POST http://127.0.0.1:8000/charges \
  -H 'Content-Type: application/json' \
  -d '{
    "value": 1500,
    "expiresIn": 900,
    "correlationID": "agenda-123",
    "comment": "Agendamento agenda-123"
  }'
```

`value` e em centavos. `expiresIn` e enviado para a Woovi no payload da cobranca. Caso a conta/API rejeite esse campo, configure o tempo padrao de expiracao no painel da Woovi em `Cobrancas > Ajustes`.

## Fluxo sandbox e confirmacao Pix

Esta API esta implementada para Woovi/OpenPix. Ela espera um AppID bruto no header `Authorization`, sem `Bearer`.

No sandbox, use o token/AppID completo exatamente como copiado do painel em `WOOVI_APP_ID`. Mesmo que o valor pareca base64 ou decodifique para `Client_Id:Client_Secret`, nao separe as partes; envie a string completa no header `Authorization`.

### Woovi sandbox

1. Crie uma conta separada em `https://app.woovi-sandbox.com/`. Dados de producao nao funcionam no sandbox.
2. Gere um AppID em `API/Plugins` no sandbox.
3. Rode a API apontando para sandbox:

```bash
WOOVI_APP_ID=seu_app_id_sandbox \
WOOVI_API_BASE_URL=https://api.woovi-sandbox.com \
WOOVI_WEBHOOK_VERIFY_SIGNATURE=true \
uvicorn app.main:app --reload
```

4. Exponha `POST /webhooks/woovi` com uma URL HTTPS publica, por exemplo via ngrok ou Cloudflare Tunnel.
5. Cadastre o webhook no painel/API da Woovi para os eventos `OPENPIX:CHARGE_COMPLETED`, `OPENPIX:CHARGE_EXPIRED` e `OPENPIX:CHARGE_CREATED`.
6. Crie uma cobranca de teste com valor baixo:

```bash
curl -X POST http://127.0.0.1:8000/charges \
  -H 'Content-Type: application/json' \
  -d '{
    "value": 500,
    "expiresIn": 600,
    "correlationID": "sandbox-agenda-001",
    "comment": "Sinal de agendamento sandbox"
  }'
```

7. Abra o `paymentLinkUrl` retornado ou a cobranca no painel sandbox e use a opcao de simular pagamento. Tambem e possivel simular pela API de teste usando o `transactionID`/`identifier` retornado:

```bash
curl "https://api.woovi-sandbox.com/openpix/testing?transactionID=TRANSACTION_ID" \
  -H "Authorization: $WOOVI_APP_ID"
```

8. Quando a Woovi enviar `OPENPIX:CHARGE_COMPLETED`, confirme o status local:

```bash
curl http://127.0.0.1:8000/charges/sandbox-agenda-001
```

### Simulacao local sem provedor

Para validar o fluxo da API sem depender do sandbox externo:

```bash
pytest tests/test_api.py::test_charge_flow_updates_created_charge_after_payment_webhook
```

Esse teste cria uma cobranca local via `POST /charges`, simula o webhook `OPENPIX:CHARGE_COMPLETED` e verifica que `GET /charges/{correlationID}` retorna `status=COMPLETED`.

### Integracao real no sandbox Woovi

Para criar uma cobranca real no sandbox Woovi, simular o pagamento e consultar `COMPLETED`:

```bash
WOOVI_SANDBOX_APP_ID=seu_app_id_sandbox \
pytest tests/test_woovi_sandbox_integration.py
```

Esse teste nao valida entrega de webhook para sua maquina local. Para isso, cadastre uma URL HTTPS publica apontando para `POST /webhooks/woovi`.

## Webhook Woovi

Cadastre na Woovi a URL publica:

```text
POST https://seu-dominio.com/webhooks/woovi
```

Eventos recomendados:

```text
OPENPIX:CHARGE_COMPLETED
OPENPIX:CHARGE_EXPIRED
OPENPIX:CHARGE_CREATED
```

Se configurar `WOOVI_WEBHOOK_AUTHORIZATION`, cadastre o mesmo valor em um header `Authorization` no webhook da Woovi.

Tambem e possivel cadastrar a URL dinamicamente pela propria API Pix:

```bash
curl -X POST http://127.0.0.1:8000/webhooks \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "agenda-cheia-dev-completed",
    "event": "OPENPIX:CHARGE_COMPLETED",
    "url": "https://sua-url-publica/webhooks/woovi",
    "isActive": true
  }'
```

Se `authorization` nao for enviado no JSON, a API usa `WOOVI_WEBHOOK_AUTHORIZATION` como valor padrao para registrar o webhook na Woovi. Para eventos diferentes, faca uma chamada por evento.

Com `WOOVI_WEBHOOK_VERIFY_SIGNATURE=true`, a API valida `x-webhook-signature` usando `GET /api/v1/webhook/public-keys`.

Para testar localmente sem assinatura:

```bash
WOOVI_WEBHOOK_VERIFY_SIGNATURE=false uvicorn app.main:app --reload
```

## Testes

```bash
pytest
```

## Referencias usadas

- https://developers.woovi.com/docs/apis/api-getting-started
- https://developers.woovi.com/en/docs/test-environment
- https://developers.woovi.com/docs/charge/how-to-create-charge-using-api
- https://developers.woovi.com/docs/webhook/platform/webhook-platform-api
- https://developers.woovi.com/docs/webhook/webhook-events-type
- https://developers.woovi.com/docs/webhook/seguranca/webhook-signature-validation
- https://developers.woovi.com/docs/webhook/seguranca/webhook-public-keys
