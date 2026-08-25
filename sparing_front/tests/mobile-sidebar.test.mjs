import assert from 'node:assert/strict';
import test from 'node:test';
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { resolve } from 'node:path';
import postcss from 'postcss';
import selectorParser from 'postcss-selector-parser';
import tailwindcss from 'tailwindcss';
import { createSSRApp, h } from 'vue';
import { renderToString } from '@vue/server-renderer';
import { createMemoryHistory, createRouter } from 'vue-router';
import tailwindConfig from '../tailwind.config.js';

process.env.BROWSERSLIST_IGNORE_OLD_DATA = 'true';
process.env.VITE_DEBUG = 'false';

const projectRoot = fileURLToPath(new URL('..', import.meta.url));
const stylesheetPath = resolve(projectRoot, 'resources/css/app.css');
const mobileViewportWidth = 375;

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

async function renderOpenLayout() {
  const { default: AppLayout } = await vite.ssrLoadModule('/resources/js/Layouts/AppLayout.vue');
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      {
        path: '/:pathMatch(.*)*',
        component: { render: () => null },
      },
    ],
  });

  await router.push('/dashboard');
  await router.isReady();

  const app = createSSRApp({
    render: () => h(AppLayout, null, { default: () => h('div') }),
  });
  app.use(router);

  return renderToString(app);
}

function mediaMatchesViewport(params, viewportWidth) {
  if (/\bprint\b/i.test(params)) return false;

  const minWidth = params.match(/min-width:\s*([\d.]+)px/i);
  const maxWidth = params.match(/max-width:\s*([\d.]+)px/i);

  if (minWidth && viewportWidth < Number(minWidth[1])) return false;
  if (maxWidth && viewportWidth > Number(maxWidth[1])) return false;
  return true;
}

function ruleMatchesViewport(rule, viewportWidth) {
  for (let parent = rule.parent; parent; parent = parent.parent) {
    if (parent.type !== 'atrule') continue;
    if (/keyframes$/i.test(parent.name)) return false;
    if (parent.name === 'media' && !mediaMatchesViewport(parent.params, viewportWidth)) return false;
  }
  return true;
}

function createElement(tagName, classAttribute = '', parent = null, attributes = {}) {
  return {
    attributes: { ...attributes, ...(classAttribute ? { class: classAttribute } : {}) },
    classNames: new Set(classAttribute.split(/\s+/).filter(Boolean)),
    parent,
    previousElementSibling: null,
    tagName,
  };
}

function sidebarElementFromLayout(html) {
  const layoutMatch = html.match(/^\s*<div\b[^>]*\bclass="([^"]+)"/i);
  const sidebarMatch = html.match(/<aside\b[^>]*\bclass="([^"]+)"/i);
  assert.ok(layoutMatch, 'AppLayout must render its root container');
  assert.ok(sidebarMatch, 'AppLayout must render the Sidebar');

  const htmlElement = createElement('html');
  const bodyElement = createElement('body', '', htmlElement);
  const mountElement = createElement('div', '', bodyElement, { id: 'app' });
  const layoutElement = createElement('div', layoutMatch[1], mountElement);
  return createElement('aside', sidebarMatch[1], layoutElement, { style: 'background: #12333B;' });
}

function attributeMatches(attribute, element) {
  const name = attribute.attribute.toLowerCase();
  const actualValue = element.attributes[name];
  if (actualValue === undefined) return false;
  if (!attribute.operator) return true;

  const insensitive = attribute.insensitive === true;
  const actual = insensitive ? String(actualValue).toLowerCase() : String(actualValue);
  const expectedValue = attribute.value ?? '';
  const expected = insensitive ? expectedValue.toLowerCase() : expectedValue;

  switch (attribute.operator) {
    case '=': return actual === expected;
    case '~=': return actual.split(/\s+/).includes(expected);
    case '|=': return actual === expected || actual.startsWith(`${expected}-`);
    case '^=': return actual.startsWith(expected);
    case '$=': return actual.endsWith(expected);
    case '*=': return actual.includes(expected);
    default: return false;
  }
}

function splitSelector(selector) {
  const compounds = [[]];
  const combinators = [];

  for (const node of selector.nodes) {
    if (node.type === 'combinator') {
      combinators.push(node.value.trim() || ' ');
      compounds.push([]);
    } else {
      compounds.at(-1).push(node);
    }
  }

  return { combinators, compounds };
}

function pseudoMatches(pseudo, element) {
  const name = pseudo.value.toLowerCase();
  const nestedSelectors = pseudo.nodes ?? [];

  if (name === ':not') {
    return !nestedSelectors.some((selector) => selectorMatchesElement(selector, element));
  }
  if (name === ':is' || name === ':where' || name === ':matches') {
    return nestedSelectors.some((selector) => selectorMatchesElement(selector, element));
  }
  if (name === ':root') return element.tagName === 'html';

  return false;
}

function compoundMatchesElement(nodes, element) {
  if (!element) return false;

  return nodes.every((node) => {
    switch (node.type) {
      case 'universal': return true;
      case 'tag': return node.value.toLowerCase() === element.tagName;
      case 'class': return element.classNames.has(node.value);
      case 'id': return element.attributes.id === node.value;
      case 'attribute': return attributeMatches(node, element);
      case 'pseudo': return pseudoMatches(node, element);
      case 'comment': return true;
      default: return false;
    }
  });
}

function selectorMatchesElement(selector, element) {
  const { combinators, compounds } = splitSelector(selector);

  function matchesFrom(candidate, compoundIndex) {
    if (!compoundMatchesElement(compounds[compoundIndex], candidate)) return false;
    if (compoundIndex === 0) return true;

    const combinator = combinators[compoundIndex - 1];
    if (combinator === '>') return matchesFrom(candidate.parent, compoundIndex - 1);
    if (combinator === '+') return matchesFrom(candidate.previousElementSibling, compoundIndex - 1);
    if (combinator === '~') {
      for (let sibling = candidate.previousElementSibling; sibling; sibling = sibling.previousElementSibling) {
        if (matchesFrom(sibling, compoundIndex - 1)) return true;
      }
      return false;
    }

    for (let ancestor = candidate.parent; ancestor; ancestor = ancestor.parent) {
      if (matchesFrom(ancestor, compoundIndex - 1)) return true;
    }
    return false;
  }

  return matchesFrom(element, compounds.length - 1);
}

function addSpecificity(target, addition) {
  return target.map((value, index) => value + addition[index]);
}

function compareSpecificity(left, right) {
  for (let index = 0; index < left.length; index += 1) {
    if (left[index] !== right[index]) return left[index] - right[index];
  }
  return 0;
}

function selectorSpecificity(selector) {
  let specificity = [0, 0, 0];

  for (const node of selector.nodes) {
    if (node.type === 'id') specificity[0] += 1;
    else if (node.type === 'class' || node.type === 'attribute') specificity[1] += 1;
    else if (node.type === 'tag') specificity[2] += 1;
    else if (node.type === 'pseudo') {
      const name = node.value.toLowerCase();
      if (name.startsWith('::')) specificity[2] += 1;
      else if (name !== ':where' && [':is', ':not', ':has', ':matches'].includes(name)) {
        const nestedSpecificity = (node.nodes ?? [])
          .map(selectorSpecificity)
          .sort((left, right) => compareSpecificity(right, left))[0] ?? [0, 0, 0];
        specificity = addSpecificity(specificity, nestedSpecificity);
      } else if (name !== ':where') {
        specificity[1] += 1;
      }
    }
  }

  return specificity;
}

function matchingSelectorSpecificity(selector, element) {
  const parsed = selectorParser().astSync(selector).first;
  return selectorMatchesElement(parsed, element) ? selectorSpecificity(parsed) : null;
}

function winningTransform(root, element, viewportWidth) {
  let order = 0;
  let winner = null;

  root.walkRules((rule) => {
    order += 1;
    if (!ruleMatchesViewport(rule, viewportWidth)) return;

    for (const selector of rule.selectors) {
      const specificity = matchingSelectorSpecificity(selector, element);
      if (specificity === null) continue;

      rule.walkDecls('transform', (declaration) => {
        const candidate = {
          important: Boolean(declaration.important),
          order,
          selector,
          specificity,
          value: declaration.value,
        };

        const winsByImportance = candidate.important && !winner?.important;
        const hasSameImportance = candidate.important === (winner?.important ?? false);
        const winsByCascade = hasSameImportance && (
          !winner
          || compareSpecificity(candidate.specificity, winner.specificity) > 0
          || (compareSpecificity(candidate.specificity, winner.specificity) === 0 && candidate.order > winner.order)
        );

        if (winsByImportance || winsByCascade) winner = candidate;
      });
    }
  });

  return winner;
}

test('keeps the open mobile sidebar on-canvas after the compiled CSS cascade', async () => {
  const html = await renderOpenLayout();
  const element = sidebarElementFromLayout(html);
  const stylesheet = await readFile(stylesheetPath, 'utf8');
  const compiled = await postcss([
    tailwindcss({
      ...tailwindConfig,
      content: [{ raw: html, extension: 'html' }],
    }),
  ]).process(stylesheet, { from: stylesheetPath });

  const transform = winningTransform(compiled.root, element, mobileViewportWidth);

  assert.ok(transform, 'The open sidebar must have a compiled transform rule');
  assert.match(
    transform.value,
    /var\(--tw-translate-x\)/,
    `Expected the open-state transform to win, but ${transform.selector} applies ${transform.value}`,
  );
});

test('includes matching compound sidebar selectors in the mobile cascade', () => {
  const bodyElement = createElement('body');
  const element = createElement('aside', 'sidebar translate-x-0', bodyElement);

  for (const selector of [
    'aside.sidebar',
    'aside.sidebar:not(.open)',
    'aside[class~="sidebar"]',
    'body .sidebar',
  ]) {
    const stylesheet = postcss.parse(`
      .translate-x-0 {
        transform: translate(var(--tw-translate-x), var(--tw-translate-y));
      }
      @media (max-width: 768px) {
        ${selector} { transform: translateX(-100%); }
      }
    `);
    const transform = winningTransform(stylesheet, element, mobileViewportWidth);

    assert.equal(transform?.value, 'translateX(-100%)', `must include ${selector}`);
  }
});
