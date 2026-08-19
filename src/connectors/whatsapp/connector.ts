import makeWASocket, {
  Browsers,
  DisconnectReason,
  useMultiFileAuthState as createMultiFileAuthState,
  type ConnectionState,
  type WASocket,
} from "baileys";
import pino, { type Logger } from "pino";

import { createOfferMessage, createOwnerResultMessage } from "./messages";
import { normalizePhoneNumber } from "./phone";
import type {
  WhatsAppCampaignResult,
  WhatsAppConnectionStatus,
  WhatsAppDeliveryReceipt,
  WhatsAppOffer,
} from "./types";

export interface WhatsAppConnectorOptions {
  authDirectory?: string;
  connectTimeoutMs?: number;
  maxReconnectAttempts?: number;
  logger?: Logger;
  onError?: (error: Error) => void;
  onQrCode?: (qrCode: string) => void | Promise<void>;
  onStatusChange?: (status: WhatsAppConnectionStatus) => void;
  verifyRecipients?: boolean;
}

const defaultAuthDirectory = ".data/whatsapp/auth";
const defaultConnectTimeoutMs = 120_000;
const reconnectBaseDelayMs = 1_000;
const reconnectMaxDelayMs = 15_000;

function asError(value: unknown): Error {
  return value instanceof Error ? value : new Error(String(value));
}

function disconnectStatusCode(error: unknown): number | undefined {
  if (!error || typeof error !== "object") {
    return undefined;
  }

  const output = "output" in error ? error.output : undefined;

  if (!output || typeof output !== "object" || !("statusCode" in output)) {
    return undefined;
  }

  return typeof output.statusCode === "number" ? output.statusCode : undefined;
}

function isTerminalDisconnect(statusCode: number | undefined): boolean {
  return (
    statusCode === DisconnectReason.loggedOut ||
    statusCode === DisconnectReason.badSession ||
    statusCode === DisconnectReason.connectionReplaced ||
    statusCode === DisconnectReason.multideviceMismatch ||
    statusCode === DisconnectReason.forbidden
  );
}

export class WhatsAppConnector {
  readonly #options: Required<
    Pick<
      WhatsAppConnectorOptions,
      | "authDirectory"
      | "connectTimeoutMs"
      | "maxReconnectAttempts"
      | "verifyRecipients"
    >
  > &
    Omit<
      WhatsAppConnectorOptions,
      | "authDirectory"
      | "connectTimeoutMs"
      | "maxReconnectAttempts"
      | "verifyRecipients"
    >;
  readonly #logger: Logger;

  #connectPromise?: Promise<void>;
  #connectReject?: (error: Error) => void;
  #connectResolve?: () => void;
  #connectTimer?: ReturnType<typeof setTimeout>;
  #manualDisconnect = false;
  #reconnectAttempts = 0;
  #reconnectTimer?: ReturnType<typeof setTimeout>;
  #socket?: WASocket;
  #status: WhatsAppConnectionStatus = "idle";

  constructor(options: WhatsAppConnectorOptions = {}) {
    this.#options = {
      ...options,
      authDirectory: options.authDirectory ?? defaultAuthDirectory,
      connectTimeoutMs: options.connectTimeoutMs ?? defaultConnectTimeoutMs,
      maxReconnectAttempts: options.maxReconnectAttempts ?? 5,
      verifyRecipients: options.verifyRecipients ?? true,
    };
    this.#logger = options.logger ?? pino({ level: "warn" });
  }

  get status(): WhatsAppConnectionStatus {
    return this.#status;
  }

  async connect(): Promise<void> {
    if (this.#status === "connected") {
      return;
    }

    if (this.#connectPromise) {
      return this.#connectPromise;
    }

    this.#manualDisconnect = false;
    this.#clearReconnectTimer();
    this.#reconnectAttempts = 0;
    this.#connectPromise = new Promise<void>((resolve, reject) => {
      this.#connectResolve = resolve;
      this.#connectReject = reject;
      this.#connectTimer = setTimeout(() => {
        const error = new Error(
          `WhatsApp connection timed out after ${this.#options.connectTimeoutMs}ms`,
        );
        this.#manualDisconnect = true;
        const socket = this.#socket;
        this.#socket = undefined;
        if (socket) {
          void socket.end(error).catch((closeError: unknown) => {
            this.#reportError(asError(closeError));
          });
        }
        this.#setStatus("disconnected");
        this.#rejectConnect(error);
      }, this.#options.connectTimeoutMs);
    });

    const pendingConnection = this.#connectPromise;
    void this.#openSocket().catch((error: unknown) => {
      const connectionError = asError(error);
      this.#setStatus("disconnected");
      this.#rejectConnect(connectionError);
      this.#reportError(connectionError);
    });

    try {
      await pendingConnection;
    } finally {
      if (this.#connectPromise === pendingConnection) {
        this.#connectPromise = undefined;
      }
    }
  }

  async disconnect(): Promise<void> {
    this.#manualDisconnect = true;
    this.#clearReconnectTimer();
    this.#rejectConnect(new Error("WhatsApp connection closed by caller"));

    const socket = this.#socket;
    this.#socket = undefined;

    if (socket) {
      await socket.end(undefined);
    }

    this.#setStatus("disconnected");
  }

  async logout(): Promise<void> {
    this.#manualDisconnect = true;
    this.#clearReconnectTimer();

    const socket = this.#requireConnectedSocket();
    await socket.logout("Agenda Cheia connector logout");
    this.#socket = undefined;
    this.#setStatus("logged_out");
  }

  async sendOffer(offer: WhatsAppOffer): Promise<WhatsAppDeliveryReceipt> {
    return this.#sendText(offer.clientPhone, createOfferMessage(offer));
  }

  async sendResultToOwner(
    result: WhatsAppCampaignResult,
  ): Promise<WhatsAppDeliveryReceipt> {
    return this.#sendText(
      result.ownerPhone,
      createOwnerResultMessage(result),
    );
  }

  async #openSocket(): Promise<void> {
    if (this.#manualDisconnect) {
      return;
    }

    this.#setStatus(this.#reconnectAttempts > 0 ? "reconnecting" : "connecting");
    const { state, saveCreds } = await createMultiFileAuthState(
      this.#options.authDirectory,
    );
    const socket = makeWASocket({
      auth: state,
      browser: Browsers.macOS("Google Chrome"),
      logger: this.#logger,
      markOnlineOnConnect: false,
      syncFullHistory: false,
    });

    this.#socket = socket;
    socket.ev.on("creds.update", saveCreds);
    socket.ev.on("connection.update", (update) => {
      this.#handleConnectionUpdate(socket, update);
    });
  }

  #handleConnectionUpdate(
    socket: WASocket,
    update: Partial<ConnectionState>,
  ): void {
    if (socket !== this.#socket) {
      return;
    }

    if (update.qr) {
      this.#setStatus("pairing");
      void Promise.resolve(this.#options.onQrCode?.(update.qr)).catch(
        (error: unknown) => this.#reportError(asError(error)),
      );
    }

    if (update.connection === "connecting" && !update.qr) {
      this.#setStatus(
        this.#reconnectAttempts > 0 ? "reconnecting" : "connecting",
      );
      return;
    }

    if (update.connection === "open") {
      this.#reconnectAttempts = 0;
      this.#setStatus("connected");
      this.#resolveConnect();
      return;
    }

    if (update.connection !== "close") {
      return;
    }

    this.#socket = undefined;

    if (this.#manualDisconnect) {
      this.#setStatus("disconnected");
      return;
    }

    const error = update.lastDisconnect?.error;
    const statusCode = disconnectStatusCode(error);

    if (isTerminalDisconnect(statusCode)) {
      const disconnectError = new Error(
        `WhatsApp session ended and must be paired again (status ${statusCode ?? "unknown"})`,
        { cause: error },
      );
      this.#setStatus(
        statusCode === DisconnectReason.loggedOut ? "logged_out" : "disconnected",
      );
      this.#rejectConnect(disconnectError);
      this.#reportError(disconnectError);
      return;
    }

    this.#scheduleReconnect(error);
  }

  #scheduleReconnect(cause: unknown): void {
    if (this.#manualDisconnect || this.#reconnectTimer) {
      return;
    }

    if (this.#reconnectAttempts >= this.#options.maxReconnectAttempts) {
      const error = new Error(
        `WhatsApp reconnect failed after ${this.#options.maxReconnectAttempts} attempts`,
        { cause },
      );
      this.#setStatus("disconnected");
      this.#rejectConnect(error);
      this.#reportError(error);
      return;
    }

    this.#reconnectAttempts += 1;
    this.#setStatus("reconnecting");
    const delay = Math.min(
      reconnectBaseDelayMs * 2 ** (this.#reconnectAttempts - 1),
      reconnectMaxDelayMs,
    );

    this.#reconnectTimer = setTimeout(() => {
      this.#reconnectTimer = undefined;
      void this.#openSocket().catch((error: unknown) => {
        this.#reportError(asError(error));
        this.#scheduleReconnect(error);
      });
    }, delay);
  }

  async #sendText(
    phoneNumber: string,
    text: string,
  ): Promise<WhatsAppDeliveryReceipt> {
    const socket = this.#requireConnectedSocket();
    const normalizedPhone = normalizePhoneNumber(phoneNumber);
    let jid = `${normalizedPhone}@s.whatsapp.net`;

    if (this.#options.verifyRecipients) {
      const [recipient] = (await socket.onWhatsApp(normalizedPhone)) ?? [];

      if (!recipient?.exists) {
        throw new Error(`Phone number ${normalizedPhone} is not on WhatsApp`);
      }

      jid = recipient.jid;
    }

    const message = await socket.sendMessage(jid, { text });
    const messageId = message?.key.id;

    if (!messageId) {
      throw new Error(`WhatsApp did not acknowledge the message to ${normalizedPhone}`);
    }

    return {
      messageId,
      recipientPhone: normalizedPhone,
      sentAt: new Date(),
    };
  }

  #requireConnectedSocket(): WASocket {
    if (this.#status !== "connected" || !this.#socket) {
      throw new Error("WhatsApp connector is not connected");
    }

    return this.#socket;
  }

  #setStatus(status: WhatsAppConnectionStatus): void {
    if (this.#status === status) {
      return;
    }

    this.#status = status;
    this.#options.onStatusChange?.(status);
  }

  #resolveConnect(): void {
    if (this.#connectTimer) {
      clearTimeout(this.#connectTimer);
      this.#connectTimer = undefined;
    }

    const resolve = this.#connectResolve;
    this.#connectResolve = undefined;
    this.#connectReject = undefined;
    resolve?.();
  }

  #rejectConnect(error: Error): void {
    if (this.#connectTimer) {
      clearTimeout(this.#connectTimer);
      this.#connectTimer = undefined;
    }

    const reject = this.#connectReject;
    this.#connectResolve = undefined;
    this.#connectReject = undefined;
    reject?.(error);
  }

  #clearReconnectTimer(): void {
    if (this.#reconnectTimer) {
      clearTimeout(this.#reconnectTimer);
      this.#reconnectTimer = undefined;
    }
  }

  #reportError(error: Error): void {
    this.#logger.error({ err: error }, error.message);
    this.#options.onError?.(error);
  }
}
