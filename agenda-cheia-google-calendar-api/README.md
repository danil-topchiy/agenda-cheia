# Agenda Cheia Google Calendar API

API FastAPI para criar, atualizar, listar e sincronizar appointments com Google Calendar.

## O que foi implementado

- `POST /appointments`: cria appointment como evento no Google Calendar.
- `PATCH /appointments/{appointment_id}`: atualiza dados, estado e status do evento.
- `GET /appointments?state=scheduled`: lista appointments por estado usando `extendedProperties.private`.
- `GET /appointments/{appointment_id}`: busca um appointment pelo ID do evento Google.
- `POST /sync/poll`: executa sync incremental via `syncToken`.
- `POST /sync/watch`: cria canal de push notification no Google Calendar.
- `POST /webhooks/google-calendar`: recebe notificacoes do Google e dispara sync.
- `GET /webhooks/google-calendar/notifications`: lista notificacoes recebidas.
- `GET /webhooks/google-calendar/stream`: stream SSE de notificacoes para UI/testes.
- `GET /auth/google/login`: gera URL OAuth para conectar o calendario real de um usuario.
- `GET /auth/google/callback`: recebe callback OAuth e salva tokens do usuario.
- `GET /auth/google/connections`: lista usuarios conectados via OAuth.
- Mirror local em SQLite para consultar resultado de sync e historico basico de canais/notificacoes.

## Setup local

```bash
cp .env.example .env
python -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

Documentacao interativa:

- Swagger: `http://127.0.0.1:8000/docs`
- Healthcheck: `http://127.0.0.1:8000/health`

## Configuracao Google

### Service account

1. Crie ou selecione um projeto no Google Cloud.
2. Habilite a Google Calendar API.
3. Crie uma service account e baixe a chave JSON.
4. Compartilhe o calendario alvo com o email da service account com permissao para alterar eventos.
5. Configure `.env`:

```bash
GOOGLE_CREDENTIALS_FILE="/absolute/path/to/service-account.json"
GOOGLE_CALENDAR_ID="calendar-id@group.calendar.google.com"
```

Para Google Workspace com domain-wide delegation, configure tambem:

```bash
GOOGLE_DELEGATED_SUBJECT="usuario@dominio.com"
```

### OAuth de usuario

Use OAuth quando a API precisa acessar o calendario real do usuario, sem pedir que ele compartilhe o calendario com uma service account.

No Google Cloud:

1. Habilite a Google Calendar API.
2. Configure a OAuth consent screen.
3. Crie um OAuth Client ID do tipo `Web application`.
4. Adicione a redirect URI local:

```text
http://127.0.0.1:8001/auth/google/callback
```

5. Configure `.env`:

```bash
GOOGLE_OAUTH_CLIENT_ID="seu-client-id.apps.googleusercontent.com"
GOOGLE_OAUTH_CLIENT_SECRET="seu-client-secret"
GOOGLE_OAUTH_REDIRECT_URI="http://127.0.0.1:8001/auth/google/callback"
GOOGLE_OAUTH_SCOPES="openid https://www.googleapis.com/auth/userinfo.email https://www.googleapis.com/auth/calendar.events"
GOOGLE_OAUTH_PROMPT_CONSENT=true
```

Tambem e possivel usar o arquivo baixado pelo Google:

```bash
GOOGLE_OAUTH_CLIENT_SECRETS_FILE="/absolute/path/client_secret.json"
```

Gerar URL de consentimento:

```bash
curl "http://127.0.0.1:8001/auth/google/login?user_id=demo-user&calendar_id=primary"
```

Abra `authorization_url` no navegador e autorize. O Google chamara `/auth/google/callback`; a API salva `refresh_token` em SQLite.

Depois use `user_id` nas operacoes:

```bash
curl "http://127.0.0.1:8001/appointments?user_id=demo-user&source=google"
curl -X POST "http://127.0.0.1:8001/sync/poll?user_id=demo-user"
curl -X POST "http://127.0.0.1:8001/sync/watch?user_id=demo-user"
```

Listar conexoes:

```bash
curl "http://127.0.0.1:8001/auth/google/connections"
```

## Modelo de estado

O estado de negocio do appointment e gravado no evento Google em:

```json
{
  "extendedProperties": {
    "private": {
      "app": "agenda-cheia",
      "appointment_state": "scheduled"
    }
  }
}
```

Estados aceitos: `scheduled`, `confirmed`, `cancelled`, `completed`, `no_show`.

## Exemplos

Criar appointment:

```bash
curl -X POST http://127.0.0.1:8000/appointments \
  -H "Content-Type: application/json" \
  -d '{
    "summary": "Consulta Ana",
    "description": "Primeira consulta",
    "start_at": "2026-08-20T14:00:00-03:00",
    "end_at": "2026-08-20T15:00:00-03:00",
    "state": "scheduled",
    "attendees": [{"email": "ana@example.com", "display_name": "Ana"}]
  }'
```

Atualizar appointment:

```bash
curl -X PATCH http://127.0.0.1:8000/appointments/{google_event_id} \
  -H "Content-Type: application/json" \
  -d '{"state": "confirmed", "summary": "Consulta Ana - confirmada"}'
```

Listar por estado:

```bash
curl "http://127.0.0.1:8000/appointments?state=confirmed"
```

Rodar polling incremental:

```bash
curl -X POST "http://127.0.0.1:8000/sync/poll"
```

## Push notifications

O Google Calendar envia notificacoes por `POST` para uma URL HTTPS publica. A notificacao nao traz o evento alterado no corpo; ela traz headers `X-Goog-*`. Por isso, o webhook desta API recebe a notificacao e chama o sync incremental para buscar as mudancas reais.

Configure:

```bash
GOOGLE_WEBHOOK_BASE_URL="https://sua-api-publica.com"
GOOGLE_WEBHOOK_TOKEN="token-aleatorio"
```

Crie o canal:

```bash
curl -X POST http://127.0.0.1:8000/sync/watch
```

Listar notificacoes recebidas:

```bash
curl "http://127.0.0.1:8000/webhooks/google-calendar/notifications?limit=50"
```

Acompanhar notificacoes por SSE:

```bash
curl -N "http://127.0.0.1:8000/webhooks/google-calendar/stream"
```

Observacoes praticas:

- A URL precisa ser HTTPS com certificado valido.
- Canais expiram; crie um novo antes do vencimento.
- Push notification nao e 100% garantido, entao mantenha `POST /sync/poll` agendado como fallback.

Referencias oficiais usadas:

- Google Calendar push notifications: https://developers.google.com/workspace/calendar/api/guides/push
- Google Calendar incremental sync: https://developers.google.com/workspace/calendar/api/guides/sync
- Google Calendar events.list: https://developers.google.com/workspace/calendar/api/v3/reference/events/list
- Google Calendar events.insert: https://developers.google.com/workspace/calendar/api/v3/reference/events/insert
- Google Calendar events.patch: https://developers.google.com/workspace/calendar/api/v3/reference/events/patch
