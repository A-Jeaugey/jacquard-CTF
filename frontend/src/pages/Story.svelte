<script lang="ts">
  import { live } from "../lib/live.svelte";
  import { markAllSeen, refreshStory, story } from "../lib/story.svelte";
  import { t, tn } from "../lib/strings";
  import { typo, typographie } from "../lib/typo";

  // Les messages non lus à l'ouverture de la page (ou arrivés pendant la visite) sont
  // précédés d'un seul repère, « Depuis ta dernière visite », s'ils ne sont pas tous nouveaux.
  let nouveaux = $state<string[]>([]);
  let charge = $state(false);

  async function charger(): Promise<void> {
    await refreshStory();
    if (!story.data) return;
    const nonLus = story.data.entries.filter((e) => !story.seen.includes(e.id)).map((e) => e.id);
    nouveaux = charge ? [...nouveaux, ...nonLus] : nonLus;
    charge = true;
    markAllSeen();
  }

  $effect(() => {
    void live.ticks.unlock;
    void charger();
  });

  const entrees = $derived(story.data?.entries ?? []);
  const premierNouveau = $derived(entrees.find((e) => nouveaux.includes(e.id))?.id ?? null);
  const tousNouveaux = $derived(entrees.length > 0 && entrees.every((e) => nouveaux.includes(e.id)));
</script>

<div class="page page-etroite">
  <h1 class="titre-page">{t("story.title")}</h1>
  {#if !story.data && story.erreur}
    <p class="refus etat" role="alert"><b>{t("error.title")}</b> {story.erreur}</p>
    <p><button type="button" class="btn-ligne" onclick={charger}>{t("action.retry")}</button></p>
  {:else if !story.data}
    <p class="secondaire etat">{t("loading")}</p>
  {:else}
    {#if nouveaux.length > 0}
      <p class="etat" role="status">{tn("story.unread_count", nouveaux.length)}</p>
    {/if}
    {#each entrees as message (message.id)}
      {#if message.id === premierNouveau && !tousNouveaux}
        <p class="repere">{t("story.since_last_visit")}</p>
      {/if}
      <article class="message" aria-labelledby="m-{message.id}">
        <h2 class="titre-section" id="m-{message.id}">{typo(message.title)}</h2>
        <!-- HTML assaini côté serveur. -->
        <div class="prose" use:typographie>{@html message.body_html}</div>
      </article>
    {:else}
      <p class="secondaire etat">{t("story.empty")}</p>
      <p><a class="btn-ligne" href="/challenges">{t("team.go_board")}</a></p>
    {/each}
    {#if story.data.locked > 0}
      <p class="chiffres">{tn("story.locked", story.data.locked)}</p>
    {/if}
  {/if}
</div>

<style>
  .etat {
    margin-top: var(--e3);
  }
  .repere {
    margin-top: var(--e7);
    font-weight: 700;
    border-bottom: 2px solid var(--claire);
    padding-bottom: var(--e2);
  }
  .repere + .message {
    border-top: 0;
    margin-top: var(--e4);
    padding-top: 0;
  }
  .message {
    margin-top: var(--e6);
    padding-top: var(--e5);
    border-top: 1px solid var(--pierre);
  }
  .message .prose {
    margin-top: var(--e4);
    font-size: var(--t-nom);
  }
  .titre-section {
    overflow-wrap: anywhere;
  }
  .chiffres {
    margin-top: var(--e6);
    padding-top: var(--e4);
    border-top: 1px solid var(--pierre);
    color: var(--voile);
  }
</style>
