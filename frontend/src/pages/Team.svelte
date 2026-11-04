<script lang="ts">
  import { tick } from "svelte";

  import PageAcces from "../components/PageAcces.svelte";
  import FilDeSoie from "../components/ville/FilDeSoie.svelte";
  import Marque from "../components/ville/Marque.svelte";
  import { api, errorMessage } from "../lib/api";
  import { refreshEquipe } from "../lib/equipe.svelte";
  import { formatHeure, formatPoints } from "../lib/format";
  import { live } from "../lib/live.svelte";
  import { navigate } from "../lib/router.svelte";
  import { refreshMe, session } from "../lib/session.svelte";
  import { t, tn } from "../lib/strings";
  import { typo } from "../lib/typo";
  import type { TeamDetail } from "../lib/types";

  let equipe = $state<TeamDetail | null>(null);
  let charge = $state(false);
  let nom = $state("");
  let code = $state("");
  let erreur = $state<string | null>(null);
  let envoi = $state(false);
  let confirmerDepart = $state(false);
  let copie = $state<string | null>(null);

  const modeEquipes = $derived(session.event?.participation.mode === "teams");
  const heure = (iso: string): string => formatHeure(iso, session.event?.timezone);

  async function charger(): Promise<void> {
    try {
      equipe = await api.get<TeamDetail | null>("/api/teams/me");
      charge = true;
      erreur = null;
    } catch (e) {
      erreur = errorMessage(e);
    }
  }

  async function agir(action: () => Promise<unknown>): Promise<void> {
    envoi = true;
    erreur = null;
    try {
      await action();
      await Promise.all([charger(), refreshMe()]);
      void refreshEquipe();
    } catch (e) {
      erreur = errorMessage(e);
    } finally {
      envoi = false;
    }
  }

  function creer(event: SubmitEvent): void {
    event.preventDefault();
    void agir(() => api.post("/api/teams", { name: nom }));
  }

  function rejoindre(event: SubmitEvent): void {
    event.preventDefault();
    void agir(() => api.post("/api/teams/join", { invite_code: code.trim() }));
  }

  async function quitter(): Promise<void> {
    confirmerDepart = false;
    await agir(() => api.post("/api/teams/leave"));
  }

  async function demanderDepart(): Promise<void> {
    confirmerDepart = true;
    await tick();
    document.getElementById("confirmer-depart")?.focus();
  }

  async function copier(texte: string): Promise<void> {
    try {
      await navigator.clipboard.writeText(texte);
      copie = t("team.invite_copied");
    } catch {
      copie = t("team.invite_copy_blocked");
    }
  }

  $effect(() => {
    void live.ticks.team;
    if (!session.me) navigate("/login", true);
    else void charger();
  });

  /** Le motif binaire d'un objet (« motif : ●○●○… »), s'il y en a un. */
  const motif = (description: string | null): string | null => description?.match(/[●○]{4,}/)?.[0] ?? null;
</script>

{#if !charge}
  <div class="page">
    {#if erreur}
      <p class="refus" role="alert"><b>{t("error.title")}</b> {erreur}</p>
      <button type="button" class="btn-ligne" onclick={charger}>{t("action.retry")}</button>
    {:else}
      <p class="secondaire">{t("loading")}</p>
    {/if}
  </div>
{:else if equipe}
  <div class="page equipe">
    <h1 class="titre-page">{typo(equipe.name)}</h1>
    <p class="bilan">
      {#if equipe.rank}
        {equipe.rank}<span class="sup">e</span> {t("team.rank_sentence")},
      {/if}
      <b class="score tnum">{formatPoints(equipe.score)}</b>.
      {tn("team.solved_count", equipe.solves.length)}
      {#if equipe.penalty > 0}{t("team.penalty", { points: formatPoints(equipe.penalty) })}{/if}
    </p>

    {#if erreur}<p class="refus" role="alert"><b>{t("error.title")}</b> {erreur}</p>{/if}

    <div class="colonnes">
      <div>
        <section class="bloc" aria-labelledby="h-fils">
          <h2 class="titre-section" id="h-fils">{t("team.items")}</h2>
          {#if equipe.items.length}
            <ul class="fils">
              {#each equipe.items as objet (objet.id)}
                <li>
                  <p class="fil-nom">{typo(objet.name)}</p>
                  <FilDeSoie motif={motif(objet.description)} />
                  {#if objet.description}<p class="meta">{typo(objet.description)}</p>{/if}
                </li>
              {/each}
            </ul>
          {:else}
            <p class="secondaire">{t("team.no_items")}</p>
            <p><a class="btn-ligne" href="/challenges">{t("team.go_board")}</a></p>
          {/if}
        </section>

        <section class="bloc" aria-labelledby="h-resolus">
          <h2 class="titre-section" id="h-resolus">{t("team.solves")}</h2>
          {#if equipe.solves.length}
            <ol class="resolus">
              {#each equipe.solves as r (r.challenge_id)}
                <li>
                  <Marque etat="resolu" />
                  <span class="r-nom">{typo(r.challenge_name)}</span>
                  <span class="r-pts tnum">{formatPoints(r.points)}</span>
                  <span class="r-qui">{t("team.solved_by", { user: r.solved_by ?? "—", time: heure(r.solved_at) })}</span>
                </li>
              {/each}
            </ol>
          {:else}
            <p class="secondaire">{t("team.no_solves")}</p>
            <p><a class="btn-ligne" href="/challenges">{t("team.go_board")}</a></p>
          {/if}
        </section>
      </div>

      <div>
        {#if equipe.invite_code}
          <section class="bloc" aria-labelledby="h-invitation">
            <h2 class="titre-bloc" id="h-invitation">{t("team.invite")}</h2>
            <p class="aide">{t("team.invite_hint")}</p>
            <div class="code">
              <span class="code-valeur tnum">{equipe.invite_code}</span>
              <button type="button" class="btn-ligne" onclick={() => copier(equipe?.invite_code ?? "")}>{t("challenge.copy")}</button>
            </div>
            <p class="meta" role="status">{copie ?? ""}</p>
          </section>
        {:else if !modeEquipes}
          <p class="secondaire bloc">{t("team.solo")}</p>
        {/if}

        <section class="bloc" aria-labelledby="h-membres">
          <h2 class="titre-bloc" id="h-membres">{t("team.members_title", { n: equipe.members.length, max: equipe.max_size })}</h2>
          <ul class="membres">
            {#each equipe.members as membre (membre.id)}<li>{membre.username}</li>{/each}
          </ul>
        </section>

        {#if modeEquipes && equipe.solves.length === 0}
          <section class="bloc depart">
            {#if confirmerDepart}
              <p>{t("team.leave.confirm")}</p>
              <p class="choix">
                <button type="button" class="btn-ligne" id="confirmer-depart" disabled={envoi} onclick={quitter}>{t("team.leave")}</button>
                <button type="button" class="btn-texte" onclick={() => (confirmerDepart = false)}>{t("action.cancel")}</button>
              </p>
            {:else}
              <button type="button" class="btn-texte" onclick={demanderDepart}>{t("team.leave")}</button>
            {/if}
          </section>
        {/if}
      </div>
    </div>
  </div>
{:else if modeEquipes}
  <PageAcces>
    <h1 class="titre-page">{t("team.join_title")}</h1>
    <p class="intro secondaire">{t("team.join_intro")}</p>
    {#if erreur}<p class="refus" role="alert"><b>{t("team.refused")}</b> {erreur}</p>{/if}
    <form class="formulaire" onsubmit={rejoindre}>
      <h2 class="titre-bloc">{t("team.join")}</h2>
      <div class="champ">
        <label for="code">{t("team.join.code")}</label>
        <input id="code" class="saisie" bind:value={code} required autocomplete="off" autocapitalize="characters" />
      </div>
      <p><button type="submit" class="btn-principal" disabled={envoi}>{t("team.join.submit")}</button></p>
    </form>
    <form class="formulaire" onsubmit={creer}>
      <h2 class="titre-bloc">{t("team.create")}</h2>
      <div class="champ">
        <label for="nom">{t("team.create.name")}</label>
        <input id="nom" class="saisie" bind:value={nom} required minlength="2" maxlength="64" />
      </div>
      <p><button type="submit" class="btn-ligne" disabled={envoi}>{t("team.create.submit")}</button></p>
    </form>
  </PageAcces>
{/if}

<style>
  .bilan {
    margin-top: var(--e3);
    font-size: var(--t-nom);
    color: var(--douce);
    max-width: 64ch;
  }
  .score {
    color: var(--lumignon);
  }
  .colonnes {
    display: grid;
    grid-template-columns: minmax(0, 3fr) minmax(0, 2fr);
    gap: var(--e7);
    margin-top: var(--e4);
  }
  .bloc {
    margin-top: var(--e6);
  }
  .bloc > h2 {
    margin-bottom: var(--e3);
  }
  .fils {
    display: grid;
    gap: var(--e4);
    border-top: 1px solid var(--pierre);
    padding-top: var(--e4);
  }
  .fils li {
    display: grid;
    gap: var(--e1);
  }
  .fil-nom {
    font-weight: 700;
  }
  .resolus {
    border-top: 1px solid var(--pierre);
  }
  .resolus li {
    display: grid;
    grid-template-columns: 12px minmax(0, 1fr) auto;
    grid-template-areas: "m nom pts" ". qui qui";
    column-gap: var(--e3);
    row-gap: var(--e1);
    align-items: baseline;
    padding: var(--e3) 0;
    border-bottom: 1px solid var(--pierre);
  }
  .resolus :global(.marque) {
    grid-area: m;
    align-self: start;
    margin-top: var(--e1);
  }
  .r-nom {
    grid-area: nom;
    font-size: var(--t-nom);
    overflow-wrap: anywhere;
  }
  .r-pts {
    grid-area: pts;
  }
  .r-qui {
    grid-area: qui;
    font-size: var(--t-meta);
    color: var(--douce);
  }
  .code {
    display: flex;
    flex-wrap: wrap;
    gap: var(--e2);
    margin-top: var(--e3);
  }
  .code-valeur {
    display: inline-flex;
    align-items: center;
    min-height: 44px;
    padding: 0 var(--e4);
    background: var(--eau);
    border-radius: 2px;
    font-size: 24px;
    font-weight: 700;
  }
  .membres li {
    padding: var(--e2) 0;
    border-bottom: 1px solid var(--pierre);
  }
  .depart {
    padding-top: var(--e4);
    border-top: 1px solid var(--pierre);
  }
  .choix {
    display: flex;
    flex-wrap: wrap;
    gap: var(--e3);
    align-items: center;
    margin-top: var(--e2);
  }
  .intro {
    margin-top: var(--e3);
  }
  .formulaire {
    display: grid;
    gap: var(--e4);
    margin-top: var(--e6);
    padding-top: var(--e5);
    border-top: 1px solid var(--pierre);
  }
  @media (max-width: 900px) {
    .colonnes {
      grid-template-columns: minmax(0, 1fr);
      gap: 0;
    }
  }
</style>
