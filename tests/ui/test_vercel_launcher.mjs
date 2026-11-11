import assert from 'node:assert/strict';
import { test } from 'node:test';
import { createHandler, launch } from '../../api/workbench.mjs';

const env = {
  RECOUP_ACCESS_SECRET: 'synthetic-access-secret-at-least-32-characters',
  OPENAI_API_KEY: 'synthetic-provider-key',
  VERCEL_OIDC_TOKEN: 'synthetic-project-token',
  VERCEL_TEAM_ID: 'synthetic-team',
  VERCEL_PROJECT_ID: 'synthetic-project',
};
const route = 'https://sb-synthetic.vercel.run';
const reply = body => ({ ok: true, json: async () => body });
function response() {
  return {
    headers: {}, code: 200, body: '',
    setHeader(key, value) { this.headers[key] = value; },
    status(code) { this.code = code; return this; },
    send(body) { this.body = body; return this; },
    end() { return this; },
  };
}
function request(secret = env.RECOUP_ACCESS_SECRET) {
  return { method: 'POST', headers: { origin: 'https://recoup.example', host: 'recoup.example' }, body: { secret } };
}

test('invalid secret, absent auth, wrong origin and missing configuration never reach Sandbox', async () => {
  let calls = 0;
  const fetcher = async () => { calls++; throw new Error('network forbidden'); };
  const cases = [
    [{ ...request(), method: 'GET' }, env, 405],
    [request('wrong'), env, 401],
    [{ ...request(), body: {} }, env, 401],
    [{ ...request(), headers: { host: 'recoup.example', origin: 'https://stranger.example' } }, env, 403],
    [request(), { ...env, RECOUP_ACCESS_SECRET: '' }, 503],
    [request(), { ...env, RECOUP_ACCESS_SECRET: env.OPENAI_API_KEY }, 503],
  ];
  for (const [req, config, status] of cases) {
    const res = response();
    await createHandler(config, fetcher)(req, res);
    assert.equal(res.code, status);
    assert.equal(res.headers['Cache-Control'], 'no-store');
    assert.equal(res.headers['Referrer-Policy'], 'same-origin');
  }
  assert.equal(calls, 0);
});

test('resume, bounded startup and redirect use server-only credentials', async () => {
  const calls = [];
  const responses = [
    {},
    { session: { id: 'sbx_synthetic' }, routes: [{ port: 8501, url: route }] },
    { command: { id: 'cmd_synthetic' } },
    { command: { exitCode: 0 } },
  ];
  const fetcher = async (url, options) => { calls.push({ url, options }); return reply(responses.shift()); };
  const res = response();
  await createHandler(env, fetcher)({ ...request(), body: `secret=${env.RECOUP_ACCESS_SECRET}` }, res);
  assert.equal(res.code, 303);
  assert.equal(res.headers.Location, route);
  assert.equal(calls.length, 4);
  assert.match(calls[1].url, /resume=true/);
  const command = JSON.parse(calls[2].options.body);
  assert.equal(command.env.OPENAI_API_KEY, env.OPENAI_API_KEY);
  assert.equal(command.env.RECOUP_MODEL, 'claude-haiku-5-5');
  assert.equal(command.env.OPENAI_BASE_URL, 'https://api.anthropic.com/v1/');
  assert.deepEqual(command.args, ['-m', 'recoup.ui.start_server']);
  assert.equal(command.timeout, 30000);
  for (const secret of [env.OPENAI_API_KEY, env.VERCEL_OIDC_TOKEN, env.RECOUP_ACCESS_SECRET]) {
    assert.ok(!JSON.stringify(res).includes(secret));
  }
});

test('provider/control errors and unexpected routes are never reflected or followed', async () => {
  for (const bad of ['failure', 'route', 'startup']) {
    let count = 0;
    const fetcher = async () => {
      count++;
      if (bad === 'failure') throw new Error(env.OPENAI_API_KEY);
      if (count === 2) return reply({ session: { id: 'sbx_synthetic' }, routes: [{ port: 8501, url: bad === 'route' ? 'https://stranger.example' : route }] });
      if (count === 3) return reply({ command: { id: 'cmd_synthetic' } });
      if (count === 4) return reply({ command: { exitCode: bad === 'startup' ? 1 : 0 } });
      return reply({});
    };
    const res = response();
    await createHandler(env, fetcher)(request(), res);
    assert.equal(res.code, 503);
    assert.ok(!JSON.stringify(res).includes(env.OPENAI_API_KEY));
    assert.equal(res.headers.Location, undefined);
  }
});

test('missing control token fails without network', async () => {
  await assert.rejects(launch({ ...env, VERCEL_OIDC_TOKEN: '' }, async () => assert.fail('network')));
});

test('trusted runtime context supplies a fresh token without trusting browser headers', async () => {
  const symbol = Symbol.for('@vercel/request-context');
  const original = globalThis[symbol];
  let usedToken;
  globalThis[symbol] = { get: () => ({ headers: { 'x-vercel-oidc-token': 'fresh-runtime-token' } }) };
  try {
    const fetcher = async (_url, options) => {
      usedToken = options.headers.Authorization;
      return { ok: false, status: 503 };
    };
    const req = request();
    req.headers['x-vercel-oidc-token'] = 'untrusted-browser-token';
    const res = response();
    await createHandler({ ...env, VERCEL_OIDC_TOKEN: '' }, fetcher)(req, res);
    assert.equal(usedToken, 'Bearer fresh-runtime-token');
    assert.equal(res.code, 503);
    assert.ok(!JSON.stringify(res).includes('fresh-runtime-token'));
  } finally {
    if (original === undefined) delete globalThis[symbol]; else globalThis[symbol] = original;
  }
});
