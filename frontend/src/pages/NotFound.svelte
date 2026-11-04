<script lang="ts">
  import { session } from "../lib/session.svelte";
  import { t } from "../lib/strings";
</script>

<div class="page page-etroite">
  <h1 class="titre-page">{t("error.not_found_title")}</h1>
  <p class="texte">{t("error.not_found")}</p>
  <p class="actions">
    {#if session.me}
      <a class="btn-principal" href="/challenges">{t("error.back_to_board")}</a>
    {/if}
    <a class={session.me ? "btn-ligne" : "btn-principal"} href="/">{t("error.back_home")}</a>
  </p>
</div>

<style>
  .texte {
    margin-top: var(--e3);
    color: var(--douce);
  }
  .actions {
    display: flex;
    flex-wrap: wrap;
    gap: var(--e3);
    margin-top: var(--e5);
  }
</style>
