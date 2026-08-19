# Hackthon Google Calendar Test UI

UI local para testar a `agenda-cheia-google-calendar-api`.

## Rodar

```bash
npm install
npm run dev
```

Abra a URL exibida pelo Vite, normalmente:

```text
http://127.0.0.1:5174
```

Configure a URL da API no topo da tela. Default neste workspace:

```text
http://127.0.0.1:8001
```

## Funcionalidades

- Criar appointment.
- Atualizar appointment.
- Buscar/listar appointments por estado.
- Rodar sync incremental ou full sync.
- Criar/parar watch channel do Google Calendar.
- Enviar webhook sintético para `POST /webhooks/google-calendar`.
- Acompanhar webhook logs por SSE em `GET /webhooks/google-calendar/stream`.
