<script lang="ts">
  import { dismissToast, toasts } from "../lib/live.svelte";
  import { t } from "../lib/strings";
</script>

<div class="toasts" role="status" aria-live="polite">
  {#each toasts as toast (toast.id)}
    <div class={`toast ${toast.kind}`}>
      <span>{toast.text}</span>
      <button class="link" aria-label={t("challenge.close")} onclick={() => dismissToast(toast.id)}>✕</button>
    </div>
  {/each}
</div>
