import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

test("protects both product pages and registers signed-in users", async () => {
  const [agendaPage, customersPage] = await Promise.all([
    readFile(new URL("../app/page.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/customers/page.tsx", import.meta.url), "utf8"),
  ]);

  for (const page of [agendaPage, customersPage]) {
    assert.match(page, /export const dynamic = "force-dynamic"/);
    assert.match(page, /requireChatGPTUser\(/);
    assert.match(page, /await registerUser\(/);
  }
});

test("defines the users, clients, and schedule tables", async () => {
  const schema = await readFile(new URL("../db/schema.ts", import.meta.url), "utf8");

  assert.match(schema, /sqliteTable\("users"/);
  assert.match(schema, /sqliteTable\(\s*"clients"/);
  assert.match(schema, /sqliteTable\(\s*"schedule"/);
  assert.match(schema, /rescheduledFromId/);
});
