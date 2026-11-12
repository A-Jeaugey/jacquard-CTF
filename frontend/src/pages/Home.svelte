<script lang="ts">
  import Reessayer from "../components/Reessayer.svelte";
  import Panorama3D from "../components/ville/Panorama3D.svelte";
  import { carteGraphique } from "../lib/carte-graphique";
  import { api, errorMessage } from "../lib/api";
  import { equipe } from "../lib/equipe.svelte";
  import { formatDateTime, formatPlage, formatPoints, poll } from "../lib/format";
  import { live } from "../lib/live.svelte";
  import { inscriptionsOuvertes, session } from "../lib/session.svelte";
  import { story } from "../lib/story.svelte";
  import { t, tn } from "../lib/strings";
  import { typo, typographie } from "../lib/typo";
  import type { Announcement, Scoreboard } from "../lib/types";
  import { villeDuClassement } from "../lib/ville";

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

  // Le classement public dit quelles fenêtres de la ville sont allumées : une fenêtre s'allume
  // dès qu'une équipe a résolu son défi. Sans lui, le panorama reste la ville froide de LUMEN.
  let classement = $state<Scoreboard | null>(null);
  async function chargerClassement(): Promise<void> {
    try {
      classement = await api.get<Scoreboard>("/api/scoreboard");
    } catch {
      // décor : en cas d'échec, la ville reste éteinte
    }
  }
  $effect(() => poll(chargerClassement, 60_000));
  $effect(() => {
    if (live.ticks.solve > 0) void chargerClassement();
  });
  const quartiers = $derived(villeDuClassement(session.event?.categories ?? [], classement));
  const resolus = $derived((classement?.teams ?? []).reduce((total, e) => total + e.solves, 0));
  $effect(() => {
    if (live.ticks.announcement > 0) void charger();
  });

  const evenement = $derived(session.event);
  const prologue = $derived(story.data?.entries.filter((e) => e.public) ?? []);
  const phase = $derived(evenement?.phase ?? "running");
  const inscriptions = $derived(inscriptionsOuvertes());

  // Le quai en volume (frontend/DESIGN.md) prend toute la scène d'ouverture, derrière le texte.
  let volume = $state(carteGraphique());
</script>

{#if evenement}
  <div class="accueil">
    <div class="scene" class:en-volume={volume}>
    <div class="intro">
      <!-- Le nom de l'événement est déjà le logotype de l'en-tête : le titre est son accroche. -->
      <h1 class="titre-page">{evenement.tagline ? typo(evenement.tagline) : evenement.name}</h1>
      <div class="details">
      <p class="dates">{formatPlage(evenement.schedule.start, evenement.schedule.end, evenement.timezone)}.</p>
      {#if classement && phase !== "not_started"}
        <p class="ce-soir">
          <span>{tn("screen.active_teams", classement.teams.length)}</span>
          <span>{tn("screen.progress", resolus)}</span>
        </p>
      {/if}
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
    </div>

    <div class="panorama-zone">
      <Panorama3D {quartiers} bind:volume />
    </div>
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


  </div>
{/if}

<style>
  .titre-page {
    overflow-wrap: anywhere;
  }
  .accueil {
    padding: 0 var(--gouttiere) var(--e8);
  }
  /* La scène d'ouverture tient dans le premier écran : le titre en haut, Lyon la nuit posée au
     bas de l'écran, quelle que soit sa hauteur (la taille du panorama suit aussi la hauteur). */
  .scene {
    display: flex;
    flex-direction: column;
    padding-top: var(--e6);
  }
  .intro .titre-page {
    max-width: 22ch;
  }
  .equipe {
    margin-top: var(--e3);
    font-size: var(--t-nom);
  }
  .dates {
    margin-top: var(--e3);
    color: var(--douce);
    font-size: var(--t-nom);
  }
  .ce-soir {
    display: grid;
    gap: var(--e1);
    margin-top: var(--e2);
    font-size: var(--t-nom);
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
  /* Pleine largeur de l'écran, au-delà du cadre : la ville déborde des bords. */
  .panorama-zone {
    width: 100vw;
    margin-left: calc(50% - 50vw);
    margin-top: auto;
    padding-top: var(--e5);
  }
  /* En volume : le quai, la Saône et le ciel occupent toute la scène d'ouverture, sous le
     texte (le haut du ciel a la couleur de la page). Sur un écran étroit, c'est un bloc sous
     le texte. */
  @media (max-width: 1099px) {
    .scene.en-volume .panorama-zone {
      height: clamp(260px, 66vw, 460px);
      padding-top: 0;
    }
  }
  .suite {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
    column-gap: var(--e7);
    align-items: start;
  }
  .chapitre,
  .annonces {
    margin-top: var(--e7);
    padding-top: var(--e5);
    border-top: 1px solid var(--pierre);
    max-width: 640px;
  }
  .chapitre .prose {
    margin-top: var(--e4);
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

  @media (min-width: 1100px) {
    /* L'écran moins l'en-tête, sur une ligne à partir de 1100 px (64 px et son filet). */
    .scene {
      min-height: calc(100svh - 65px);
    }
    .scene.en-volume {
      position: relative;
    }
    .scene.en-volume .intro {
      position: relative;
      z-index: 1;
    }
    .scene.en-volume .panorama-zone {
      position: absolute;
      top: 0;
      bottom: 0;
      left: 0;
      height: auto;
      margin-top: 0;
    }
  }
  /* Écran large : le titre à gauche, les dates, la soirée et l'action à sa droite. */
  @media (min-width: 900px) {
    .intro {
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(260px, 380px);
      column-gap: var(--e7);
      align-items: end;
    }
    .details > :first-child {
      margin-top: 0;
    }
  }
  @media (min-width: 1280px) and (min-height: 760px) {
    .intro .titre-page {
      font-size: 72px;
    }
  }
  @media (min-width: 1800px) and (min-height: 1100px) {
    .intro .titre-page {
      font-size: 96px;
    }
  }
  @media (max-width: 900px) {
    .suite {
      grid-template-columns: minmax(0, 1fr);
    }
  }
  @media (max-width: 640px) {
    .accueil {
      padding-top: var(--e5);
    }
  }
</style>
