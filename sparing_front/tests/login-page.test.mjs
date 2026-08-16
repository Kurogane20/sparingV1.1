import assert from 'node:assert/strict';
import test from 'node:test';
import { fileURLToPath } from 'node:url';
import { resolve } from 'node:path';
import { createSSRApp } from 'vue';
import { renderToString } from '@vue/server-renderer';

process.env.BROWSERSLIST_IGNORE_OLD_DATA = 'true';
process.env.VITE_DEBUG = 'false';

const projectRoot = fileURLToPath(new URL('..', import.meta.url));

globalThis.localStorage = {
  getItem: () => null,
  setItem: () => {},
  removeItem: () => {},
};

let vite;

test.before(async () => {
  const [{ default: vue }, { createServer }] = await Promise.all([
    import('@vitejs/plugin-vue'),
    import('vite'),
  ]);

  vite = await createServer({
    appType: 'custom',
    configFile: false,
    logLevel: 'silent',
    plugins: [vue()],
    resolve: {
      alias: {
        '@': resolve(projectRoot, 'resources/js'),
      },
    },
    root: projectRoot,
    server: {
      middlewareMode: true,
    },
  });
});

test.after(async () => {
  await vite?.close();
});

async function renderLoginPage() {
  const { default: LoginPage } = await vite.ssrLoadModule('/resources/js/Pages/Auth/Login.vue');
  return renderToString(createSSRApp(LoginPage));
}

test('renders the monitoring workflow as assistive-technology-hidden decoration', async () => {
  const html = await renderLoginPage();

  assert.match(html, /<div class="monitoring-flow" aria-hidden="true"[^>]*>/);
  for (const stage of ['Sensor', 'Data Logger', 'Server', 'Dashboard', 'KLHK']) {
    assert.match(html, new RegExp(`>${stage}<`));
  }
});

test('presents the monitoring facts as three semantic information groups', async () => {
  const html = await renderLoginPage();
  const terms = Array.from(html.matchAll(/<dt\b[^>]*>(.*?)<\/dt>/gs), ([, content]) =>
    content.replace(/<[^>]+>/g, '').trim(),
  );

  assert.deepEqual(terms, ['5 Parameter', 'Monitoring', 'Integrasi']);
  assert.match(html, /pH.*TSS.*COD.*NH3-N.*Debit/s);
  assert.match(html, /Setiap 2 menit/);
  assert.match(html, /Pelaporan KLHK/);
});

test('keeps workflow node centers within tablet-safe horizontal bounds', async () => {
  const html = await renderLoginPage();
  const anchors = Array.from(
    html.matchAll(/<div class="[^"]*monitoring-flow__node[^"]*" style="[^"]*--flow-x:\s*([\d.]+)%/g),
    ([, value]) => Number(value),
  );

  assert.equal(anchors.length, 5);
  assert.ok(anchors[0] >= 16, 'first node must clear the left clipping edge');
  assert.ok(anchors.at(-1) <= 84, 'last node must clear the right clipping edge');
  for (let index = 1; index < anchors.length; index += 1) {
    assert.ok(anchors[index] - anchors[index - 1] >= 10, 'node centers must remain ordered and separated');
  }
});

test('keeps the login form controls available while enhancing the hero', async () => {
  const html = await renderLoginPage();

  assert.match(html, /<input id="email"[^>]*type="email"[^>]*required/);
  assert.match(html, /<input id="password"[^>]*type="password"[^>]*required/);
  assert.match(html, /<button type="submit"[^>]*>.*<span[^>]*>Masuk<\/span>/s);
});
