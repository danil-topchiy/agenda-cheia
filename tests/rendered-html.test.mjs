import assert from "node:assert/strict";
import test from "node:test";

async function render(pathname = "/") {
  const workerUrl = new URL("../dist/server/index.js", import.meta.url);
  workerUrl.searchParams.set("test", `${process.pid}-${Date.now()}-${pathname}`);
  const { default: worker } = await import(workerUrl.href);

  return worker.fetch(
    new Request(`http://localhost${pathname}`, {
      headers: { accept: "text/html" },
    }),
    {
      ASSETS: {
        fetch: async () => new Response("Not found", { status: 404 }),
      },
    },
    {
      waitUntil() {},
      passThroughOnException() {},
    },
  );
}

test("server-renders the agenda dashboard", async () => {
  const response = await render();
  assert.equal(response.status, 200);
  assert.match(response.headers.get("content-type") ?? "", /^text\/html\b/i);

  const html = await response.text();
  assert.match(html, /<title>Agenda \| Agenda Cheia<\/title>/i);
  assert.match(html, /Próximos horários/);
  assert.match(html, /Cancelamentos/);
  assert.match(html, /Dados de demonstração/);
  assert.doesNotMatch(html, /codex-preview|Your site is taking shape|Building your site/i);
});

test("server-renders the customers page", async () => {
  const response = await render("/customers");
  assert.equal(response.status, 200);

  const html = await response.text();
  assert.match(html, /<title>Clientes \| Agenda Cheia<\/title>/i);
  assert.match(html, /Base unificada/);
  assert.match(html, /Importar clientes/);
  assert.match(html, /Marina Costa/);
});
