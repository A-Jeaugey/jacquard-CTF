#!/usr/bin/env node
// Mesures déterministes sur une page rendue, fournies au juge de design avant toute
// appréciation visuelle (les modèles de vision voient mal les contrastes, débordements et
// alignements au pixel près).
//
//   node scripts/ui-audit.mjs <url> [--name accueil] [--out dossier] [--click "sélecteur"]
//                                  [--login pseudo:motdepasse]
//
// Pour chaque largeur (1440, 768, 390), relève : débordement horizontal, textes sous le
// contraste WCAG AA, cibles tactiles trop petites (390 px), familles et tailles de police
// utilisées, espacements hors de l'échelle de 4 px, focus clavier invisible, animations
// actives avec prefers-reduced-motion, erreurs console. Écrit <out>/<name>.json et affiche
// un résumé.

import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { chromium } from "playwright";

const args = process.argv.slice(2);
const url = args.find((a) => !a.startsWith("--") && !args[args.indexOf(a) - 1]?.startsWith("--"));
const opt = (name, fallback) => {
  const i = args.indexOf(`--${name}`);
  return i >= 0 ? args[i + 1] : fallback;
};
if (!url) {
  console.error("usage : node scripts/ui-audit.mjs <url> [--name n] [--out dossier] [--click sélecteur]");
  process.exit(2);
}
const name = opt("name", "page");
const out = opt("out", "audit");
const click = opt("click", null);
const login = opt("login", null);

/** Connexion par l'API de la plateforme (cookie de session et jeton CSRF), avant la mesure. */
async function seConnecter(page) {
  const [username, ...rest] = login.split(":");
  await page.goto(new URL("/?audit", url).href, { waitUntil: "load" });
  const status = await page.evaluate(async ({ username, password }) => {
    const csrf = document.cookie.match(/jq_csrf=([^;]+)/)?.[1] ?? "";
    const r = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf },
      body: JSON.stringify({ username, password }),
    });
    return r.status;
  }, { username, password: rest.join(":") });
  if (status !== 200) throw new Error(`connexion refusée (${status})`);
}
const VIEWPORTS = [
  { label: "1440", width: 1440, height: 900, mobile: false },
  { label: "768", width: 768, height: 1024, mobile: false },
  { label: "390", width: 390, height: 844, mobile: true },
];

// Exécuté dans la page.
function measure(isMobile) {
  const lum = (c) => {
    const f = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; };
    return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2]);
  };
  const parse = (s) => {
    const m = s.match(/rgba?\(([^)]+)\)/);
    if (!m) return null;
    const p = m[1].split(/[ ,/]+/).filter(Boolean).map(Number);
    return [p[0], p[1], p[2], p.length > 3 ? p[3] : 1];
  };
  const blend = (top, under) => {
    const a = top[3];
    return [0, 1, 2].map((i) => top[i] * a + under[i] * (1 - a)).concat(1);
  };
  const bgOf = (el) => {
    const layers = [];
    for (let n = el; n; n = n.parentElement) {
      const cs = getComputedStyle(n);
      if (cs.backgroundImage && cs.backgroundImage !== "none") return { color: null, image: true };
      const c = parse(cs.backgroundColor);
      if (c && c[3] > 0) { layers.push(c); if (c[3] >= 1) break; }
    }
    let color = [255, 255, 255, 1];
    for (const l of layers.reverse()) color = blend(l, color);
    return { color, image: false };
  };
  const visible = (el) => {
    const r = el.getBoundingClientRect();
    const cs = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && cs.visibility !== "hidden" && cs.display !== "none" && +cs.opacity > 0.05;
  };
  const describe = (el) => {
    const id = el.id ? `#${el.id}` : "";
    const cls = typeof el.className === "string" && el.className.trim() ? `.${el.className.trim().split(/\s+/).slice(0, 2).join(".")}` : "";
    const r = el.getBoundingClientRect();
    return { sel: `${el.tagName.toLowerCase()}${id}${cls}`, text: (el.textContent || "").trim().slice(0, 40), box: [r.x, r.y, r.width, r.height].map(Math.round) };
  };

  const report = { contrast: [], targets: [], fonts: {}, sizes: {}, offScale: {}, overflow: null, clipped: [] };
  const doc = document.documentElement;
  report.overflow = doc.scrollWidth > doc.clientWidth + 1 ? { scrollWidth: doc.scrollWidth, clientWidth: doc.clientWidth } : null;

  const textEls = [...document.querySelectorAll("body *")].filter((el) =>
    visible(el) && [...el.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim()));
  for (const el of textEls) {
    const cs = getComputedStyle(el);
    const family = cs.fontFamily.split(",")[0].replace(/["']/g, "").trim();
    report.fonts[family] = (report.fonts[family] || 0) + 1;
    const size = parseFloat(cs.fontSize);
    report.sizes[size] = (report.sizes[size] || 0) + 1;
    const fg = parse(cs.color);
    const bg = bgOf(el);
    if (!fg || bg.image) continue;
    const front = blend(fg, bg.color);
    const [l1, l2] = [lum(front), lum(bg.color)].sort((a, b) => b - a);
    const ratio = (l1 + 0.05) / (l2 + 0.05);
    const large = size >= 24 || (size >= 18.66 && +cs.fontWeight >= 700);
    if (ratio < (large ? 3 : 4.5)) report.contrast.push({ ...describe(el), ratio: +ratio.toFixed(2), size });
    if (el.scrollWidth > el.clientWidth + 1 && ["hidden", "clip"].includes(cs.overflowX)) report.clipped.push(describe(el));
  }
  for (const el of document.querySelectorAll("body *")) {
    if (!visible(el)) continue;
    const cs = getComputedStyle(el);
    for (const prop of ["paddingTop", "paddingRight", "paddingBottom", "paddingLeft", "marginTop", "marginBottom", "rowGap", "columnGap"]) {
      const v = parseFloat(cs[prop]);
      if (v > 0 && v % 4 !== 0 && v % 2 !== 0) report.offScale[v] = (report.offScale[v] || 0) + 1;
    }
  }
  if (isMobile) {
    for (const el of document.querySelectorAll("a[href], button, input, select, textarea, [role=button], [tabindex]:not([tabindex='-1'])")) {
      if (!visible(el)) continue;
      const r = el.getBoundingClientRect();
      if (r.width < 44 || r.height < 44) report.targets.push({ ...describe(el), size: [Math.round(r.width), Math.round(r.height)] });
    }
  }
  return report;
}

async function focusCheck(page) {
  const missing = [];
  for (let i = 0; i < 12; i++) {
    await page.keyboard.press("Tab");
    const res = await page.evaluate(() => {
      const el = document.activeElement;
      if (!el || el === document.body) return null;
      const cs = getComputedStyle(el);
      const visibleRing = (cs.outlineStyle !== "none" && parseFloat(cs.outlineWidth) > 0) || (cs.boxShadow && cs.boxShadow !== "none");
      return { sel: el.tagName.toLowerCase() + (el.className && typeof el.className === "string" ? "." + el.className.trim().split(/\s+/)[0] : ""), text: (el.textContent || el.getAttribute("aria-label") || "").trim().slice(0, 30), visibleRing };
    });
    if (res && !res.visibleRing) missing.push(res);
  }
  return missing;
}

const browser = await chromium.launch();
const result = { url, name, viewports: {} };
for (const vp of VIEWPORTS) {
  const context = await browser.newContext({ viewport: { width: vp.width, height: vp.height }, isMobile: vp.mobile, hasTouch: vp.mobile, reducedMotion: "reduce" });
  const page = await context.newPage();
  const errors = [];
  page.on("console", (m) => m.type() === "error" && errors.push(m.text()));
  page.on("pageerror", (e) => errors.push(String(e)));
  if (login) await seConnecter(page);
  await page.goto(url, { waitUntil: "load" });
  await page.waitForTimeout(800);
  if (click) { await page.click(click); await page.waitForTimeout(500); }
  const data = await page.evaluate(measure, vp.mobile);
  data.runningAnimations = await page.evaluate(() => document.getAnimations().filter((a) => a.playState === "running" && (a.effect?.getTiming().iterations === Infinity)).length);
  data.focusWithoutRing = await focusCheck(page);
  data.consoleErrors = errors;
  result.viewports[vp.label] = data;
  await context.close();
}
await browser.close();

mkdirSync(out, { recursive: true });
writeFileSync(join(out, `${name}.json`), JSON.stringify(result, null, 1));

const lines = [`Audit de ${name} (${url})`];
for (const [label, d] of Object.entries(result.viewports)) {
  const fonts = Object.entries(d.fonts).sort((a, b) => b[1] - a[1]).map(([f, n]) => `${f}×${n}`).join(", ");
  const sizes = Object.keys(d.sizes).map(Number).sort((a, b) => a - b).join("/");
  lines.push(`\n[${label}px]`);
  lines.push(`  débordement horizontal : ${d.overflow ? `OUI (${d.overflow.scrollWidth}px)` : "non"}`);
  lines.push(`  polices : ${fonts}`);
  lines.push(`  tailles (px) : ${sizes}`);
  lines.push(`  contrastes insuffisants : ${d.contrast.length}${d.contrast.slice(0, 5).map((c) => `\n    ${c.ratio}:1 ${c.sel} « ${c.text} »`).join("")}`);
  lines.push(`  textes coupés : ${d.clipped.length}`);
  lines.push(`  espacements hors échelle : ${Object.entries(d.offScale).map(([v, n]) => `${v}px×${n}`).join(", ") || "aucun"}`);
  if (label === "390") lines.push(`  cibles < 44px : ${d.targets.length}${d.targets.slice(0, 5).map((t) => `\n    ${t.size.join("×")} ${t.sel} « ${t.text} »`).join("")}`);
  lines.push(`  focus invisible (12 premières tabulations) : ${d.focusWithoutRing.length}${d.focusWithoutRing.slice(0, 3).map((f) => `\n    ${f.sel} « ${f.text} »`).join("")}`);
  lines.push(`  animations infinies malgré reduced-motion : ${d.runningAnimations}`);
  lines.push(`  erreurs console : ${d.consoleErrors.length}`);
}
console.log(lines.join("\n"));
