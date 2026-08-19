# Agenda Cheia

**O agente outbound que vende seus horários vagos.** Cancelou? O agente liga e chama no zap, revende o horário com desconto de última hora e trava com sinal via Pix — no-show zerado. Verticais: salões, barbearias, clínicas e estúdios de pilates/fitness/yoga (cancelamento de última hora em aula é rotina — e a lista de espera da turma é o comprador perfeito).

Landing page is bilingual (pt-BR default, EN via the PT|EN switch in the nav).

## Structure

- `landing/index.html` — landing page (pt-BR, single self-contained file — open directly in a browser)
- `agenda-cheia-google-calendar-api/` — FastAPI service integrated with Google Calendar for appointments, sync polling and push notifications
- `agenda-cheia-google-calendar-test-ui/` — Vite/React UI to exercise Google Calendar API operations and the webhook log stream
- `agenda-cheia-pix-test-ui/` — FastAPI/static UI to create Pix charges and inspect Woovi webhook calls in real time

## Core product loop

Live call → mid-call Pix on WhatsApp → payment webhook → slot flips green.
