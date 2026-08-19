# WhatsApp connector

Standalone, demo-only WhatsApp transport built with
[Baileys](https://github.com/WhiskeySockets/Baileys). It is intentionally not
imported by the Vinext app or Cloudflare worker.

## Pair a personal account

Run `npm run whatsapp:pair`, then scan the terminal QR code in WhatsApp under
**Settings → Linked devices → Link a device**. The linked-device credentials
are stored in `.data/whatsapp/auth`, which is ignored by Git.

The pairing process must run on a normal Node.js host (for the demo, the team's
laptop). Baileys maintains a long-lived WebSocket and filesystem-backed auth
state, so it cannot run inside the project's Cloudflare worker.

## Use the connector later

```ts
import { WhatsAppConnector } from "./src/connectors/whatsapp";

const whatsapp = new WhatsAppConnector();
await whatsapp.connect();

await whatsapp.sendOffer({
  businessName: "Salão da Ju",
  clientName: "Ricardo",
  clientPhone: "+55 11 99999-0000",
  serviceName: "corte e barba",
  slotLabel: "hoje às 19h",
  originalPriceCents: 12_000,
  offerPriceCents: 9_600,
  offerValidForMinutes: 15,
  depositCents: 1_500,
});

await whatsapp.sendResultToOwner({
  ownerPhone: "+55 11 98888-0000",
  businessName: "Salão da Ju",
  clientName: "Ricardo",
  serviceName: "corte e barba",
  slotLabel: "hoje às 19h",
  outcome: "booked",
  offerPriceCents: 9_600,
  depositCents: 1_500,
});
```

Phone numbers must include their country code. Calling `connect()` is explicit;
constructing or importing the connector never opens a socket or sends a
message.

## Demo limitations

Baileys uses the unofficial WhatsApp Web protocol. Use only a dedicated or
low-risk account, contact opted-in recipients only, keep demo volume low, and
do not use it as the production transport. A production implementation should
move to the official WhatsApp Business Platform and a database-backed auth
strategy.
