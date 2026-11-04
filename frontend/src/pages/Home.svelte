<script lang="ts">
  import Reessayer from "../components/Reessayer.svelte";
  import Decor from "../components/ville/Decor.svelte";
  import { api, errorMessage } from "../lib/api";
  import { equipe } from "../lib/equipe.svelte";
  import { formatDateTime, formatPlage, formatPoints, poll } from "../lib/format";
  import { live } from "../lib/live.svelte";
  import { inscriptionsOuvertes, session } from "../lib/session.svelte";
  import { story } from "../lib/story.svelte";
  import { t } from "../lib/strings";
  import { typo, typographie } from "../lib/typo";
  import type { Announcement } from "../lib/types";

  let annonces = $state<Announcement[]>([]);
  let annoncesChargees = $state(false);
  let erreurAnnonces = $state<string | null>(null);

  async function charger(): Promise<void> {
    try {
      annonces = await api.get<Announcement[]>("/api/announcements");
      annoncesChargees = true;
      erreurAnnonces = null;
    } catch (e) {
      erreurAnnonces = errorMessage(e);
    }
  }

  $effect(() => poll(charger, 120_000));
  $effect(() => {
    if (live.ticks.announcement > 0) void charger();
  });

  const evenement = $derived(session.event);
  const prologue = $derived(story.data?.entries.filter((e) => e.public) ?? []);
  const phase = $derived(evenement?.phase ?? "running");
  const inscriptions = $derived(inscriptionsOuvertes());
</script>

{#if evenement}
  <div class="accueil">
    <div class="intro">
      <!-- Le nom de l'événement est déjà le logotype de l'en-tête : le titre est son accroche. -->
      <h1 class="titre-page">{evenement.tagline ? typo(evenement.tagline) : evenement.name}</h1>
      <p class="dates">{formatPlage(evenement.schedule.start, evenement.schedule.end, evenement.timezone)}.</p>
      {#if phase === "not_started"}
        <p class="phase">{t("home.phase.not_started")}</p>
      {:else if phase === "ended"}
        <p class="phase">{t("home.phase.ended")}</p>
      {/if}
      {#if session.me?.team}
        <p class="equipe">
          {#if equipe.data?.rank}
            {t("home.team_rank_start", { team: session.me.team.name })}
            {equipe.data.rank}<span class="sup">e</span>
            {t("home.team_rank_end", { total: equipe.nombreEquipes, points: formatPoints(equipe.data.score) })}
          {:else}
            {t("home.team_no_score", { team: session.me.team.name })}
          {/if}
        </p>
      {/if}
      <p class="actions">
        {#if phase === "ended"}
          <a class="btn-principal" href="/scoreboard">{t("home.cta.scoreboard")}</a>
        {:else if !session.me}
          <!-- La connexion est dans l'en-tête : une seule action ici. -->
          <a class="btn-principal" href={inscriptions ? "/register" : "/login"}>{inscriptions ? t("nav.register") : t("nav.login")}</a>
        {:else if !session.me.team && session.me.user.role !== "admin"}
          <a class="btn-principal" href="/team">{t("home.cta.team")}</a>
        {:else if phase === "not_started"}
          <a class="btn-principal" href="/team">{t("home.cta.my_team")}</a>
        {:else}
          <a class="btn-principal" href="/challenges">{t("home.cta.board")}</a>
        {/if}
      </p>
    </div>

    <div class="suite">
      <!-- Le prologue pour les visiteurs ; les joueurs le retrouvent dans leurs messages. -->
      {#each session.me ? [] : prologue as chapitre (chapitre.id)}
        <article class="chapitre" aria-labelledby="ch-{chapitre.id}">
          <h2 class="titre-section" id="ch-{chapitre.id}">{typo(chapitre.title)}</h2>
          <!-- HTML assaini côté serveur. -->
          <div class="prose" use:typographie>{@html chapitre.body_html}</div>
        </article>
      {/each}

      <section class="annonces" aria-labelledby="h-annonces" id="annonces">
        <h2 class="titre-section" id="h-annonces" tabindex="-1">{t("home.announcements")}</h2>
        {#if erreurAnnonces && !annoncesChargees}
          <p class="refus" role="alert"><b>{t("error.title")}</b> {erreurAnnonces}</p>
          <p><Reessayer action={charger} cible="h-annonces" /></p>
        {:else if !annoncesChargees}
          <p class="secondaire">{t("loading")}</p>
        {/if}
        {#each annonces as annonce (annonce.id)}
          <article class="annonce">
            <h3 class="titre-bloc">{typo(annonce.title)}</h3>
            <p class="meta">{formatDateTime(annonce.created_at, evenement.timezone)}</p>
            <!-- HTML assaini côté serveur. -->
            <div class="prose" use:typographie>{@html annonce.body_html}</div>
          </article>
        {:else}
          {#if annoncesChargees}<p class="secondaire">{t("home.no_announcements")}</p>{/if}
        {/each}
      </section>
    </div>

    <div class="illustration">
      <Decor />
    </div>
  </div>
{/if}

<style>
  .titre-page {
    overflow-wrap: anywhere;
  }
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
  .equipe {
    margin-top: var(--e3);
    font-size: var(--t-nom);
  }
  .dates {
    margin-top: var(--e2);
    color: var(--douce);
  }
  .phase {
    margin-top: var(--e3);
    max-width: 48ch;
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
    justify-self: end;
    width: 100%;
    max-width: 640px;
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
      justify-self: start;
      max-width: 520px;
    }
  }
  @media (max-width: 640px) {
    .accueil {
      padding-top: var(--e5);
    }
  }
</style>
