<script lang="ts">
  import { tick } from "svelte";

  import { t } from "../lib/strings";

  // « Réessayer » : le même comportement partout. Pendant la relance, le bouton garde le focus
  // (aria-disabled plutôt que disabled) et dit qu'il travaille, au moins un court instant pour
  // qu'un nouvel échec reste perceptible. Si la relance réussit, le bouton disparaît avec
  // l'erreur et le focus va au contenu rechargé (`cible`).
  let { action, cible = null }: { action: () => Promise<unknown>; cible?: string | null } = $props();

  let envoi = $state(false);
  let bouton = $state<HTMLButtonElement>();

  async function relancer(): Promise<void> {
    if (envoi) return;
    envoi = true;
    try {
      await Promise.all([action(), new Promise((fin) => setTimeout(fin, 400))]);
    } finally {
      envoi = false;
    }
    await tick();
    if (bouton?.isConnected) return;
    if (cible) document.getElementById(cible)?.focus();
  }
</script>

<button
  type="button"
  class="btn-ligne"
  bind:this={bouton}
  aria-disabled={envoi ? "true" : undefined}
  onclick={relancer}
>
  {envoi ? t("action.retrying") : t("action.retry")}
</button>
