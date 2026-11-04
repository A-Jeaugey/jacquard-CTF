#!/usr/bin/env node
// Lance Impeccable sur une page qui demande une connexion : ouvre un Chromium avec un port
// DevTools, se connecte par l'API, ouvre la page, puis laisse Impeccable l'analyser par ce port.
//
//   node scripts/impeccable-connecte.mjs <url> <pseudo:motdepasse> [largeur]

import { spawnSync } from "node:child_process";
import { chromium } from "playwright";

const [url, identifiants, largeur = "1280"] = process.argv.slice(2);
if (!url || !identifiants) {
  console.error("usage : node scripts/impeccable-connecte.mjs <url> <pseudo:motdepasse> [largeur]");
  process.exit(2);
}
const PORT = 9333;
const [username, ...reste] = identifiants.split(":");
const largeurPx = Number(largeur);
const hauteurPx = largeurPx < 600 ? 844 : 800;

const navigateur = await chromium.launch({ args: [`--remote-debugging-port=${PORT}`] });
const contexte = await navigateur.newContext({ viewport: { width: largeurPx, height: hauteurPx }, reducedMotion: "reduce" });
const page = await contexte.newPage();
await page.goto(new URL("/?audit", url).href, { waitUntil: "load" });
const statut = await page.evaluate(async ({ username, password }) => {
  const csrf = document.cookie.match(/jq_csrf=([^;]+)/)?.[1] ?? "";
  const r = await fetch("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf },
    body: JSON.stringify({ username, password }),
  });
  return r.status;
}, { username, password: reste.join(":") });
if (statut !== 200) {
  console.error(`connexion refusée (${statut})`);
  await navigateur.close();
  process.exit(1);
}
await page.goto(url, { waitUntil: "load" });
await page.waitForTimeout(1500);
// Répertoire de travail neutre : Impeccable lit un éventuel DESIGN.md du dossier courant ;
// on le lance depuis le frontend pour qu'il prenne le nôtre.
const resultat = spawnSync("npx", ["-y", "impeccable@4.8.0", "detect", "--json", "--cdp", String(PORT)], { encoding: "utf8" });
let constats = [];
try {
  constats = JSON.parse(resultat.stdout || "[]");
} catch {
  process.stdout.write(resultat.stdout ?? "");
}
process.stderr.write(resultat.stderr ?? "");
if (Array.isArray(constats)) {
  console.log(`Impeccable (page connectée, ${largeurPx} px) : ${constats.length} constat(s).`);
  for (const c of constats) console.log(`- [${c.antipattern ?? c.rule ?? c.id}] ${c.snippet ?? c.message ?? JSON.stringify(c).slice(0, 160)}`);
}
await navigateur.close();
process.exit(resultat.status ?? 1);
