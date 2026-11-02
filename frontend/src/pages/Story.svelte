<script lang="ts">
  import { live } from "../lib/live.svelte";
  import { markAllSeen, refreshStory, story } from "../lib/story.svelte";
  import { t } from "../lib/strings";

  // Les chapitres non lus à l'ouverture de la page restent marqués « nouveau ».
  let unreadOnOpen = $state<string[]>([]);
  let loaded = $state(false);

  $effect(() => {
    void live.ticks.unlock;
    void refreshStory().then(() => {
      if (!loaded) {
        unreadOnOpen = story.data?.entries.filter((e) => !story.seen.includes(e.id)).map((e) => e.id) ?? [];
        loaded = true;
      }
      markAllSeen();
    });
  });
</script>

<h1>{t("story.title")}</h1>

{#if !story.data}
  <p class="muted">{t("loading")}</p>
{:else}
  {#each story.data.entries as entry (entry.id)}
    <article class="card chapter" class:fresh={unreadOnOpen.includes(entry.id)}>
      <header>
        <h2>{entry.title}</h2>
        {#if unreadOnOpen.includes(entry.id)}<span class="badge new">{t("story.new")}</span>{/if}
      </header>
      <!-- HTML assaini côté serveur. -->
      <div class="prose">{@html entry.body_html}</div>
    </article>
  {:else}
    <p class="muted">{t("story.empty")}</p>
  {/each}
  {#if story.data.locked > 0}
    <p class="muted center">🔒 {t("story.locked", { n: story.data.locked })}</p>
  {/if}
{/if}
