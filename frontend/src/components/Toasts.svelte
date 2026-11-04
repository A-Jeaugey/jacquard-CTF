<script lang="ts">
  import { dismissToast, toasts } from "../lib/live.svelte";
  import { t } from "../lib/strings";

  // Les événements en direct : des lignes de chronique empilées en bas de l'écran, sans boîte
  // flottante ni ombre ; un filet au-dessus, comme la chronique sous la carte.
</script>

<div class="chroniques" role="status" aria-live="polite">
  {#each toasts as toast (toast.id)}
    <p class="chronique" data-kind={toast.kind}>
      <span class="texte">{toast.text}</span>
      <button type="button" class="btn-texte" onclick={() => dismissToast(toast.id)}>{t("live.dismiss")}</button>
    </p>
  {/each}
</div>

<style>
  .chroniques {
    position: fixed;
    left: var(--gouttiere);
    bottom: var(--e4);
    z-index: 60;
    display: grid;
    gap: var(--e2);
    width: min(480px, calc(100vw - 2 * var(--gouttiere)));
  }
  .chronique {
    display: flex;
    align-items: center;
    gap: var(--e4);
    padding: var(--e2) var(--e4);
    background: var(--eau);
    border-top: 1px solid var(--pierre);
  }
  .chronique[data-kind="success"] {
    border-top-color: var(--lumignon);
  }
  .texte {
    flex: 1;
  }
</style>
