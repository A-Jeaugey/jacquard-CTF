<script lang="ts">
  import { untrack } from "svelte";

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
</script>

<div class="page">
  <h1 class="titre-page">{t("scoreboard.title")}</h1>
  <p class="intro">{t("scoreboard.intro")}</p>

  {#if erreur}
    <p class="refus" role="alert"><b>{t("error.title")}</b> {erreur}</p>
    <p><button type="button" class="btn-ligne" onclick={charger}>{t("action.retry")}</button></p>
  {:else if !classement}
    <p class="secondaire etat">{t("loading")}</p>
  {:else}
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
            <span class="defis meta">{tn("scoreboard.solves", ligne.solves)}</span>
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
  .classement {
    margin-top: var(--e5);
    border-top: 1px solid var(--pierre);
  }
  .classement li {
    display: grid;
    grid-template-columns: 4rem minmax(0, 1fr) auto auto;
    align-items: baseline;
    column-gap: var(--e4);
    min-height: 56px;
    padding: var(--e3) var(--e2);
    margin: 0 calc(-1 * var(--e2));
    border-bottom: 1px solid var(--pierre);
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
  .score {
    font-size: var(--t-nom);
    font-weight: 700;
    text-align: right;
  }
  .mien {
    background: var(--pierre-sombre);
  }
  .mien .nom {
    font-weight: 700;
  }
  .mien .score {
    color: var(--lumignon);
  }
  @media (max-width: 640px) {
    .classement li {
      grid-template-columns: 3rem minmax(0, 1fr) auto;
      grid-template-areas: "rang nom score" ". defis defis";
    }
    .rang {
      grid-area: rang;
    }
    .nom {
      grid-area: nom;
    }
    .defis {
      grid-area: defis;
    }
    .score {
      grid-area: score;
    }
  }
</style>
