import assert from 'node:assert/strict';
import { after, before, test } from 'node:test';
import { createServer } from 'vite';

let vite;
let api;
let chatModule;
before(async () => {
  vite = await createServer({ root: new URL('..', import.meta.url).pathname, configFile: new URL('../vite.config.ts', import.meta.url).pathname, appType: 'custom', logLevel: 'silent', server: { middlewareMode: true } });
  [api, chatModule] = await Promise.all([vite.ssrLoadModule('/src/auth/api.ts'), vite.ssrLoadModule('/src/astrology/AIChatPage.tsx')]);
});
after(async () => { await vite?.close(); });

const savedFetch = globalThis.fetch;

test('AI conversation API uses owned endpoints and bearer authentication', async () => {
  const calls = [];
  globalThis.fetch = async (url, init) => {
    calls.push({ url: String(url), init });
    if (init.method === 'DELETE') return new Response(null, { status: 204 });
    return new Response(JSON.stringify({ items: [], total: 0 }), { status: 200, headers: { 'Content-Type': 'application/json' } });
  };
  try {
    await api.createAIConversation('jwt', { profile_id: 'profile-1', chart_id: 'chart-2', astrology_system: 'vedic', language: 'ta' });
    await api.listAIConversations('jwt', 25, 5);
    await api.getAIConversation('jwt', 'conversation/a');
    await api.deleteAIConversation('jwt', 'conversation/a');
    assert.equal(calls[0].url, 'http://localhost:8000/api/v1/ai/conversations');
    assert.deepEqual(JSON.parse(calls[0].init.body), { profile_id: 'profile-1', chart_id: 'chart-2', astrology_system: 'vedic', language: 'ta' });
    assert.equal(calls[1].url, 'http://localhost:8000/api/v1/ai/conversations?limit=25&offset=5');
    assert.equal(calls[2].url, 'http://localhost:8000/api/v1/ai/conversations/conversation%2Fa');
    assert.equal(calls[3].init.method, 'DELETE');
    for (const { init } of calls) assert.equal(init.headers.Authorization, 'Bearer jwt');
  } finally { globalThis.fetch = savedFetch; }
});

test('streaming API sends authenticated message and parses fragmented SSE deltas and completion', async () => {
  let call;
  const structured = { status: 'missing_chart', answer: 'No completed chart is available.', answer_fact_ids: [], answer_rule_ids: [], sections: [], metadata: { engine_version: '1.0.0', knowledge_base_version: '1.0.0', system: 'vedic', division: 'D1', language: 'en', matched_rule_ids: [] } };
  const sse = 'event: metadata\ndata: {"status":"missing_chart","language":"en"}\n\nevent: delta\ndata: {"content":"வணக்கம் "}\n\nevent: delta\ndata: {"content":"there"}\n\nevent: done\ndata: ' + JSON.stringify({ message: { id: 'm1', role: 'assistant', content: 'வணக்கம் there', structured_response: structured }, usage: { daily_limit: 20, requests_used: 1, remaining: 19 } }) + '\n\n';
  globalThis.fetch = async (url, init) => {
    call = { url: String(url), init };
    const encoder = new TextEncoder();
    const chunks = [sse.slice(0, 19), sse.slice(19, 51), sse.slice(51)];
    return new Response(new ReadableStream({ start(controller) { for (const chunk of chunks) controller.enqueue(encoder.encode(chunk)); controller.close(); } }), { status: 200, headers: { 'Content-Type': 'text/event-stream' } });
  };
  const deltas = [];
  try {
    const result = await api.streamAIMessage('jwt', 'conv-1', 'question', value => deltas.push(value), 'request-key-1');
    assert.equal(call.url, 'http://localhost:8000/api/v1/ai/conversations/conv-1/messages/stream');
    assert.equal(call.init.headers.Authorization, 'Bearer jwt');
    assert.equal(call.init.headers['Idempotency-Key'], 'request-key-1');
    assert.deepEqual(JSON.parse(call.init.body), { content: 'question' });
    assert.deepEqual(deltas, ['வணக்கம் ', 'there']);
    assert.equal(result.usage.remaining, 19);
    assert.equal(result.message.structured_response.status, 'missing_chart');
  } finally { globalThis.fetch = savedFetch; }
});

test('SSE error events produce useful errors and EN/Tamil chat strings have matching keys', async () => {
  globalThis.fetch = async () => new Response('event: error\ndata: {"detail":"The response could not be completed. Please try again."}\n\n', { status: 200 });
  try {
    await assert.rejects(api.streamAIMessage('jwt', 'conv', 'question', () => {}), /response could not be completed/);
  } finally { globalThis.fetch = savedFetch; }
  const { aiChatText } = chatModule;
  assert.deepEqual(Object.keys(aiChatText.en).sort(), Object.keys(aiChatText.ta).sort());
  for (const [key, value] of Object.entries(aiChatText.ta)) assert.ok(value.trim(), `Tamil text is empty: ${key}`);
  assert.match(aiChatText.en.disclaimer, /not scientific certainty/);
  assert.match(aiChatText.ta.disclaimer, /அறிவியல் உறுதி/);
});

test('interrupted SSE connection rejects instead of treating partial assistant text as complete', async () => {
  globalThis.fetch = async () => {
    const encoder = new TextEncoder();
    return new Response(new ReadableStream({
      start(controller) {
        controller.enqueue(encoder.encode('event: delta\ndata: {"content":"partial"}\n\n'));
        setTimeout(() => controller.error(new Error('network interrupted')), 10);
      },
    }), { status: 200 });
  };
  const partial = [];
  try {
    await assert.rejects(api.streamAIMessage('jwt', 'conv', 'question', value => partial.push(value), 'request-key-2'));
    assert.deepEqual(partial, ['partial']);
  } finally { globalThis.fetch = savedFetch; }
});
