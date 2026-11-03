#!/usr/bin/env node
// Détecteur déterministe des marqueurs d'interface « générée par IA » (sans modèle).
//
//   node scripts/slop-lint.mjs [dossier ou fichier ...]     (par défaut : src)
//
// Règles reprises des catalogues cités dans docs/refonte-ui/recherche.md (avoid-ai-design,
// Impeccable, skill frontend-design d'Anthropic), réécrites pour Svelte + CSS natif.
// Code de sortie 1 si une règle bloquante (P0 ou P1) est touchée.
// Une exception assumée se déclare dans le fichier : /* slop-ok: <règle> <raison> */

import { readFileSync, readdirSync, statSync } from "node:fs";
import { extname, join, relative } from "node:path";

const EXTS = new Set([".svelte", ".css", ".html", ".ts", ".js"]);

// ── couleurs ─────────────────────────────────────────────────────────────────
const COLOR_RE = /#[0-9a-f]{3,8}\b|rgba?\([^)]*\)|hsla?\([^)]*\)/gi;
function parseColor(text) {
  const t = text.trim().toLowerCase();
  if (t.startsWith("#")) {
    let h = t.slice(1);
    if (h.length === 3 || h.length === 4) h = [...h].map((c) => c + c).join("");
    if (h.length !== 6 && h.length !== 8) return null;
    const n = (i) => parseInt(h.slice(i, i + 2), 16);
    return { r: n(0), g: n(2), b: n(4), a: h.length === 8 ? n(6) / 255 : 1 };
  }
  const nums = t.match(/[\d.]+%?/g);
  if (!nums || nums.length < 3) return null;
  const v = (s, max) => (s.endsWith("%") ? (parseFloat(s) / 100) * max : parseFloat(s));
  if (t.startsWith("rgb")) return { r: v(nums[0], 255), g: v(nums[1], 255), b: v(nums[2], 255), a: nums[3] ? v(nums[3], 1) : 1 };
  // hsl
  const h = parseFloat(nums[0]), s = v(nums[1], 1), l = v(nums[2], 1);
  const k = (n) => (n + h / 30) % 12, a = s * Math.min(l, 1 - l);
  const f = (n) => l - a * Math.max(-1, Math.min(k(n) - 3, 9 - k(n), 1));
  return { r: f(0) * 255, g: f(8) * 255, b: f(4) * 255, a: nums[3] ? v(nums[3], 1) : 1 };
}
function hsl({ r, g, b }) {
  r /= 255; g /= 255; b /= 255;
  const max = Math.max(r, g, b), min = Math.min(r, g, b), l = (max + min) / 2, d = max - min;
  if (d === 0) return { h: 0, s: 0, l };
  const s = d / (1 - Math.abs(2 * l - 1));
  let h = max === r ? ((g - b) / d) % 6 : max === g ? (b - r) / d + 2 : (r - g) / d + 4;
  h = (h * 60 + 360) % 360;
  return { h, s, l };
}
const isViolet = (c) => { const x = hsl(c); return x.s > 0.35 && x.h >= 235 && x.h <= 290; };
const isSaturated = (c) => hsl(c).s > 0.45 && hsl(c).l > 0.2 && hsl(c).l < 0.85;
const isCream = (c) => { const x = hsl(c); return x.l > 0.88 && x.l < 0.97 && x.h >= 30 && x.h <= 60 && x.s > 0.15; };
const isTerracotta = (c) => { const x = hsl(c); return x.h >= 8 && x.h <= 25 && x.s > 0.4 && x.l > 0.45 && x.l < 0.7; };
const isNearBlack = (c) => { const x = hsl(c); return x.l < 0.09 && x.s < 0.2; };

// ── polices ──────────────────────────────────────────────────────────────────
const BANNED_FONTS = [
  "inter", "roboto", "arial", "helvetica", "open sans", "lato", "montserrat", "poppins",
  "space grotesk", "space mono", "geist", "syne", "sora", "instrument serif", "instrument sans",
  "fraunces", "playfair", "playfair display", "georgia", "cal sans", "clash display", "satoshi",
  "dm sans", "dm serif", "dm serif display", "manrope", "plus jakarta sans", "outfit",
  "bricolage grotesque", "unbounded", "ibm plex sans", "ibm plex serif", "ibm plex mono",
  "jetbrains mono", "fira code", "vt323", "press start 2p", "system-ui", "-apple-system",
  "segoe ui",
];
const GENERIC = /^(inherit|initial|unset|serif|sans-serif|monospace|cursive|fantasy|math|emoji|ui-monospace|ui-sans-serif|ui-serif)$/;

// ── analyse ──────────────────────────────────────────────────────────────────
function files(target) {
  const st = statSync(target);
  if (st.isFile()) return [target];
  return readdirSync(target).flatMap((name) => {
    if (name === "node_modules" || name.startsWith(".")) return [];
    const p = join(target, name);
    return statSync(p).isDirectory() ? files(p) : EXTS.has(extname(p)) ? [p] : [];
  });
}

function split(file, text) {
  const ext = extname(file);
  if (ext === ".css") return { css: text, markup: "", script: "" };
  if (ext === ".ts" || ext === ".js") return { css: "", markup: "", script: text };
  const css = [...text.matchAll(/<style\b[^>]*>([\s\S]*?)<\/style>/gi)].map((m) => m[1]).join("\n");
  const script = [...text.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/gi)].map((m) => m[1]).join("\n");
  const markup = text.replace(/<script\b[\s\S]*?<\/script>|<style\b[\s\S]*?<\/style>|<!--[\s\S]*?-->/gi, "");
  return { css, markup, script };
}

function cssRules(css) {
  const out = [];
  const clean = css.replace(/\/\*[\s\S]*?\*\//g, "");
  for (const m of clean.matchAll(/([^{}]+)\{([^{}]*)\}/g)) out.push({ sel: m[1].trim(), body: m[2] });
  return out;
}

const RULES = [
  ["F1", "P0", "Police interdite (cliché IA)", ({ css }) => {
    const hits = [];
    for (const m of css.matchAll(/font-family\s*:\s*([^;}]+)/gi)) {
      const first = m[1].split(",")[0].replace(/["']/g, "").trim().toLowerCase();
      if (BANNED_FONTS.includes(first)) hits.push(first);
    }
    return hits;
  }],
  ["F2", "P1", "Police déclarée mais jamais chargée", ({ css }, all) => {
    const hits = [];
    for (const m of css.matchAll(/font-family\s*:\s*([^;}]+)/gi)) {
      const first = m[1].split(",")[0].replace(/["']/g, "").trim();
      if (!first || first.startsWith("var(") || GENERIC.test(first.toLowerCase())) continue;
      if (!all.fontFaces.has(first.toLowerCase())) hits.push(first);
    }
    return hits;
  }],
  ["C1", "P0", "Dégradé violet ou indigo", ({ css }) =>
    [...css.matchAll(/(?:linear|radial|conic)-gradient\(([^;{}]*)\)/gi)]
      .filter((m) => (m[1].match(COLOR_RE) || []).map(parseColor).filter(Boolean).some(isViolet)).map(() => "dégradé")],
  ["C2", "P0", "Texte en dégradé", ({ css }) =>
    cssRules(css).filter((r) => /background-clip\s*:\s*text/.test(r.body)).map((r) => r.sel)],
  ["C3", "P1", "Ombre lumineuse colorée (glow)", ({ css }) =>
    [...css.matchAll(/box-shadow\s*:\s*([^;}]+)/gi)].filter((m) => {
      if (/\binset\b/.test(m[1])) return false;
      const blur = m[1].match(/-?[\d.]+(?:px)?\s+-?[\d.]+(?:px)?\s+([\d.]+)px/);
      if (!blur || +blur[1] < 8) return false;
      return (m[1].match(COLOR_RE) || []).map(parseColor).filter(Boolean).some((c) => c.a >= 0.25 && isSaturated(c));
    }).map((m) => m[1].trim())],
  ["C4", "P1", "Fond crème + accent terracotta (style maison des modèles)", ({ css }) => {
    const colors = (css.match(COLOR_RE) || []).map(parseColor).filter(Boolean);
    return colors.some(isCream) && colors.some(isTerracotta) ? ["crème + terracotta"] : [];
  }],
  ["C5", "P2", "Quasi-noir teinté utilisé comme fond (#0B0B0B, #111…)", ({ css }) =>
    cssRules(css).filter((r) => /^(html|body|:root)$/.test(r.sel) && /background(-color)?\s*:/.test(r.body))
      .filter((r) => (r.body.match(COLOR_RE) || []).map(parseColor).filter(Boolean).some(isNearBlack)).map((r) => r.sel)],
  ["K1", "P1", "Verre dépoli (backdrop-filter: blur)", ({ css }) =>
    [...css.matchAll(/backdrop-filter\s*:\s*[^;]*blur/gi)].map(() => "backdrop-filter")],
  ["K2", "P1", "Bordure colorée sur un côté d'une carte", ({ css }) =>
    cssRules(css).filter((r) => /border-(left|right|top)\s*:\s*([3-9]|\d\d)px\s+solid/.test(r.body)
      || /border-(left|top)-width\s*:\s*([3-9]|\d\d)px/.test(r.body)).map((r) => r.sel)],
  ["K3", "P2", "Pastilles en série (border-radius: 999px)", ({ css }) => {
    const hits = [...css.matchAll(/border-radius\s*:\s*(999|9999|100)px|border-radius\s*:\s*50vh/gi)];
    return hits.length >= 3 ? hits.map(() => "pastille") : [];
  }],
  ["T1", "P1", "Étiquettes en capitales espacées", ({ css }) => {
    const hits = cssRules(css).filter((r) => /text-transform\s*:\s*uppercase/.test(r.body) && /letter-spacing\s*:\s*[.\d]/.test(r.body));
    return hits.length >= 2 ? hits.map((r) => r.sel) : [];
  }],
  ["T2", "P2", "Monospace pour de petites étiquettes", ({ css }) => {
    const hits = cssRules(css).filter((r) => {
      const ff = r.body.match(/font-family\s*:\s*([^;]+)/), fs = r.body.match(/font-size\s*:\s*([\d.]+)(px|rem|em)/);
      if (!ff || !fs || !/mono|menlo|consolas|courier/i.test(ff[1])) return false;
      return (fs[2] === "px" ? +fs[1] : +fs[1] * 16) <= 13;
    });
    return hits.length >= 2 ? hits.map((r) => r.sel) : [];
  }],
  ["T3", "P2", "Métadonnées « A · B · C »", ({ markup }) => {
    const hits = [...markup.matchAll(/[^\s<>{}·][^<>{}\n·]{0,40}\s·\s[^<>{}\n]{1,60}/g)];
    return hits.length >= 2 ? hits.map((m) => m[0].trim().slice(0, 40)) : [];
  }],
  ["T4", "P1", "Flèche « → » accolée à un lien ou un bouton", ({ markup }) =>
    [...markup.matchAll(/→/g)].map(() => "→")],
  ["T5", "P1", "Emoji en guise d'icône", ({ markup }) =>
    [...markup.matchAll(/[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}]/gu)].filter((m) => !/[✓✗]/.test(m[0])).map((m) => m[0])],
  ["T6", "P2", "Numérotation décorative 01 / 02 / 03", ({ markup }) => {
    const hits = [...markup.matchAll(/>\s*0[1-9]\s*</g)];
    return hits.length >= 3 ? hits.map(() => "0x") : [];
  }],
  ["M1", "P1", "transition: all", ({ css }) => [...css.matchAll(/transition\s*:\s*all\b/gi)].map(() => "transition: all")],
  ["M2", "P2", "Rebond (cubic-bezier hors de [0,1])", ({ css }) =>
    [...css.matchAll(/cubic-bezier\(([^)]*)\)/gi)].filter((m) => m[1].split(",").map(Number).some((v, i) => i % 2 === 1 && (v < 0 || v > 1))).map((m) => m[0])],
  ["M3", "P2", "Animation décorative en boucle", ({ css }) =>
    [...css.matchAll(/animation\s*:[^;]*infinite/gi)].map((m) => m[0].slice(0, 50))],
  ["I1", "P1", "Icônes Lucide (jeu par défaut)", ({ script }) =>
    [...script.matchAll(/from\s+["'](@lucide\/svelte|lucide-svelte|lucide)["']/g)].map((m) => m[1])],
  ["X1", "P1", "Focus supprimé sans :focus-visible", ({ css }, all) =>
    /outline\s*:\s*(none|0)\b/.test(css) && !all.hasFocusVisible ? ["outline: none"] : []],
  ["T7", "P1", "Un seul mot mis en valeur dans un titre", ({ markup }) => {
    const hits = [];
    for (const m of markup.matchAll(/<h([1-3])\b[^>]*>([\s\S]{0,400}?)<\/h\1>/gi)) {
      const accent = m[2].match(/<(span|em|i|b|strong|mark)\b[^>]*>([\s\S]{1,60}?)<\/\1>/i);
      if (!accent) continue;
      const words = (s) => s.replace(/<[^>]+>|\{[^}]*\}/g, " ").trim().split(/\s+/).filter(Boolean).length;
      const inside = words(accent[2]), total = words(m[2]);
      if (inside >= 1 && inside <= 3 && total > inside) hits.push(accent[2].replace(/<[^>]+>/g, "").trim());
    }
    return hits;
  }],
  ["T8", "P2", "Libellés « MOT — fragment »", ({ markup }) =>
    [...markup.matchAll(/\b[A-ZÀ-Ý][A-ZÀ-Ý0-9]{2,}(?:\s[A-ZÀ-Ý0-9]{2,})*\s[—–]\s[A-Za-zÀ-ÿ]/g)].map((m) => m[0])],
  ["K4", "P2", "Fausse fenêtre (trois pastilles façon macOS)", ({ css, markup }) =>
    [...(css + markup).matchAll(/#(ff5f57|febc2e|ffbd2e|28c840|27c93f)\b/gi)].map((m) => m[0])],
  ["C6", "P2", "Vert émeraude, accent de repli des modèles", ({ css }) =>
    [...css.matchAll(/#(10b981|059669|34d399|6ee7b7|047857)\b/gi)].map((m) => m[0])],
  ["C7", "P1", "Bouton principal violet ou indigo", ({ css }) =>
    cssRules(css).filter((r) => /btn|button|cta|primary/i.test(r.sel) && /background/.test(r.body)
      && (r.body.match(COLOR_RE) || []).map(parseColor).filter(Boolean).some(isViolet)).map((r) => r.sel)],
  ["W1", "P2", "Texte publicitaire ou libellé vague", ({ markup, script }) => {
    // Texte visible seulement : le texte entre les balises, et les chaînes du script qui
    // ressemblent à une phrase (avec une espace), pas les clés ni les noms d'événements.
    const visibleText = markup.replace(/<[^>]*>/g, " ").replace(/\{[^}]*\}/g, " ");
    const phrases = [...script.matchAll(/(["'`])((?:\\.|(?!\1).){3,200})\1/g)].map((m) => m[2]).filter((s) => / /.test(s));
    const text = visibleText + "\n" + phrases.join("\n");
    return [...text.matchAll(/\b(soumettre|en savoir plus|cliquez ici|découvrez|boostez|révolutionn\w*|sans effort|en toute simplicité|de pointe|incroyable|libérez|transformez|élevez|plongez dans|submit|learn more|click here|get started|seamless|cutting-edge|unleash|elevate|supercharge|next-generation)\b/gi)]
      .map((m) => m[0]);
  }],
  ["W2", "P1", "Contenu de remplissage ou signature de générateur", ({ markup, script }) =>
    [...(markup + script).matchAll(/lorem ipsum|john doe|jane doe|\bacme\b|via\.placeholder|picsum\.photos|source\.unsplash|generated by (v0|bolt|lovable)|made with (v0|bolt|lovable)/gi)].map((m) => m[0])],
];

// Règles qui portent sur l'ensemble des styles (jetons résolus).
function globalRules(allCss) {
  const vars = {};
  for (const m of allCss.matchAll(/--([\w-]+)\s*:\s*([^;}]+)/g)) vars[m[1]] = m[2].trim();
  const resolve = (v, depth = 0) => (depth > 6 ? v : v.replace(/var\(\s*--([\w-]+)\s*(?:,\s*([^)]+))?\)/g,
    (_, n, fallback) => (vars[n] !== undefined ? resolve(vars[n], depth + 1) : fallback || "")));
  const colors = (v) => (resolve(v).match(COLOR_RE) || []).map(parseColor).filter(Boolean);
  const out = [];

  const radii = [...allCss.matchAll(/border-radius\s*:\s*([^;}]+)/g)].map((m) => resolve(m[1]).trim())
    .filter((v) => !/^(0|0px|50%|999px|9999px|100px|inherit)$/.test(v));
  const top = (list) => {
    const counts = {};
    for (const v of list) counts[v] = (counts[v] || 0) + 1;
    return Object.entries(counts).sort((a, b) => b[1] - a[1])[0] || ["", 0];
  };
  const [radius, nRadius] = top(radii);
  if (radii.length >= 6 && nRadius / radii.length >= 0.8) {
    out.push({ id: "K5", sev: "P1", name: "Un seul arrondi appliqué partout", hits: [`${radius} sur ${nRadius}/${radii.length}`] });
  }
  const shadows = [...allCss.matchAll(/box-shadow\s*:\s*([^;}]+)/g)].map((m) => resolve(m[1]).trim()).filter((v) => v !== "none");
  const [shadow, nShadow] = top(shadows);
  if (shadows.length >= 4 && nShadow / shadows.length >= 0.75) {
    out.push({ id: "K6", sev: "P2", name: "La même ombre sous chaque surface", hits: [`${shadow} sur ${nShadow}/${shadows.length}`] });
  }
  const pageBg = cssRules(allCss).filter((r) => /^(html|body|:root)$/.test(r.sel))
    .flatMap((r) => [...r.body.matchAll(/background(?:-color)?\s*:\s*([^;]+)/g)].flatMap((m) => colors(m[1])));
  const all = colors(allCss);
  const acid = (c) => { const x = hsl(c); return x.h >= 75 && x.h <= 150 && x.s > 0.6 && x.l > 0.4 && x.l < 0.7; };
  const vermilion = (c) => { const x = hsl(c); return x.h <= 15 && x.s > 0.7 && x.l > 0.45 && x.l < 0.6; };
  if (pageBg.some(isNearBlack) && all.some((c) => acid(c) || vermilion(c))) {
    out.push({ id: "C8", sev: "P1", name: "Quasi-noir + un unique accent vert acide ou vermillon", hits: ["fond quasi noir"] });
  }
  const pick = (re) => Object.keys(vars).filter((k) => re.test(k)).map((k) => colors(`var(--${k})`)[0]).find((c) => c && isSaturated(c));
  const primary = pick(/^(primary|brand|accent-1)$/), accent = pick(/^(accent|secondary|highlight|signal|accent-2)$/);
  if (primary && accent) {
    const d = Math.abs(hsl(primary).h - hsl(accent).h);
    if (Math.min(d, 360 - d) < 20) out.push({ id: "C9", sev: "P2", name: "Couleur principale et accent quasi identiques", hits: ["écart de teinte < 20°"] });
  }
  const entrances = [...allCss.matchAll(/animation(?:-name)?\s*:\s*([\w-]+)/g)].map((m) => m[1]).filter((n) => !/^(none|inherit)$/.test(n));
  const [entrance, nEntrance] = top(entrances);
  if (nEntrance >= 4 || /@keyframes\s+(fade-?in-?up|fade-?up|slide-?up)\b/i.test(allCss)) {
    out.push({ id: "M5", sev: "P2", name: "La même animation d'entrée partout", hits: [entrance || "fade-up"] });
  }
  return out;
}

function main() {
  const targets = process.argv.slice(2);
  const list = (targets.length ? targets : ["src"]).flatMap(files);
  const parts = list.map((f) => {
    const text = readFileSync(f, "utf8");
    return { file: f, text, ...split(f, text) };
  });
  const allCss = parts.map((p) => p.css).join("\n");
  const all = {
    fontFaces: new Set([...allCss.matchAll(/@font-face\s*\{[^}]*font-family\s*:\s*["']?([^"';}]+)/gi)].map((m) => m[1].trim().toLowerCase())),
    hasFocusVisible: /:focus-visible/.test(allCss),
  };
  const animated = /transition\s*:|animation\s*:|@keyframes/.test(allCss);
  const findings = [];
  for (const p of parts) {
    const allowed = new Set([...p.text.matchAll(/slop-ok:\s*([A-Z]\d)/g)].map((m) => m[1]));
    for (const [id, sev, name, run] of RULES) {
      if (allowed.has(id)) continue;
      const hits = run(p, all);
      if (hits.length) findings.push({ file: relative(process.cwd(), p.file), id, sev, name, hits });
    }
  }
  if (animated && !/prefers-reduced-motion/.test(allCss)) {
    findings.push({ file: "(ensemble)", id: "M4", sev: "P1", name: "Animations sans prefers-reduced-motion", hits: ["@media manquant"] });
  }
  const allowedGlobally = new Set(parts.flatMap((p) => [...p.text.matchAll(/slop-ok:\s*([A-Z]\d)/g)].map((m) => m[1])));
  for (const f of globalRules(allCss)) if (!allowedGlobally.has(f.id)) findings.push({ file: "(ensemble)", ...f });
  findings.sort((a, b) => a.sev.localeCompare(b.sev) || a.file.localeCompare(b.file));
  for (const f of findings) {
    const sample = [...new Set(f.hits)].slice(0, 3).join(" | ");
    console.log(`${f.sev} ${f.id} ${f.file} — ${f.name} (${f.hits.length}) : ${sample}`);
  }
  const blocking = findings.filter((f) => f.sev !== "P2").length;
  console.log(findings.length ? `\n${findings.length} constat(s), dont ${blocking} bloquant(s).` : "Aucun marqueur détecté.");
  process.exit(blocking ? 1 : 0);
}

main();
