# Agenda Cheia Pix API

API FastAPI para criar cobrancas Pix na Woovi com QR Code e receber webhooks de confirmacao de pagamento.

## O que foi implementado

- `POST /charges`: cria cobranca Pix na Woovi usando `POST /api/v1/charge`.
- `GET /charges/{correlationID}`: consulta o registro local da cobranca.
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

A credencial base64 no formato `Client_Id:Client_Secret` e de Efi/Gerencianet. Ela nao deve ser usada em `WOOVI_APP_ID`: a Efi usa OAuth2 com Basic Auth e exige certificado mTLS em todas as chamadas da API Pix, inclusive `/oauth/token`.

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

7. Abra o `paymentLinkUrl` retornado ou a cobranca no painel sandbox e use a opcao de simular pagamento. Quando a Woovi enviar `OPENPIX:CHARGE_COMPLETED`, confirme o status local:

```bash
curl http://127.0.0.1:8000/charges/sandbox-agenda-001
```

### Simulacao local sem provedor

Para validar o fluxo da API sem depender do sandbox externo:

```bash
pytest tests/test_api.py::test_charge_flow_updates_created_charge_after_payment_webhook
```

Esse teste cria uma cobranca local via `POST /charges`, simula o webhook `OPENPIX:CHARGE_COMPLETED` e verifica que `GET /charges/{correlationID}` retorna `status=COMPLETED`.

### Se o provedor for Efi

Antes de usar a credencial `Client_Id:Client_Secret`, sera necessario trocar ou adicionar um client Efi. O fluxo nao e compativel com o client Woovi atual:

1. Configure `EFI_CLIENT_ID`, `EFI_CLIENT_SECRET`, `EFI_CERT_PATH` e a chave Pix da conta sandbox.
2. Use a base `https://pix-h.api.efipay.com.br`.
3. Obtenha token em `POST /oauth/token` com Basic Auth e certificado mTLS.
4. Crie a cobranca imediata em `POST /v2/cob` ou `PUT /v2/cob/:txid`.
5. Cadastre webhook em `PUT /v2/webhook/:chave`; a Efi envia callbacks para `sua-url/pix`.
6. Para testar confirmacao automatica no sandbox Efi, use valor entre R$ 0,01 e R$ 10,00. Valores acima de R$ 10,00 ficam ativos e nao geram webhook de confirmacao.

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
- https://dev.efipay.com.br/en/docs/api-pix/credenciais/
- https://dev.efipay.com.br/en/docs/api-pix/cobrancas-imediatas/
- https://dev.efipay.com.br/en/docs/api-pix/webhooks/
