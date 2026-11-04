<script lang="ts">
  import { t } from "../../lib/strings";
  import { NOMS_RIVIERES, PLAN, PONTS, RIVIERES, type Quartier } from "../../lib/ville";
  import Immeuble from "./Immeuble.svelte";

  // Le plan de nuit : la chose mémorable de l'interface (frontend/DESIGN.md).
  let {
    quartiers,
    choisi = null,
    ouvert = null,
    allumage = [],
    onChoisir,
  }: {
    quartiers: Quartier[];
    /** Catégorie choisie (filtre). */
    choisi?: string | null;
    /** Défi ouvert dans le panneau : son quartier est mis en avant, sa fenêtre cadrée. */
    ouvert?: string | null;
    /** Défis résolus dans l'ordre réel des résolutions, pour l'allumage. */
    allumage?: string[];
    onChoisir: (categorie: string) => void;
  } = $props();

  const enAvant = $derived(
    ouvert ? (quartiers.find((q) => q.defis.some((d) => d.id === ouvert))?.categorie.id ?? choisi) : choisi,
  );

  // L'allumage, seul moment orchestré : au premier affichage de la session, tout est froid,
  // puis les fenêtres résolues s'allument une à une dans l'ordre des résolutions.
  const CLE = "jq_allumage";
  let froides = $state<Set<string> | null>(null);
  let lance = false;
  $effect(() => {
    if (lance || allumage.length === 0) return;
    lance = true;
    let dejaVu = false;
    try {
      dejaVu = sessionStorage.getItem(CLE) === "1";
      sessionStorage.setItem(CLE, "1");
    } catch {
      // stockage indisponible : l'allumage se rejoue, sans gravité
    }
    if (dejaVu || matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const toutes = new Set(quartiers.flatMap((q) => q.defis.filter((d) => d.solved).map((d) => d.id)));
    froides = toutes;
    const minuteurs = allumage.map((id, i) =>
      setTimeout(() => {
        if (!froides) return;
        const suite = new Set(froides);
        suite.delete(id);
        froides = suite;
      }, 700 + i * 110),
    );
    minuteurs.push(setTimeout(() => (froides = null), 700 + allumage.length * 110 + 260));
    return () => minuteurs.forEach(clearTimeout);
  });

  const pct = (valeur: number, total: number): string => `${(valeur / total) * 100}%`;
</script>

<div class="carte" class:en-avant={enAvant !== null}>
  <svg class="fond" viewBox="0 0 {PLAN.w} {PLAN.h}" preserveAspectRatio="none" aria-hidden="true" focusable="false">
    {#each RIVIERES as riviere (riviere.points)}
      <polyline class="quai" points={riviere.points} stroke-width={riviere.largeur + 4} />
    {/each}
    {#each RIVIERES as riviere (riviere.points)}
      <polyline class="eau" points={riviere.points} stroke-width={riviere.largeur} />
    {/each}
    {#each PONTS as [x, y, w] (`${x}-${y}`)}
      <rect class="pont" {x} {y} width={w} height="4" />
    {/each}
  </svg>
  {#each NOMS_RIVIERES as riviere (riviere.nom)}
    <span
      class="riviere"
      aria-hidden="true"
      style:left={pct(riviere.x, PLAN.w)}
      style:top={pct(riviere.y, PLAN.h)}
      style:--angle="{riviere.angle}deg">{riviere.nom}</span
    >
  {/each}
  {#each quartiers as q (q.categorie.id)}
    {@const avance = enAvant === q.categorie.id}
    <button
      type="button"
      class="quartier"
      class:avance
      data-categorie={q.categorie.id}
      aria-pressed={choisi === q.categorie.id}
      aria-label={t("board.district_label", { name: q.categorie.name, n: q.resolus, total: q.defis.length })}
      style:left={pct(q.x, PLAN.w)}
      style:top={pct(q.y, PLAN.h)}
      style:width={pct(q.w, PLAN.w)}
      onclick={() => onChoisir(q.categorie.id)}
    >
      <Immeuble
        quartier={q}
        avecFil={avance}
        cadre={avance ? ouvert : null}
        {froides}
        retrait={enAvant !== null && !avance}
      />
      <span class="repere">
        <span class="nom">{q.categorie.name}</span>
      </span>
    </button>
  {/each}
</div>

<style>
  .carte {
    position: relative;
    width: 100%;
    aspect-ratio: 600 / 650;
    container-type: inline-size;
  }
  .fond {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    display: block;
  }
  .quai {
    fill: none;
    stroke: var(--lumen);
    stroke-linejoin: miter;
  }
  .eau {
    fill: none;
    stroke: var(--eau);
    stroke-linejoin: miter;
  }
  .pont {
    fill: var(--pierre);
  }
  .riviere {
    position: absolute;
    transform: translate(-50%, -50%) rotate(var(--angle));
    font-style: italic;
    font-size: var(--t-texte);
    line-height: 1;
    color: var(--douce);
    white-space: nowrap;
    pointer-events: none;
  }
  .quartier {
    position: absolute;
    display: block;
    min-width: 44px;
    padding: 0;
    border: 0;
    background: none;
    color: var(--claire);
    text-align: center;
  }
  .quartier:focus-visible {
    outline-offset: 8px;
  }
  .repere {
    position: relative;
    left: 50%;
    transform: translateX(-50%);
    display: flex;
    flex-direction: column;
    align-items: center;
    width: max-content;
    margin-top: var(--e1);
    pointer-events: none;
  }
  .nom {
    font-family: var(--display);
    font-size: 24px;
    line-height: 1;
    padding: var(--e1) var(--e1) 0;
  }
  @container (max-width: 600px) {
    .nom {
      font-size: 21px;
    }
  }
  @media (hover: hover) {
    .quartier:hover .nom {
      text-decoration: underline;
      text-decoration-thickness: 1px;
      text-underline-offset: 4px;
    }
  }
  .quartier[aria-pressed="true"] .nom {
    background: var(--claire);
    color: var(--nuit);
    text-decoration: none;
  }
  .en-avant .quartier:not(.avance) .nom {
    color: var(--douce);
  }
</style>
