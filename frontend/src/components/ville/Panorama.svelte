<script lang="ts">
  import { untrack } from "svelte";

  import { api } from "../../lib/api";
  import { session } from "../../lib/session.svelte";
  import type { Scoreboard } from "../../lib/types";
  import { etatDe, GABARITS, villeDuClassement, type NomGabarit, type Quartier } from "../../lib/ville";
  import Immeuble from "./Immeuble.svelte";

  // Lyon la nuit, vue du quai : les huit quartiers en ligne d'horizon, devant des toits plus
  // lointains en silhouette ; dessous, la Saône, où chaque fenêtre allumée se reflète. Une
  // fenêtre s'allume dès qu'une équipe a résolu son défi (classement public). Décoratif
  // (aria-hidden) : l'état de chaque défi est dit ailleurs (plan, classement).
  let { quartiers = null }: { quartiers?: Quartier[] | null } = $props();

  // Sans ville fournie (pages d'accès), le panorama lit lui-même le classement public.
  let classement = $state<Scoreboard | null>(null);
  $effect(() => {
    if (quartiers) return;
    api
      .get<Scoreboard>("/api/scoreboard")
      .then((c) => (classement = c))
      .catch(() => {
        // décor : en cas d'échec, la ville reste éteinte
      });
  });
  const ville = $derived(quartiers ?? villeDuClassement(session.event?.categories ?? [], classement));

  // Ordre de la ligne d'horizon et espace avant chaque immeuble (unités du plan).
  const ORDRE: [NomGabarit, number][] = [
    ["basilique", 0],
    ["renaissance", 16],
    ["traboule", 12],
    ["canuts", 20],
    ["musee", 24],
    ["tour", 18],
    ["ecole", 22],
    ["usine", 16],
  ];
  const EAU = 64;

  const rangee = $derived.by(() => {
    let x = 0;
    return ORDRE.flatMap(([nom, ecart]) => {
      const q = ville.find((quartier) => quartier.gabarit === GABARITS[nom]);
      if (!q) return [];
      x += ecart;
      const place = { q, x, ecart };
      x += q.gabarit.w;
      return [place];
    });
  });
  const largeur = $derived(rangee.reduce((fin, b) => Math.max(fin, b.x + b.q.gabarit.w), 0));

  // L'allumage : à la première visite de la session, les fenêtres allumées s'éclairent une à une
  // dans la ville froide (rien si le système demande de réduire les animations). Il se décide
  // une fois, quand les premières lumières arrivent, et rien ne l'interrompt.
  const allumes = $derived(ville.flatMap((q) => q.defis.filter((d) => etatDe(d) === "resolu").map((d) => d.id)));
  const CLE = "jq_allumage_panorama";
  const brouille = (texte: string): number => [...texte].reduce((h, c) => Math.imul(h ^ c.charCodeAt(0), 0x2c1b3c6d) >>> 0, 7);
  let froides = $state<Set<string> | null>(null);
  let decide = false;
  const minuteurs: ReturnType<typeof setTimeout>[] = [];
  $effect(() => {
    const ids = allumes;
    if (decide || ids.length === 0) return;
    decide = true;
    untrack(() => {
      let dejaVu = false;
      try {
        dejaVu = sessionStorage.getItem(CLE) === "1";
        sessionStorage.setItem(CLE, "1");
      } catch {
        // stockage indisponible : l'allumage se rejoue, sans gravité
      }
      if (dejaVu || matchMedia("(prefers-reduced-motion: reduce)").matches) return;
      const ordre = [...ids].sort((a, b) => brouille(a) - brouille(b));
      const pas = Math.min(90, 2000 / ordre.length);
      froides = new Set(ordre);
      ordre.forEach((id, i) =>
        minuteurs.push(
          setTimeout(() => {
            if (!froides) return;
            const suite = new Set(froides);
            suite.delete(id);
            froides = suite;
          }, 400 + i * pas),
        ),
      );
      minuteurs.push(setTimeout(() => (froides = null), 400 + ordre.length * pas + 200));
    });
  });
  $effect(() => () => minuteurs.forEach(clearTimeout));

  // Reflets : trois traits qui s'amenuisent sous chaque fenêtre allumée.
  const reflets = $derived(
    rangee.flatMap(({ q, x }) =>
      q.fenetres.flatMap((f, i) => {
        const defi = q.defis[i];
        if (!defi || etatDe(defi) !== "resolu" || froides?.has(defi.id)) return [];
        const cx = x + f.x + f.w / 2;
        return [0.9, 0.6, 0.35].map((k, j) => ({ x: cx - (f.w * k) / 2, y: 8 + j * 9, w: f.w * k }));
      }),
    ),
  );

  // Toits lointains, avec quelques fenêtres éteintes : une rangée déterministe.
  const LOIN = 3200;
  const lointains = (() => {
    const toits: string[] = [];
    const fenetres: string[] = [];
    let graine = 7;
    const hasard = (): number => {
      graine = (graine * 16807) % 2147483647;
      return graine / 2147483647;
    };
    let x = 0;
    while (x < LOIN) {
      const w = 34 + Math.round(hasard() * 56);
      const h = 40 + Math.round(hasard() * 110);
      const y = 200 - h;
      const toit = hasard();
      if (toit < 0.35) toits.push(`M${x} 200V${y + 10}L${x + w / 2} ${y}L${x + w} ${y + 10}V200Z`);
      else if (toit < 0.5) toits.push(`M${x} 200V${y}H${x + w}V200Z M${x + w * 0.7} ${y}v-9h5v9Z`);
      else toits.push(`M${x} 200V${y}H${x + w}V200Z`);
      for (let fy = y + 18; fy < 186; fy += 14) {
        for (let fx = x + 8; fx < x + w - 8; fx += 12) {
          if (hasard() < 0.22) fenetres.push(`M${fx} ${fy}h4v6h-4Z`);
        }
      }
      x += w + Math.round(hasard() * 6);
    }
    return { toits: toits.join(" "), fenetres: fenetres.join(" ") };
  })();
</script>

<div class="panorama" aria-hidden="true">
  <svg class="loin" viewBox="0 0 {LOIN} 200" preserveAspectRatio="xMidYMax slice" focusable="false">
    <path class="silhouette" d={lointains.toits} />
    <path class="fenetres-loin" d={lointains.fenetres} />
  </svg>
  <div class="rangee" style:--largeur={largeur}>
    {#each rangee as { q, ecart } (q.categorie.id)}
      <div class="bat" style:--w={q.gabarit.w} style:--ecart={ecart}>
        <Immeuble quartier={q} {froides} />
      </div>
    {/each}
  </div>
  <div class="saone">
    <svg class="reflets" viewBox="0 0 {largeur} {EAU}" style:--largeur={largeur} focusable="false">
      {#each reflets as r, i (i)}
        <rect x={r.x} y={r.y} width={r.w} height="3" />
      {/each}
    </svg>
  </div>
</div>

<style>
  /* Une unité du plan en pixels : la ligne d'horizon grandit avec la largeur de l'écran et
     prend la hauteur que lui laissent l'en-tête et le titre (environ 420 px ; le panorama
     mesure 298 unités de haut) ; sur un petit écran, elle reste lisible et ses bords sont
     rognés. */
  .panorama {
    --u: clamp(0.78px, min(0.06vw + 0.5px, (100svh - 420px) / 298), 2.1px);
    position: relative;
    overflow: hidden;
    padding-top: calc(var(--u) * 24);
  }
  .loin {
    position: absolute;
    left: 0;
    right: 0;
    bottom: calc(var(--u) * 64);
    width: 100%;
    height: calc(var(--u) * 170);
  }
  .silhouette {
    fill: var(--toit);
    stroke: var(--pierre);
    stroke-width: 1;
    vector-effect: non-scaling-stroke;
  }
  .fenetres-loin {
    fill: var(--pierre-sombre);
  }
  .rangee {
    position: relative;
    display: flex;
    align-items: flex-end;
    width: calc(var(--u) * var(--largeur));
    /* Centrée, même plus large que l'écran. */
    margin-left: 50%;
    transform: translateX(-50%);
  }
  .bat {
    flex: none;
    width: calc(var(--u) * var(--w));
    margin-left: calc(var(--u) * var(--ecart));
  }
  .bat:first-child {
    margin-left: 0;
  }
  .saone {
    position: relative;
    height: calc(var(--u) * 64);
    background: var(--eau);
    border-top: 2px solid var(--lumen);
  }
  .reflets {
    display: block;
    width: calc(var(--u) * var(--largeur));
    height: 100%;
    margin-left: 50%;
    transform: translateX(-50%);
  }
  .reflets rect {
    fill: var(--lumignon);
  }
</style>
