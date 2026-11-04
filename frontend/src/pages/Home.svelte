<script lang="ts">
  import Decor from "../components/ville/Decor.svelte";
  import { api } from "../lib/api";
  import { formatDateTime, formatPlage, poll } from "../lib/format";
  import { live } from "../lib/live.svelte";
  import { session } from "../lib/session.svelte";
  import { story } from "../lib/story.svelte";
  import { t } from "../lib/strings";
  import { typo, typographie } from "../lib/typo";
  import type { Announcement } from "../lib/types";

  let annonces = $state<Announcement[]>([]);

  async function charger(): Promise<void> {
    annonces = await api.get<Announcement[]>("/api/announcements").catch(() => annonces);
  }

  $effect(() => poll(charger, 120_000));
  $effect(() => {
    if (live.ticks.announcement > 0) void charger();
  });

  const evenement = $derived(session.event);
  const prologue = $derived(story.data?.entries.filter((e) => e.public) ?? []);
  const inscriptions = $derived(evenement?.participation.registration !== "closed");
</script>

{#if evenement}
  <div class="accueil">
    <div class="intro">
      <h1 class="titre-page">{evenement.name}</h1>
      {#if evenement.tagline}<p class="accroche">{typo(evenement.tagline)}</p>{/if}
      <p class="dates">{formatPlage(evenement.schedule.start, evenement.schedule.end, evenement.timezone)}.</p>
      <p class="actions">
        {#if !session.me}
          {#if inscriptions}<a class="btn-principal" href="/register">{t("home.cta.register")}</a>{/if}
          <a class={inscriptions ? "btn-ligne" : "btn-principal"} href="/login">{t("nav.login")}</a>
        {:else if !session.me.team && session.me.user.role !== "admin"}
          <a class="btn-principal" href="/team">{t("home.cta.team")}</a>
        {:else}
          <a class="btn-principal" href="/challenges">{t("home.cta.board")}</a>
        {/if}
      </p>
    </div>

    <div class="suite">
      {#each prologue as chapitre (chapitre.id)}
        <article class="chapitre" aria-labelledby="ch-{chapitre.id}">
          <h2 class="titre-section" id="ch-{chapitre.id}">{typo(chapitre.title)}</h2>
          <!-- HTML assaini côté serveur. -->
          <div class="prose" use:typographie>{@html chapitre.body_html}</div>
        </article>
      {/each}

      <section class="annonces" aria-labelledby="h-annonces" id="annonces">
        <h2 class="titre-section" id="h-annonces">{t("home.announcements")}</h2>
        {#each annonces as annonce (annonce.id)}
          <article class="annonce">
            <h3 class="titre-bloc">{typo(annonce.title)}</h3>
            <p class="meta">{formatDateTime(annonce.created_at, evenement.timezone)}</p>
            <!-- HTML assaini côté serveur. -->
            <div class="prose" use:typographie>{@html annonce.body_html}</div>
          </article>
        {:else}
          <p class="secondaire">{t("home.no_announcements")}</p>
        {/each}
      </section>
    </div>

    <div class="illustration">
      <Decor />
    </div>
  </div>
{/if}

<style>
  .accueil {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
    grid-template-areas: "intro illustration" "suite illustration";
    grid-template-rows: auto 1fr;
    column-gap: var(--e7);
    align-items: start;
    padding: var(--e6) var(--gouttiere) var(--e8);
  }
  .intro {
    grid-area: intro;
    max-width: 640px;
  }
  .suite {
    grid-area: suite;
    max-width: 640px;
  }
  .accroche {
    margin-top: var(--e3);
    font-size: var(--t-nom);
  }
  .dates {
    margin-top: var(--e2);
    color: var(--douce);
  }
  .actions {
    display: flex;
    flex-wrap: wrap;
    gap: var(--e3);
    margin-top: var(--e5);
  }
  .chapitre {
    margin-top: var(--e7);
    padding-top: var(--e5);
    border-top: 1px solid var(--pierre);
  }
  .chapitre .prose {
    margin-top: var(--e4);
  }
  .annonces {
    margin-top: var(--e7);
    padding-top: var(--e5);
    border-top: 1px solid var(--pierre);
  }
  .annonces > p {
    margin-top: var(--e3);
  }
  .annonce {
    padding: var(--e4) 0;
    border-bottom: 1px solid var(--pierre);
  }
  .annonce .meta {
    margin-top: var(--e1);
  }
  .annonce .prose {
    margin-top: var(--e3);
  }
  .illustration {
    grid-area: illustration;
    position: sticky;
    top: var(--e5);
  }

  @media (max-width: 900px) {
    .accueil {
      grid-template-columns: minmax(0, 1fr);
      grid-template-areas: "intro" "illustration" "suite";
      grid-template-rows: none;
      row-gap: var(--e6);
    }
    .illustration {
      position: static;
      max-width: 520px;
    }
  }
  @media (max-width: 640px) {
    .accueil {
      padding-top: var(--e5);
    }
  }
</style>
