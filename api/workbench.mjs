import { createHash, timingSafeEqual } from 'node:crypto';

const digest = value => createHash('sha256').update(value).digest();

// Native Sandbox REST calls, matching @vercel/sandbox 3.9.1's published client.
// No provider SDK, key, or Sandbox control token is sent to the browser.
export async function launch(env, fetcher = fetch) {
  const token = env.VERCEL_OIDC_TOKEN;
  if (!token || !env.OPENAI_API_KEY || !env.VERCEL_PROJECT_ID || !env.VERCEL_TEAM_ID) {
    throw Object.assign(new Error('Server configuration unavailable'), {
      stage: 'configuration',
      missing: ['VERCEL_OIDC_TOKEN', 'OPENAI_API_KEY', 'VERCEL_PROJECT_ID', 'VERCEL_TEAM_ID'].filter(key => !env[key]),
    });
  }
  const base = 'https://vercel.com/api';
  const project = encodeURIComponent(env.VERCEL_PROJECT_ID);
  const team = encodeURIComponent(env.VERCEL_TEAM_ID);
  const named = `/v2/sandboxes/recoup-workbench?projectId=${project}&teamId=${team}`;
  async function api(path, method = 'GET', body) {
    const response = await fetcher(base + path, {
      method,
      headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
      ...(body === undefined ? {} : { body: JSON.stringify(body) }),
      signal: AbortSignal.timeout(90000),
    });
    if (!response.ok) throw Object.assign(new Error('Sandbox request unavailable'), { stage: 'sandbox_http', status: response.status });
    return response.json();
  }
  // Retain the environment snapshot indefinitely; application data lives on the Drive.
  await api(named, 'PATCH', { persistent: true, snapshotExpiration: 0 });
  const box = await api(named + '&resume=true');
  const session = box.session?.id;
  if (!/^sbx_[A-Za-z0-9]+$/.test(session || '')) throw new Error('Invalid session');
  const commandPath = `/v2/sandboxes/sessions/${session}/cmd`;
  const started = await api(commandPath + `?teamId=${team}`, 'POST', {
    command: '/data/venv/bin/python',
    args: ['-m', 'recoup.ui.start_server'],
    cwd: '/data/app',
    env: {
      RECOUP_LLM: 'live',
      RECOUP_MODEL: 'claude-haiku-5-5',
      OPENAI_BASE_URL: 'https://api.anthropic.com/v1/',
      OPENAI_API_KEY: env.OPENAI_API_KEY,
      RECOUP_ACCESS_SECRET: env.RECOUP_ACCESS_SECRET,
      RECOUP_DB: '/data/recoup.db',
      RECOUP_VISION: '0',
      PYTHONPATH: '/data/app',
    },
    timeout: 30000,
  });
  const command = started.command?.id;
  if (!/^cmd_[A-Za-z0-9]+$/.test(command || '')) throw new Error('Invalid command');
  const finished = await api(`${commandPath}/${command}?wait=true&teamId=${team}`);
  if (finished.command?.exitCode !== 0) throw new Error('Workspace startup failed');
  const route = box.routes?.find(item => item.port === 8501)?.url;
  if (!/^https:\/\/sb-[a-z0-9]+\.vercel\.run\/?$/.test(route || '')) {
    throw new Error('Invalid workspace route');
  }
  return route;
}

export function createHandler(env = process.env, fetcher = fetch) {
  return async (req, res) => {
    res.setHeader('Cache-Control', 'no-store');
    res.setHeader('Referrer-Policy', 'same-origin');
    if (req.method !== 'POST') return res.status(405).send('Use the workspace sign-in form.');
    if (req.headers.origin !== `https://${req.headers.host}`) {
      return res.status(403).send('Please use the workspace sign-in form.');
    }
    const expected = env.RECOUP_ACCESS_SECRET || '';
    if (expected.length < 32 || expected === env.OPENAI_API_KEY) {
      return res.status(503).send('Workspace access is not configured.');
    }
    let body = req.body;
    if (typeof body === 'string' && body.length <= 4096) {
      body = Object.fromEntries(new URLSearchParams(body));
    }
    const candidate = body?.secret;
    if (typeof candidate !== 'string' || candidate.length > 1024 ||
        !timingSafeEqual(digest(candidate), digest(expected))) {
      return res.status(401).send('Unable to sign in. Return to the form and try again.');
    }
    try {
      // Vercel provides a fresh OIDC token in its trusted request context.
      // This is the resolution used by @vercel/oidc 4.0.8; no caller header is trusted.
      const context = globalThis[Symbol.for('@vercel/request-context')]?.get?.();
      const token = context?.headers?.['x-vercel-oidc-token'] ?? env.VERCEL_OIDC_TOKEN;
      const url = await launch({ ...env, VERCEL_OIDC_TOKEN: token }, fetcher);
      res.setHeader('Location', url);
      return res.status(303).end();
    } catch (error) {
      // Never return or log Sandbox bodies, environment variables, tokens, or keys.
      console.warn('Recoup startup unavailable', {
        stage: error.stage === 'configuration' ? 'configuration' : error.stage === 'sandbox_http' ? 'sandbox_http' : 'startup',
        ...(Number.isInteger(error.status) ? { status: error.status } : {}),
        ...(error.stage === 'configuration' ? { missing: error.missing } : {}),
      });
      return res.status(503).send('Workspace could not start. Please try again shortly.');
    }
  };
}

export default createHandler();
