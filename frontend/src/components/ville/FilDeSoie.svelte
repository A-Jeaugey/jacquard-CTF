<script lang="ts">
  // Un fil de soie gagné, dessiné avec ses nœuds : un gros nœud pour ●, un petit pour ○.
  // Le motif vient de la description de l'objet dans le pack (« motif : ●○●○… ») ; sans
  // motif, le fil est dessiné seul.
  let { motif = null, manquant = false }: { motif?: string | null; manquant?: boolean } = $props();

  const noeuds = $derived(motif ? [...motif].filter((c) => c === "●" || c === "○") : []);
  const largeur = 240;
  const pas = $derived(noeuds.length ? largeur / (noeuds.length + 1) : 0);
</script>

<svg class="fil-soie" class:manquant viewBox="0 0 {largeur} 24" aria-hidden="true" focusable="false">
  <path class="brin" d="M0 12 Q{largeur / 2} 18 {largeur} 12" />
  {#each noeuds as noeud, i (i)}
    {@const x = pas * (i + 1)}
    {@const y = 12 + 12 * (x / largeur) * (1 - x / largeur)}
    {#if noeud === "●"}
      <circle class="noeud plein" cx={x} cy={y} r="6" />
    {:else}
      <circle class="noeud" cx={x} cy={y} r="2.5" />
    {/if}
  {/each}
</svg>

<style>
  .fil-soie {
    display: block;
    width: 100%;
    max-width: 240px;
    height: 24px;
    overflow: visible;
  }
  .brin {
    fill: none;
    stroke: var(--lumignon);
    stroke-width: 2;
    vector-effect: non-scaling-stroke;
  }
  .noeud {
    fill: var(--lumignon);
  }
  .manquant .brin {
    stroke: var(--lumen);
    stroke-dasharray: 4 4;
  }
</style>
