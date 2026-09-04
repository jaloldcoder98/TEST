/**
 * Phase 0 — cross-site iframe cookie simulation.
 *
 * Telegram Web (web.telegram.org in a normal browser) embeds a Mini App in a cross-site
 * <iframe>; the native iOS/Android/Desktop clients load it as a top-level document. That single
 * difference decides whether the refresh cookie in docs/DECISIONS.md D-13 exists at all. We have
 * no physical machine running Telegram Web, so this reproduces the *browser* half of that
 * situation directly: two genuinely different registrable domains over HTTPS, the app embedded
 * in the other one, with third-party cookies allowed and then blocked.
 *
 * What it can tell us: how Chromium treats `__Host-`, `SameSite=None` and `Partitioned` in a
 * third-party frame, and whether Origin/Referer survive. What it cannot tell us: anything about
 * Telegram's own wrapper, Safari's ITP, or Firefox's Total Cookie Protection — see the caveats
 * in docs/TELEGRAM_WEBVIEW_MATRIX.md. It is evidence about the browser, not a substitute for
 * the real client.
 *
 *   node tools/webview-sim/run.mjs            # human-readable
 *   node tools/webview-sim/run.mjs --json     # machine-readable, for the matrix doc
 */

import { createServer } from 'node:https';
import { execFileSync } from 'node:child_process';
import { mkdtempSync, readFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { chromium } from 'playwright';

// Cross-site means different *sites*, not different ports: two ports on `localhost` are the
// same site and would silently test nothing. `127.0.0.1` (an IP, whose site is the IP itself)
// and `localhost` (a registrable domain) are genuinely cross-site to Chromium, and both are
// reachable here — invented hostnames such as `app.test` are not, because this sandbox's DNS
// swallows names it does not know. See the caveats in docs/TELEGRAM_WEBVIEW_MATRIX.md.
const APP_HOST = '127.0.0.1';
const TOP_HOST = 'localhost';
const APP_PORT = 8443;
const TOP_PORT = 8444;
const COOKIE = '__Host-gym_diag';

function selfSignedCert() {
  const dir = mkdtempSync(join(tmpdir(), 'webview-sim-'));
  const key = join(dir, 'key.pem');
  const crt = join(dir, 'cert.pem');
  execFileSync('openssl', [
    'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-days', '1',
    '-keyout', key, '-out', crt, '-subj', '/CN=webview-sim',
    '-addext', `subjectAltName=DNS:${TOP_HOST},IP:${APP_HOST}`,
  ], { stdio: 'ignore' });
  return { key: readFileSync(key), cert: readFileSync(crt) };
}

/** Mirrors the real Set-Cookie string from backend/app/api/v1/diag.py. */
function setCookieHeader(partitioned) {
  const base = `${COOKIE}=probe-value; Path=/; Secure; HttpOnly; SameSite=None; Max-Age=600`;
  return partitioned ? `${base}; Partitioned` : base;
}

function startAppServer(tls) {
  return new Promise((resolve) => {
    const server = createServer(tls, (req, res) => {
      const url = new URL(req.url, `https://${APP_HOST}`);
      if (url.pathname === '/page') {
        res.writeHead(200, { 'Content-Type': 'text/html' });
        return res.end('<!doctype html><title>app</title><body>app frame</body>');
      }
      if (url.pathname === '/set') {
        res.writeHead(200, {
          'Content-Type': 'application/json',
          'Set-Cookie': setCookieHeader(url.searchParams.get('p') === '1'),
        });
        return res.end(JSON.stringify({ sent: true }));
      }
      if (url.pathname === '/read' || url.pathname === '/read-post') {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        return res.end(JSON.stringify({
          cookie_returned: (req.headers.cookie || '').includes(COOKIE),
          origin: req.headers.origin ?? null,
          referer: req.headers.referer ?? null,
          sec_fetch_site: req.headers['sec-fetch-site'] ?? null,
        }));
      }
      res.writeHead(404); res.end();
    });
    server.listen(APP_PORT, '127.0.0.1', () => resolve(server));
  });
}

function startTopServer(tls) {
  return new Promise((resolve) => {
    const server = createServer(tls, (_req, res) => {
      res.writeHead(200, { 'Content-Type': 'text/html' });
      res.end(`<!doctype html><title>top</title><body>
        <iframe src="https://${APP_HOST}:${APP_PORT}/page" width="300" height="200"></iframe>
      </body>`);
    });
    server.listen(TOP_PORT, '127.0.0.1', () => resolve(server));
  });
}

// The sandbox exports HTTPS_PROXY, which Chromium would otherwise honour — sending loopback
// requests to the proxy instead of to the servers this script just started.
const launchArgs = ['--no-proxy-server'];

/** One measurement: set the cookie, then ask the server whether it comes back.
 *
 * Both a GET and a POST are made because they differ in exactly the way D-19 cares about: a
 * browser omits `Origin` on a same-origin GET but sends it on a same-origin POST. Since the
 * real refresh endpoint is a POST, measuring only the GET would understate what is available
 * to the secondary CSRF layer. */
async function probe(frame, partitioned) {
  return frame.evaluate(async (p) => {
    await fetch(`/set?p=${p ? 1 : 0}`, { credentials: 'include' });
    const get = await (await fetch('/read', { credentials: 'include' })).json();
    const post = await (await fetch('/read-post', {
      method: 'POST', credentials: 'include',
      headers: { 'Content-Type': 'application/json' }, body: '{}',
    })).json();
    return { ...get, post_origin: post.origin, post_referer: post.referer, post_sec_fetch_site: post.sec_fetch_site };
  }, partitioned);
}

async function scenario({ label, thirdPartyBlocked, topLevel }) {
  const browser = await chromium.launch({ args: launchArgs });
  const out = { label, third_party_cookies_blocked: thirdPartyBlocked, context: topLevel ? 'top-level' : 'cross-site iframe' };
  try {
    for (const partitioned of [false, true]) {
      const context = await browser.newContext({ ignoreHTTPSErrors: true });
      const page = await context.newPage();
      if (thirdPartyBlocked) {
        // The command-line flag alone did not change behaviour here, so the restriction is
        // driven over CDP instead — this is the switch DevTools itself flips for "block
        // third-party cookies", which makes it the closest available stand-in for a browser
        // with 3PC turned off.
        const cdp = await context.newCDPSession(page);
        await cdp.send('Network.enable');
        await cdp.send('Network.setCookieControls', {
          enableThirdPartyCookieRestriction: true,
          disableThirdPartyCookieMetadata: true,
          disableThirdPartyCookieHeuristics: true,
        });
      }
      let frame;
      if (topLevel) {
        await page.goto(`https://${APP_HOST}:${APP_PORT}/page`, { waitUntil: 'load' });
        frame = page.mainFrame();
      } else {
        await page.goto(`https://${TOP_HOST}:${TOP_PORT}/`, { waitUntil: 'load' });
        frame = page.frames().find((f) => f.url().includes(APP_HOST));
        if (!frame) throw new Error('app iframe did not load');
      }
      out[partitioned ? 'with_partitioned' : 'without_partitioned'] = await probe(frame, partitioned);
      await context.close();
    }
  } finally {
    await browser.close();
  }
  return out;
}

const tls = selfSignedCert();
const appServer = await startAppServer(tls);
const topServer = await startTopServer(tls);

let results;
try {
  results = [
    await scenario({ label: 'Top-level (native WebView bilan bir xil kontekst)', topLevel: true, thirdPartyBlocked: false }),
    await scenario({ label: 'Cross-site iframe, 3P cookie ruxsat etilgan', topLevel: false, thirdPartyBlocked: false }),
    await scenario({ label: 'Cross-site iframe, 3P cookie bloklangan (Telegram Web + Chrome)', topLevel: false, thirdPartyBlocked: true }),
  ];
} finally {
  appServer.close();
  topServer.close();
}

if (process.argv.includes('--json')) {
  console.log(JSON.stringify({ engine: 'chromium', results }, null, 2));
} else {
  const mark = (r) => (r?.cookie_returned ? 'QAYTDI ✓' : 'QAYTMADI ✗');
  for (const r of results) {
    console.log(`\n${r.label}`);
    console.log(`  kontekst: ${r.context} · 3P bloklangan: ${r.third_party_cookies_blocked}`);
    console.log(`  Partitioned YO'Q : ${mark(r.without_partitioned)}`);
    console.log(`  Partitioned BOR  : ${mark(r.with_partitioned)}`);
    const o = r.with_partitioned;
    console.log(`  GET  headerlar: Origin=${o.origin ?? "yo'q"} · Referer=${o.referer ? 'bor' : "yo'q"} · Sec-Fetch-Site=${o.sec_fetch_site ?? "yo'q"}`);
    console.log(`  POST headerlar: Origin=${o.post_origin ?? "yo'q"} · Referer=${o.post_referer ? 'bor' : "yo'q"} · Sec-Fetch-Site=${o.post_sec_fetch_site ?? "yo'q"}`);
  }
  console.log('');
}
