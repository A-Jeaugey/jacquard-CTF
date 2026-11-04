<script lang="ts">
  import { tick } from "svelte";

  import PageAcces from "../components/PageAcces.svelte";
  import FilDeSoie from "../components/ville/FilDeSoie.svelte";
  import Marque from "../components/ville/Marque.svelte";
  import { api, ApiError, errorMessage } from "../lib/api";
  import { refreshEquipe } from "../lib/equipe.svelte";
  import { formatHeure, formatPoints } from "../lib/format";
  import { live } from "../lib/live.svelte";
  import { navigate } from "../lib/router.svelte";
  import { refreshMe, session } from "../lib/session.svelte";
  import { t, tn } from "../lib/strings";
  import { typo } from "../lib/typo";
  import type { TeamDetail } from "../lib/types";

  type Action = "rejoindre" | "creer" | "quitter";

  let equipe = $state<TeamDetail | null>(null);
  let charge = $state(false);
  let nom = $state("");
  let code = $state("");
  let erreurChargement = $state<string | null>(null);
  // L'erreur d'une action s'affiche à côté de ce qui l'a provoquée.
  let erreur = $state<{ action: Action; titre: string; texte: string; champ: boolean } | null>(null);
  let envoi = $state<Action | null>(null);
  let confirmerDepart = $state(false);
  let copie = $state<string | null>(null);
  let minuteurCopie: ReturnType<typeof setTimeout> | undefined;

  const modeEquipes = $derived(session.event?.participation.mode === "teams");
  const heure = (iso: string): string => formatHeure(iso, session.event?.timezone);

  async function charger(): Promise<void> {
    try {
      equipe = await api.get<TeamDetail | null>("/api/teams/me");
      charge = true;
      erreurChargement = null;
    } catch (e) {
      erreurChargement = errorMessage(e);
    }
  }

  async function agir(action: Action, requete: () => Promise<unknown>): Promise<void> {
    envoi = action;
    erreur = null;
    let reussi = false;
    try {
      await requete();
      await Promise.all([charger(), refreshMe()]);
      void refreshEquipe();
      reussi = true;
    } catch (e) {
      const refus = e instanceof ApiError && e.status >= 400 && e.status < 500;
      erreur = {
        action,
        titre: refus ? t("team.refused") : t("error.title"),
        texte: errorMessage(e),
        champ: refus && action !== "quitter",
      };
    } finally {
      envoi = null;
    }
    await tick();
    if (reussi) document.getElementById("titre-equipe")?.focus();
    else if (action === "rejoindre") document.getElementById(erreur?.champ ? "code" : "envoyer-code")?.focus();
    else if (action === "creer") document.getElementById(erreur?.champ ? "nom" : "envoyer-nom")?.focus();
    else document.getElementById("quitter")?.focus();
  }

  function creer(event: SubmitEvent): void {
    event.preventDefault();
    void agir("creer", () => api.post("/api/teams", { name: nom }));
  }

  function rejoindre(event: SubmitEvent): void {
    event.preventDefault();
    void agir("rejoindre", () => api.post("/api/teams/join", { invite_code: code.trim() }));
  }

  async function quitter(): Promise<void> {
    confirmerDepart = false;
    await agir("quitter", () => api.post("/api/teams/leave"));
  }

  async function demanderDepart(): Promise<void> {
    confirmerDepart = true;
    await tick();
    document.getElementById("confirmer-depart")?.focus();
  }

  async function annulerDepart(): Promise<void> {
    confirmerDepart = false;
    await tick();
    document.getElementById("quitter")?.focus();
  }

  function clavier(event: KeyboardEvent): void {
    if (event.key === "Escape" && confirmerDepart) {
      event.preventDefault();
      void annulerDepart();
    }
  }

  async function copier(texte: string): Promise<void> {
    try {
      await navigator.clipboard.writeText(texte);
      copie = t("team.invite_copied");
    } catch {
      copie = t("team.invite_copy_blocked");
    }
    clearTimeout(minuteurCopie);
    minuteurCopie = setTimeout(() => (copie = null), 4000);
  }

  $effect(() => {
    void live.ticks.team;
    if (!session.me) navigate("/login", true);
    else void charger();
  });
  $effect(() => () => clearTimeout(minuteurCopie));

  /** Le motif binaire d'un objet (« motif : ●○●○… »), s'il y en a un. */
  const motif = (description: string | null): string | null => description?.match(/[●○]{4,}/)?.[0] ?? null;

  // Les défis résolus, par quartier, dans l'ordre des quartiers de l'événement.
  const parQuartier = $derived.by(() => {
    if (!equipe) return [];
    const categories = session.event?.categories ?? [];
    const groupes = categories
      .map((c) => ({ id: c.id, nom: c.name, defis: equipe?.solves.filter((s) => s.category === c.id) ?? [] }))
      .filter((g) => g.defis.length > 0);
    const connus = new Set(categories.map((c) => c.id));
    const autres = equipe.solves.filter((s) => !connus.has(s.category));
    if (autres.length) groupes.push({ id: "", nom: t("team.solves"), defis: autres });
    return groupes;
  });
</script>

<svelte:window onkeydown={clavier} />

{#snippet refus(action: Action)}
  {#if erreur?.action === action}
    <p class="refus" id="erreur-{action}" role="alert"><b>{erreur.titre}</b> {erreur.texte}</p>
  {/if}
{/snippet}

{#if !charge}
  <div class="page">
    {#if erreurChargement}
      <p class="refus" role="alert"><b>{t("error.title")}</b> {erreurChargement}</p>
      <p><button type="button" class="btn-ligne" onclick={charger}>{t("action.retry")}</button></p>
    {:else}
      <p class="secondaire">{t("loading")}</p>
    {/if}
  </div>
{:else if equipe}
  <div class="page equipe">
    <h1 class="titre-page" id="titre-equipe" tabindex="-1">{typo(equipe.name)}</h1>
    <p class="bilan">
      {#if equipe.rank}
        {equipe.rank}<span class="sup">e</span> {t("team.rank_sentence")},
      {/if}
      <b class="score tnum">{formatPoints(equipe.score)}</b>.
      {tn("team.solved_count", equipe.solves.length)}
      {#if equipe.penalty > 0}{t("team.penalty", { points: formatPoints(equipe.penalty) })}{/if}
    </p>

    <div class="haut">
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
      </div>
      <div>
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
                <button type="button" class="btn-ligne" id="confirmer-depart" disabled={envoi !== null} onclick={quitter}>{t("team.leave")}</button>
                <button type="button" class="btn-texte" onclick={annulerDepart}>{t("action.cancel")}</button>
              </p>
            {:else}
              <button type="button" class="btn-texte" id="quitter" onclick={demanderDepart}>{t("team.leave")}</button>
            {/if}
            {@render refus("quitter")}
          </section>
        {/if}
      </div>
    </div>

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
      {#each parQuartier as groupe (groupe.id)}
        <h3 class="titre-bloc quartier">{groupe.nom}</h3>
        <ol class="resolus">
          {#each groupe.defis as r (r.challenge_id)}
            <li>
              <Marque etat="resolu" />
              <span class="r-nom">{typo(r.challenge_name)}</span>
              <span class="r-qui">
                <b>{t("board.row.solved")}</b>
                {t("team.solved_by", { user: r.solved_by ?? "—", time: heure(r.solved_at), points: formatPoints(r.points) })}
              </span>
            </li>
          {/each}
        </ol>
      {:else}
        <p class="secondaire">{t("team.no_solves")}</p>
        <p><a class="btn-ligne" href="/challenges">{t("team.go_board")}</a></p>
      {/each}
    </section>
  </div>
{:else if modeEquipes}
  <PageAcces>
    <h1 class="titre-page" id="titre-equipe" tabindex="-1">{t("team.join_title")}</h1>
    <p class="intro">{t("team.join_intro")}</p>
    <form class="formulaire" onsubmit={rejoindre}>
      <h2 class="titre-bloc">{t("team.join")}</h2>
      <div class="champ">
        <label for="code">{t("team.join.code")}</label>
        <input
          id="code"
          class="saisie"
          bind:value={code}
          required
          autocomplete="off"
          autocapitalize="characters"
          aria-invalid={erreur?.action === "rejoindre" && erreur.champ ? "true" : undefined}
          aria-describedby={erreur?.action === "rejoindre" ? "erreur-rejoindre" : undefined}
          oninput={() => erreur?.action === "rejoindre" && (erreur = null)}
        />
      </div>
      {@render refus("rejoindre")}
      <p>
        <button type="submit" class="btn-principal" id="envoyer-code" disabled={envoi !== null}>
          {envoi === "rejoindre" ? t("team.joining") : t("team.join.submit")}
        </button>
      </p>
    </form>
    <form class="formulaire" onsubmit={creer}>
      <h2 class="titre-bloc">{t("team.create")}</h2>
      <div class="champ">
        <label for="nom">{t("team.create.name")}</label>
        <input
          id="nom"
          class="saisie"
          bind:value={nom}
          required
          minlength="2"
          maxlength="64"
          aria-invalid={erreur?.action === "creer" && erreur.champ ? "true" : undefined}
          aria-describedby={erreur?.action === "creer" ? "erreur-creer" : undefined}
          oninput={() => erreur?.action === "creer" && (erreur = null)}
        />
      </div>
      {@render refus("creer")}
      <p>
        <button type="submit" class="btn-ligne" id="envoyer-nom" disabled={envoi !== null}>
          {envoi === "creer" ? t("team.creating") : t("team.create.submit")}
        </button>
      </p>
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
  .equipe {
    max-width: 880px;
  }
  .titre-page {
    overflow-wrap: anywhere;
  }
  .haut {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
    gap: var(--e6);
  }
  .bloc {
    margin-top: var(--e6);
  }
  .bloc > h2 {
    margin-bottom: var(--e3);
  }
  .fils {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(min(100%, 320px), 1fr));
    gap: var(--e5) var(--e6);
    border-top: 1px solid var(--pierre);
    padding-top: var(--e4);
  }
  .fils li {
    display: grid;
    gap: var(--e1);
    min-width: 0;
    overflow-wrap: anywhere;
  }
  .fil-nom {
    font-weight: 700;
  }
  .quartier {
    margin-top: var(--e5);
    margin-bottom: var(--e2);
  }
  .resolus {
    border-top: 1px solid var(--pierre);
  }
  .resolus li {
    display: grid;
    grid-template-columns: 12px minmax(0, 1fr);
    grid-template-areas: "m nom" ". qui";
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
  .r-qui {
    grid-area: qui;
    font-size: var(--t-meta);
    color: var(--douce);
  }
  /* Même rangée que sur le plan : le mot « Résolu » en gras, couleur du résolu. */
  .r-qui b {
    color: var(--lumignon);
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
    overflow-wrap: anywhere;
  }
  .depart {
    padding-top: var(--e4);
    border-top: 1px solid var(--pierre);
  }
  .depart .refus {
    margin-top: var(--e2);
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
    font-size: var(--t-nom);
  }
  .formulaire {
    display: grid;
    gap: var(--e4);
    margin-top: var(--e6);
    padding-top: var(--e5);
    border-top: 1px solid var(--pierre);
  }
  @media (max-width: 760px) {
    .haut {
      grid-template-columns: minmax(0, 1fr);
      gap: 0;
    }
  }
</style>
