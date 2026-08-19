const allowedPhoneCharacters = /^[+\d\s().-]+$/;
const e164Digits = /^[1-9]\d{7,14}$/;

export function normalizePhoneNumber(phoneNumber: string): string {
  const input = phoneNumber.trim();

  if (!input || !allowedPhoneCharacters.test(input)) {
    throw new Error("Phone number must contain only E.164 phone characters");
  }

  const normalized = input.replace(/\D/g, "");

  if (!e164Digits.test(normalized)) {
    throw new Error(
      "Phone number must include its country code and contain 8 to 15 digits",
    );
  }

  return normalized;
}
