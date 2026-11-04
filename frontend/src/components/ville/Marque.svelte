<script lang="ts">
  import type { Etat } from "../../lib/ville";

  // La fenêtre-marque 12 × 18 : pleine chaude (résolu), vide cadrée (disponible), pleine
  // froide (verrouillé). Même forme partout ; l'état est aussi écrit en toutes lettres à côté.
  let { etat }: { etat: Etat } = $props();
</script>

<svg class="marque" data-etat={etat} viewBox="0 0 12 18" aria-hidden="true" focusable="false">
  <rect x="1" y="1" width="10" height="16" />
</svg>

<style>
  .marque {
    width: 12px;
    height: 18px;
    flex: none;
    display: block;
  }
  rect {
    fill: var(--eau);
    stroke: var(--claire);
    stroke-width: 2;
  }
  [data-etat="resolu"] rect {
    fill: var(--lumignon);
    stroke: none;
  }
  [data-etat="verrouille"] rect {
    fill: var(--lumen);
    stroke: none;
  }
</style>
