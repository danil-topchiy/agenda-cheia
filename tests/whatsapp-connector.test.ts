import assert from "node:assert/strict";
import test from "node:test";

import {
  WhatsAppConnector,
  createOfferMessage,
  createOwnerResultMessage,
  normalizePhoneNumber,
  type WhatsAppCampaignResult,
  type WhatsAppOffer,
} from "../src/connectors/whatsapp";

const offer: WhatsAppOffer = {
  businessName: "Salão da Ju",
  clientName: "Ricardo",
  clientPhone: "+55 (11) 99999-0000",
  serviceName: "corte e barba",
  slotLabel: "hoje às 19h",
  originalPriceCents: 12_000,
  offerPriceCents: 9_600,
  offerValidForMinutes: 15,
  depositCents: 1_500,
};

test("normalizes E.164 phone numbers for WhatsApp", () => {
  assert.equal(normalizePhoneNumber("+55 (11) 99999-0000"), "5511999990000");
  assert.throws(() => normalizePhoneNumber("11 9999"), /country code/);
  assert.throws(() => normalizePhoneNumber("+55 call-me"), /E\.164/);
});

test("creates a pt-BR client offer with urgency and deposit", () => {
  const message = createOfferMessage(offer);

  assert.match(message, /assistente virtual do \*Salão da Ju\*/);
  assert.match(message, /corte e barba/);
  assert.match(message, /R\$ 120,00/);
  assert.match(message, /R\$ 96,00/);
  assert.match(message, /20% off/);
  assert.match(message, /15 minutos/);
  assert.match(message, /sinal é de \*R\$ 15,00\*/);
  assert.match(message, /Responda \*QUERO\*/);
});

test("adds a validated payment URL when one is available", () => {
  const message = createOfferMessage({
    ...offer,
    paymentUrl: "https://pay.example/charge/123",
  });

  assert.match(message, /https:\/\/pay\.example\/charge\/123/);
  assert.throws(
    () => createOfferMessage({ ...offer, paymentUrl: "javascript:alert(1)" }),
    /http or https/,
  );
});

test("creates a concise booked result for the business owner", () => {
  const result: WhatsAppCampaignResult = {
    ownerPhone: "+55 11 98888-0000",
    businessName: "Salão da Ju",
    clientName: "Ricardo",
    serviceName: "corte e barba",
    slotLabel: "hoje às 19h",
    outcome: "booked",
    offerPriceCents: 9_600,
    depositCents: 1_500,
  };
  const message = createOwnerResultMessage(result);

  assert.match(message, /✅ \*Horário recuperado/);
  assert.match(message, /Reserva confirmada/);
  assert.match(message, /Cliente: Ricardo/);
  assert.match(message, /Valor: R\$ 96,00/);
  assert.match(message, /Sinal: R\$ 15,00/);
});

test("does not connect or send as an import side effect", async () => {
  const connector = new WhatsAppConnector();

  assert.equal(connector.status, "idle");
  await assert.rejects(connector.sendOffer(offer), /not connected/);
  assert.equal(connector.status, "idle");
});
