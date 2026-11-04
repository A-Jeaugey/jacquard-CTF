<script lang="ts">
  import { tick } from "svelte";

  import { formatHeure } from "../lib/format";
  import { session } from "../lib/session.svelte";
  import { t } from "../lib/strings";

  // « Réessayer » : le même comportement partout. Pendant la relance, le bouton garde le focus
  // (aria-disabled plutôt que disabled) et dit qu'il travaille, au moins un court instant pour
  // qu'un nouvel échec reste perceptible. Si la relance réussit, le bouton disparaît avec
  // l'erreur et le focus va au contenu rechargé (`cible`).
  let { action, cible = null }: { action: () => Promise<unknown>; cible?: string | null } = $props();

  let envoi = $state(false);
  let bouton = $state<HTMLButtonElement>();
  // Un nouvel échec doit se voir (et s'entendre) : l'erreur affichée, elle, ne change pas.
  let echec = $state<string | null>(null);
  let essais = 1;

  async function relancer(): Promise<void> {
    if (envoi) return;
    envoi = true;
    // Le message du dernier échec ne reste pas affiché pendant le nouvel essai.
    echec = null;
    try {
      await Promise.all([action(), new Promise((fin) => setTimeout(fin, 400))]);
    } finally {
      envoi = false;
    }
    await tick();
    if (bouton?.isConnected) {
      // Numéroté, et vidé avant d'être rempli : deux échecs dans la même minute restent
      // deux messages distincts, vus et annoncés.
      essais += 1;
      echec = null;
      await tick();
      echec = t("action.retry_failed", { n: essais, time: formatHeure(new Date().toISOString(), session.event?.timezone) });
      return;
    }
    if (cible) document.getElementById(cible)?.focus();
  }
</script>

<span class="relance">
  <button
    type="button"
    class="btn-ligne"
    bind:this={bouton}
    aria-disabled={envoi ? "true" : undefined}
    onclick={relancer}
  >
    {envoi ? t("action.retrying") : t("action.retry")}
  </button>
  <span class="echec" role="status">{echec ?? ""}</span>
</span>

<style>
  .relance {
    display: inline-flex;
    flex-wrap: wrap;
    align-items: center;
    gap: var(--e2) var(--e3);
  }
  .echec {
    font-size: var(--t-meta);
    color: var(--douce);
  }
</style>
