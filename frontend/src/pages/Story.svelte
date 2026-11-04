<script lang="ts">
  import { live } from "../lib/live.svelte";
  import { markAllSeen, refreshStory, story } from "../lib/story.svelte";
  import { t, tn } from "../lib/strings";
  import { typo, typographie } from "../lib/typo";

  // Les messages non lus à l'ouverture de la page restent marqués « nouveau ».
  let nonLusALOuverture = $state<string[]>([]);
  let charge = $state(false);

  $effect(() => {
    void live.ticks.unlock;
    void refreshStory().then(() => {
      if (!charge) {
        nonLusALOuverture = story.data?.entries.filter((e) => !story.seen.includes(e.id)).map((e) => e.id) ?? [];
        charge = true;
      }
      markAllSeen();
    });
  });
</script>

<div class="page page-etroite">
  <h1 class="titre-page">{t("story.title")}</h1>
  {#if !story.data}
    <p class="secondaire etat">{t("loading")}</p>
  {:else}
    {#each story.data.entries as message (message.id)}
      {@const nouveau = nonLusALOuverture.includes(message.id)}
      <article class="message" aria-labelledby="m-{message.id}">
        {#if nouveau}<p class="nouveau">{t("story.new")}</p>{/if}
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
  .message {
    margin-top: var(--e6);
    padding-top: var(--e5);
    border-top: 1px solid var(--pierre);
  }
  .nouveau {
    margin-bottom: var(--e2);
    font-weight: 700;
    color: var(--lumignon);
  }
  .message .prose {
    margin-top: var(--e4);
    font-size: var(--t-nom);
  }
  .chiffres {
    margin-top: var(--e6);
    padding-top: var(--e4);
    border-top: 1px solid var(--pierre);
    color: var(--voile);
  }
</style>
