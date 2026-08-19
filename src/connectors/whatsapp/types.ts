export type WhatsAppConnectionStatus =
  | "idle"
  | "connecting"
  | "pairing"
  | "connected"
  | "reconnecting"
  | "disconnected"
  | "logged_out";

export interface WhatsAppOffer {
  businessName: string;
  clientName: string;
  clientPhone: string;
  serviceName: string;
  slotLabel: string;
  originalPriceCents: number;
  offerPriceCents: number;
  offerValidForMinutes: number;
  depositCents?: number;
  paymentUrl?: string;
}

export type WhatsAppCampaignOutcome =
  | "booked"
  | "declined"
  | "expired"
  | "failed";

export interface WhatsAppCampaignResult {
  ownerPhone: string;
  businessName: string;
  clientName: string;
  serviceName: string;
  slotLabel: string;
  outcome: WhatsAppCampaignOutcome;
  offerPriceCents: number;
  depositCents?: number;
  details?: string;
}

export interface WhatsAppDeliveryReceipt {
  messageId: string;
  recipientPhone: string;
  sentAt: Date;
}
