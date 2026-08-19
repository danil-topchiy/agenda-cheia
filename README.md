# Agenda Cheia

**O agente outbound que vende seus horários vagos.** Cancelou? O agente liga e chama no zap, revende o horário com desconto de última hora e trava com sinal via Pix — no-show zerado. Verticais: salões, barbearias, clínicas e estúdios de pilates/fitness/yoga (cancelamento de última hora em aula é rotina — e a lista de espera da turma é o comprador perfeito).

Landing page is bilingual (pt-BR default, EN via the PT|EN switch in the nav).

Hackathon São Paulo · Ago/2026 · Track: Small Businesses · Panel score: 7.1 (wow 8.0 / feasibility 6.5 / brazil 6.0)

## Structure

- `landing/index.html` — landing page (pt-BR, single self-contained file — open directly in a browser)
- `agenda-cheia-google-calendar-api/` — FastAPI service integrated with Google Calendar for appointments, sync polling and push notifications
- `hackthon-google-calendar-test-ui/` — Vite/React UI to exercise Google Calendar API operations and the webhook log stream
- `hackthon-pix-test-ui/` — FastAPI/static UI to create Pix charges and inspect Woovi webhook calls in real time
- `docs/IMPLEMENTATION-PLAN.md` — one-day build plan: architecture, slot state machine + policy harness, stack with fallbacks, night-before checklist, 12h schedule with cut lines, 3-min demo script, voice-agent system prompt draft, risk register, judge Q&A prep

## The non-negotiable core loop (never cut)

Live call → mid-call Pix on WhatsApp → payment webhook → slot flips green.

## Key decisions (see plan for rationale)

Vapi + ElevenLabs Flash pt-BR (Retell/Cartesia as hot spares) · Z-API ×3 warmed numbers (Twilio WA sandbox spare) · OpenPix/Woovi + a real R$0,50 Pix for the authentic notification sound · Node/TS Fastify orchestrator, first-payer-wins enforced in code, not in the prompt.
