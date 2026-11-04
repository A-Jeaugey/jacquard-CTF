<script lang="ts">
  import PageAcces from "../components/PageAcces.svelte";
  import { session } from "../lib/session.svelte";
  import { t } from "../lib/strings";
</script>

<PageAcces>
  <h1 class="titre-page">{t("error.not_found_title")}</h1>
  <p class="texte">{t("error.not_found")}</p>
  <p class="actions">
    {#if session.me}
      <a class="btn-principal" href="/challenges">{t("error.back_to_board")}</a>
    {:else}
      <a class="btn-principal" href="/">{t("error.back_home")}</a>
    {/if}
  </p>
</PageAcces>

<style>
  .texte {
    margin-top: var(--e3);
    font-size: var(--t-nom);
  }
  .actions {
    margin-top: var(--e5);
  }
</style>
