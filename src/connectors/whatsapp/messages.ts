import type {
  WhatsAppCampaignOutcome,
  WhatsAppCampaignResult,
  WhatsAppOffer,
} from "./types";

const outcomeCopy: Record<
  WhatsAppCampaignOutcome,
  { icon: string; title: string; label: string }
> = {
  booked: {
    icon: "✅",
    title: "Horário recuperado",
    label: "Reserva confirmada",
  },
  declined: {
    icon: "↩️",
    title: "Oferta recusada",
    label: "Cliente não aceitou a oferta",
  },
  expired: {
    icon: "⏰",
    title: "Oferta encerrada",
    label: "Prazo da oferta expirou",
  },
  failed: {
    icon: "⚠️",
    title: "Falha no contato",
    label: "Não foi possível concluir o envio",
  },
};

function cleanSingleLine(value: string, fieldName: string): string {
  const cleaned = value.replace(/\s+/g, " ").trim();

  if (!cleaned) {
    throw new Error(`${fieldName} is required`);
  }

  return cleaned;
}

function assertPositiveInteger(value: number, fieldName: string): void {
  if (!Number.isSafeInteger(value) || value <= 0) {
    throw new Error(`${fieldName} must be a positive integer`);
  }
}

function formatCurrency(cents: number): string {
  assertPositiveInteger(cents, "price in cents");

  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
  })
    .format(cents / 100)
    .replace(/\u00a0/g, " ");
}

function validatePaymentUrl(paymentUrl: string): string {
  const url = new URL(paymentUrl);

  if (url.protocol !== "https:" && url.protocol !== "http:") {
    throw new Error("paymentUrl must use http or https");
  }

  return url.toString();
}

export function createOfferMessage(offer: WhatsAppOffer): string {
  const businessName = cleanSingleLine(offer.businessName, "businessName");
  const clientName = cleanSingleLine(offer.clientName, "clientName");
  const serviceName = cleanSingleLine(offer.serviceName, "serviceName");
  const slotLabel = cleanSingleLine(offer.slotLabel, "slotLabel");

  assertPositiveInteger(offer.originalPriceCents, "originalPriceCents");
  assertPositiveInteger(offer.offerPriceCents, "offerPriceCents");
  assertPositiveInteger(offer.offerValidForMinutes, "offerValidForMinutes");

  if (offer.offerPriceCents > offer.originalPriceCents) {
    throw new Error("offerPriceCents cannot exceed originalPriceCents");
  }

  if (offer.depositCents !== undefined) {
    assertPositiveInteger(offer.depositCents, "depositCents");
  }

  const discount = Math.round(
    (1 - offer.offerPriceCents / offer.originalPriceCents) * 100,
  );
  const priceLine =
    discount > 0
      ? `~${formatCurrency(offer.originalPriceCents)}~ → *${formatCurrency(offer.offerPriceCents)}* (${discount}% off)`
      : `*${formatCurrency(offer.offerPriceCents)}*`;
  const depositLine = offer.depositCents
    ? `\nPara reservar, o sinal é de *${formatCurrency(offer.depositCents)}* e será descontado do total.`
    : "";
  const paymentLine = offer.paymentUrl
    ? `\n\nLink para o sinal: ${validatePaymentUrl(offer.paymentUrl)}`
    : "";

  return [
    `Oi, ${clientName}! Aqui é a assistente virtual do *${businessName}*. 👋`,
    "",
    `Abriu um horário para *${serviceName}* ${slotLabel}:`,
    priceLine,
    "",
    `Essa oferta fica disponível por *${offer.offerValidForMinutes} minutos*.${depositLine}`,
    "",
    "Quer aproveitar? Responda *QUERO* por aqui.",
    paymentLine,
  ]
    .filter((line, index, lines) => line !== "" || lines[index - 1] !== "")
    .join("\n")
    .trim();
}

export function createOwnerResultMessage(
  result: WhatsAppCampaignResult,
): string {
  const copy = outcomeCopy[result.outcome];
  const businessName = cleanSingleLine(result.businessName, "businessName");
  const clientName = cleanSingleLine(result.clientName, "clientName");
  const serviceName = cleanSingleLine(result.serviceName, "serviceName");
  const slotLabel = cleanSingleLine(result.slotLabel, "slotLabel");

  assertPositiveInteger(result.offerPriceCents, "offerPriceCents");

  if (result.depositCents !== undefined) {
    assertPositiveInteger(result.depositCents, "depositCents");
  }

  const lines = [
    `${copy.icon} *${copy.title} — ${businessName}*`,
    "",
    `Resultado: ${copy.label}`,
    `Cliente: ${clientName}`,
    `Serviço: ${serviceName}`,
    `Horário: ${slotLabel}`,
    `Valor: ${formatCurrency(result.offerPriceCents)}`,
  ];

  if (result.depositCents !== undefined) {
    lines.push(`Sinal: ${formatCurrency(result.depositCents)}`);
  }

  if (result.details?.trim()) {
    lines.push("", `Detalhes: ${cleanSingleLine(result.details, "details")}`);
  }

  return lines.join("\n");
}
