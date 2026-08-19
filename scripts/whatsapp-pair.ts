import QRCode from "qrcode";

import { WhatsAppConnector } from "../src/connectors/whatsapp";

const connector = new WhatsAppConnector({
  onQrCode: async (qrCode) => {
    console.log("\nScan this QR code in WhatsApp → Linked devices:\n");
    console.log(await QRCode.toString(qrCode, { type: "terminal", small: true }));
  },
  onStatusChange: (status) => {
    if (status === "connecting" || status === "reconnecting") {
      console.log(`WhatsApp status: ${status}`);
    }
  },
});

async function shutdown(): Promise<void> {
  await connector.disconnect();
  process.exitCode = 0;
}

process.once("SIGINT", () => void shutdown());
process.once("SIGTERM", () => void shutdown());

try {
  await connector.connect();
  console.log("\nPersonal WhatsApp account paired successfully.");
  await connector.disconnect();
} catch (error) {
  console.error("Could not pair the WhatsApp account:", error);
  process.exitCode = 1;
}
