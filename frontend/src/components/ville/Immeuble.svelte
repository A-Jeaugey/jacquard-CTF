<script lang="ts">
  import { cheminFenetre, etatDe, fil, type Quartier } from "../../lib/ville";

  // L'élévation d'un quartier : la même sur la carte et dans le panneau d'un défi.
  let {
    quartier,
    avecFil = false,
    cadre = null,
    froides = null,
    retrait = false,
    nuit = false,
  }: {
    quartier: Quartier;
    /** Montrer le fil de soie (quartier choisi, panneau). */
    avecFil?: boolean;
    /** Identifiant du défi dont la fenêtre est cadrée. */
    cadre?: string | null;
    /** Fenêtres encore froides pendant l'allumage. */
    froides?: Set<string> | null;
    /** Quartier mis en retrait : silhouette sans couleur d'état. */
    retrait?: boolean;
    /** Grand écran : les fenêtres non résolues sont éteintes (sombres), pas verrouillées. */
    nuit?: boolean;
  } = $props();

  const g = $derived(quartier.gabarit);
  const troncons = $derived(avecFil ? fil(quartier) : []);
</script>

<svg
  class="bati"
  class:retrait
  class:nuit
  viewBox="0 0 {g.w} {g.h + 4}"
  aria-hidden="true"
  focusable="false"
>
  {#each g.dessin as forme, i (i)}
    {#if forme.el === "rect"}
      <rect class={forme.c} x={forme.x} y={forme.y} width={forme.w} height={forme.h} />
    {:else if forme.el === "polygon"}
      <polygon class={forme.c} points={forme.points} />
    {:else}
      <path class={forme.c} d={forme.d} />
    {/if}
  {/each}
  {#each quartier.defis as defi, i (defi.id)}
    {@const f = quartier.fenetres[i]}
    {#if f}
      {@const etat = froides?.has(defi.id) ? "verrouille" : etatDe(defi)}
      {#if f.arc}
        <path class="fen" data-etat={etat} d={cheminFenetre(f)} />
      {:else}
        <rect class="fen" data-etat={etat} x={f.x} y={f.y} width={f.w} height={f.h} />
      {/if}
      {#if cadre === defi.id}
        <rect class="cadre" x={f.x - 4} y={f.y - 4} width={f.w + 8} height={f.h + 8} />
      {/if}
    {/if}
  {/each}
  <rect class="socle" x={g.socle.x} y={g.h} width={g.socle.w} height="4" />
  {#each troncons as troncon (troncon.vers)}
    <path class="fil" data-etat={troncon.etat} d={troncon.d} />
  {/each}
</svg>

<style>
  .bati {
    display: block;
    width: 100%;
    height: auto;
    overflow: visible;
  }
  .facade,
  .socle {
    fill: var(--pierre);
  }
  .toit {
    fill: var(--toit);
  }
  .passage {
    fill: var(--eau);
  }
  .couronne {
    fill: var(--lumen);
  }
  .fen {
    fill: var(--eau);
    stroke: var(--claire);
    stroke-width: 2;
  }
  .fen[data-etat="resolu"] {
    fill: var(--lumignon);
    stroke: none;
  }
  .fen[data-etat="verrouille"] {
    fill: var(--lumen);
    stroke: none;
  }
  .cadre {
    fill: none;
    stroke: var(--claire);
    stroke-width: 2;
  }
  .fil {
    fill: none;
    stroke-width: 3;
    stroke-linecap: round;
    vector-effect: non-scaling-stroke;
  }
  .fil[data-etat="resolu"] {
    stroke: var(--lumignon);
  }
  .fil[data-etat="disponible"] {
    stroke: var(--douce);
  }
  .fil[data-etat="verrouille"] {
    stroke: var(--lumen);
    stroke-dasharray: 4 4;
    stroke-linecap: butt;
  }
  /* Nuit (grand écran) : seules les fenêtres rallumées brillent. */
  .nuit .fen:not([data-etat="resolu"]) {
    fill: var(--eau);
    stroke: none;
  }
  /* Quartier en retrait : une silhouette, sans couleur d'état (jetons, pas d'opacité). */
  .retrait .facade,
  .retrait .socle,
  .retrait .couronne {
    fill: var(--toit);
  }
  .retrait .fen,
  .retrait .fen[data-etat] {
    fill: var(--pierre);
    stroke: none;
  }
</style>
