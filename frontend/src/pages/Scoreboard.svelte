<script lang="ts">
  import { untrack } from "svelte";

  import Reessayer from "../components/Reessayer.svelte";
  import { api, errorMessage } from "../lib/api";
  import { formatHeure, formatPoints, poll } from "../lib/format";
  import { live } from "../lib/live.svelte";
  import { session } from "../lib/session.svelte";
  import { t, tn } from "../lib/strings";
  import { typo } from "../lib/typo";
  import type { Scoreboard } from "../lib/types";

  let classement = $state<Scoreboard | null>(null);
  let erreur = $state<string | null>(null);

  async function charger(): Promise<void> {
    try {
      classement = await api.get<Scoreboard>("/api/scoreboard");
      erreur = null;
    } catch (e) {
      erreur = errorMessage(e);
    }
  }

  $effect(() => poll(charger, 60_000));
  $effect(() => {
    void live.ticks.solve;
    void live.ticks.team;
    if (untrack(() => classement)) void charger();
  });

  const monEquipe = $derived(session.me?.team?.id ?? null);

  // La façade d'une équipe : une fenêtre chaude par défi résolu, posée sur un socle.
  const PAS = 9;
  const largeur = (n: number): number => Math.max(n * PAS - 3, 24);
</script>

<div class="page">
  <h1 class="titre-page" id="titre-classement" tabindex="-1">{t("scoreboard.title")}</h1>
  <p class="intro">{t("scoreboard.intro")}</p>

  {#if erreur}
    <div class="etat" role="alert">
      <p class="refus">
        <b>{t("error.title")}</b>
        {erreur}
        {#if classement}{t("error.stale")}{/if}
      </p>
      <p class="relance"><Reessayer action={charger} cible="titre-classement" /></p>
    </div>
  {:else if !classement}
    <p class="secondaire etat">{t("loading")}</p>
  {/if}

  {#if classement}
    <p class="secondaire etat">
      {#if classement.frozen && classement.frozen_at}
        {t("scoreboard.frozen", { time: formatHeure(classement.frozen_at, session.event?.timezone) })}
      {:else}
        {tn("scoreboard.teams", classement.teams.length)}
      {/if}
    </p>
    {#if classement.teams.length}
      <ol class="classement">
        {#each classement.teams as ligne (ligne.team_id)}
          {@const mien = ligne.team_id === monEquipe}
          <li class:mien aria-current={mien ? "true" : undefined}>
            <span class="rang tnum">{ligne.rank}<span class="sup">{ligne.rank === 1 ? "re" : "e"}</span></span>
            <span class="nom">
              {typo(ligne.name)}
              {#if mien}<span class="meta">{t("scoreboard.yours")}</span>{/if}
            </span>
            <span class="facade">
              <svg viewBox="0 0 {largeur(ligne.solves)} 14" width={largeur(ligne.solves)} height="14" aria-hidden="true" focusable="false">
                {#each { length: ligne.solves } as _, i (i)}
                  <rect class="fenetre" x={i * PAS} y="0" width="6" height="10" />
                {/each}
                <rect class="socle" x="0" y="12" width={largeur(ligne.solves)} height="2" />
              </svg>
              <span class="nombre tnum" aria-hidden="true">{ligne.solves}</span>
              <span class="sr-only">{tn("scoreboard.solves", ligne.solves)}</span>
            </span>
            <span class="score tnum">{formatPoints(ligne.score)}</span>
          </li>
        {/each}
      </ol>
    {:else if session.me && !session.me.team}
      <p><a class="btn-principal" href="/team">{t("home.cta.team")}</a></p>
    {/if}
  {/if}
</div>

<style>
  .page {
    max-width: 880px;
  }
  .intro {
    margin-top: var(--e3);
    font-size: var(--t-nom);
    max-width: 56ch;
  }
  .etat {
    margin-top: var(--e3);
  }
  .relance {
    margin-top: var(--e2);
  }
  /* Le fond de « ton équipe » déborde de 8 px ; les filets et le contenu restent alignés. */
  /* Les rangées partagent les colonnes de la liste (subgrid) : façades et points alignés. */
  .classement {
    position: relative;
    isolation: isolate;
    display: grid;
    grid-template-columns: 4rem minmax(0, 1fr) auto auto;
    column-gap: var(--e4);
    margin-top: var(--e5);
    border-top: 1px solid var(--pierre);
  }
  .classement li {
    position: relative;
    grid-column: 1 / -1;
    display: grid;
    grid-template-columns: subgrid;
    align-items: center;
    min-height: 56px;
    padding: var(--e3) 0;
    border-bottom: 1px solid var(--pierre);
  }
  .mien::before {
    content: "";
    position: absolute;
    inset: 0 calc(-1 * var(--e2));
    z-index: -1;
    background: var(--pierre-sombre);
  }
  .rang {
    font-size: 24px;
    font-weight: 700;
    color: var(--douce);
  }
  .classement li:nth-child(-n + 3) .rang {
    color: var(--claire);
  }
  .nom {
    font-size: var(--t-nom);
    overflow-wrap: anywhere;
  }
  .nom .meta {
    margin-left: var(--e2);
  }
  .facade {
    display: flex;
    align-items: center;
    gap: var(--e2);
    min-width: 0;
  }
  .facade svg {
    display: block;
    max-width: 100%;
    height: auto;
  }
  .fenetre {
    fill: var(--lumignon);
  }
  .socle {
    fill: var(--pierre);
  }
  .nombre {
    order: -1;
    min-width: 2ch;
    font-size: var(--t-meta);
    color: var(--douce);
    text-align: right;
  }
  .score {
    font-size: var(--t-nom);
    font-weight: 700;
    text-align: right;
  }
  .mien .nom {
    font-weight: 700;
  }
  .mien .score {
    color: var(--lumignon);
  }
  @media (max-width: 640px) {
    .classement {
      display: block;
    }
    .classement li {
      grid-template-columns: 3rem minmax(0, 1fr) auto;
      grid-template-areas: "rang nom score" ". facade facade";
      column-gap: var(--e4);
      row-gap: var(--e2);
    }
    .rang {
      grid-area: rang;
    }
    .nom {
      grid-area: nom;
    }
    .facade {
      grid-area: facade;
    }
    .score {
      grid-area: score;
    }
  }
</style>
