#!/usr/bin/env node
/**
 * Carousel renderer — slides.json → PNG через headless Chrome.
 *
 * Зависимостей нет: используется установленный Google Chrome.
 *
 *   node render.js slides.json ./out
 *
 * Формат slides.json:
 * {
 *   "theme": { "bg": "#0f2419", "fg": "#ffffff", "accent": "#7cb342",
 *              "font": "Georgia, serif", "size": [1080, 1350] },
 *   "slides": [
 *     { "kind": "cover",  "title": "Заголовок", "subtitle": "Подзаголовок" },
 *     { "kind": "point",  "title": "Мысль",     "body": "Пояснение", "num": 1 },
 *     { "kind": "cta",    "title": "Что делать","body": "Призыв" }
 *   ]
 * }
 */

const fs = require('fs');
const path = require('path');
const os = require('os');
const { execFileSync } = require('child_process');

const CHROME_CANDIDATES = [
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  '/Applications/Chromium.app/Contents/MacOS/Chromium',
  '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge',
  '/usr/bin/google-chrome',
  '/usr/bin/chromium',
];

function findChrome() {
  const fromEnv = process.env.CHROME_BIN;
  if (fromEnv && fs.existsSync(fromEnv)) return fromEnv;
  for (const c of CHROME_CANDIDATES) if (fs.existsSync(c)) return c;
  throw new Error('Не найден Chrome. Укажи путь через CHROME_BIN=/path/to/chrome');
}

const DEFAULT_THEME = {
  bg: '#0f2419',
  fg: '#ffffff',
  accent: '#7cb342',
  font: '-apple-system, "Helvetica Neue", Arial, sans-serif',
  size: [1080, 1350],
};

function esc(s) {
  return String(s == null ? '' : s).replace(/[&<>]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]));
}

function slideHtml(slide, theme, index, total) {
  const [w, h] = theme.size;
  const kind = slide.kind || 'point';
  const titleSize = kind === 'cover' ? 92 : 68;
  const bodySize = kind === 'cover' ? 40 : 36;

  const badge =
    kind === 'point' && slide.num
      ? `<div class="num">${esc(slide.num)}</div>`
      : '';

  const counter =
    kind !== 'cover' ? `<div class="counter">${index + 1} / ${total}</div>` : '';

  return `<!doctype html><meta charset="utf-8"><style>
  @page { margin: 0 }
  * { margin: 0; padding: 0; box-sizing: border-box }
  html, body { width: ${w}px; height: ${h}px }
  body {
    background: ${theme.bg};
    color: ${theme.fg};
    font-family: ${theme.font};
    display: flex; flex-direction: column; justify-content: center;
    padding: 110px 96px;
    position: relative;
    -webkit-font-smoothing: antialiased;
  }
  body::before {
    content: ''; position: absolute; left: 0; top: 0; bottom: 0; width: 14px;
    background: ${theme.accent};
  }
  .num {
    width: 92px; height: 92px; border-radius: 50%;
    background: ${theme.accent}; color: ${theme.bg};
    display: flex; align-items: center; justify-content: center;
    font-size: 46px; font-weight: 700; margin-bottom: 48px;
  }
  h1 {
    font-size: ${titleSize}px; line-height: 1.14; font-weight: 700;
    letter-spacing: -0.02em; text-wrap: balance;
  }
  p {
    font-size: ${bodySize}px; line-height: 1.45; margin-top: 40px;
    opacity: .82; max-width: 86%;
  }
  .accent { color: ${theme.accent} }
  .counter {
    position: absolute; right: 96px; bottom: 76px;
    font-size: 28px; opacity: .45; letter-spacing: .05em;
  }
  .cta h1 { color: ${theme.accent} }
</style>
<body class="${kind === 'cta' ? 'cta' : ''}">
  ${badge}
  <h1>${esc(slide.title)}</h1>
  ${slide.subtitle ? `<p>${esc(slide.subtitle)}</p>` : ''}
  ${slide.body ? `<p>${esc(slide.body)}</p>` : ''}
  ${counter}
</body>`;
}

function main() {
  const [, , inputArg, outArg] = process.argv;
  if (!inputArg) {
    console.error('Использование: node render.js slides.json [./out]');
    process.exit(1);
  }

  const input = path.resolve(inputArg);
  const outDir = path.resolve(outArg || './out');
  const data = JSON.parse(fs.readFileSync(input, 'utf8'));
  const theme = { ...DEFAULT_THEME, ...(data.theme || {}) };
  const slides = data.slides || [];

  if (!slides.length) throw new Error('В slides.json нет слайдов');

  fs.mkdirSync(outDir, { recursive: true });
  const chrome = findChrome();
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'carousel-'));
  const [w, h] = theme.size;
  const made = [];

  slides.forEach((slide, i) => {
    const htmlPath = path.join(tmp, `slide-${i + 1}.html`);
    fs.writeFileSync(htmlPath, slideHtml(slide, theme, i, slides.length), 'utf8');

    const outPath = path.join(outDir, `slide-${String(i + 1).padStart(2, '0')}.png`);
    execFileSync(
      chrome,
      [
        '--headless',
        '--disable-gpu',
        '--hide-scrollbars',
        '--force-device-scale-factor=1',
        `--screenshot=${outPath}`,
        `--window-size=${w},${h}`,
        `file://${htmlPath}`,
      ],
      { stdio: 'ignore' }
    );

    if (!fs.existsSync(outPath)) throw new Error(`Не отрендерился слайд ${i + 1}`);
    made.push(outPath);
    console.log(`  ✓ ${path.basename(outPath)}`);
  });

  fs.rmSync(tmp, { recursive: true, force: true });
  console.log(`\nГотово: ${made.length} слайдов в ${outDir}`);
}

main();
