<script lang="ts">
  import { tick } from "svelte";

  import PageAcces from "../components/PageAcces.svelte";
  import Reessayer from "../components/Reessayer.svelte";
  import FilDeSoie from "../components/ville/FilDeSoie.svelte";
  import Immeuble from "../components/ville/Immeuble.svelte";
  import { api, ApiError, errorMessage } from "../lib/api";
  import { refreshEquipe } from "../lib/equipe.svelte";
  import { formatHeure, formatPoints } from "../lib/format";
  import { live } from "../lib/live.svelte";
  import { navigate } from "../lib/router.svelte";
  import { refreshMe, session } from "../lib/session.svelte";
  import { t, tn } from "../lib/strings";
  import { typo } from "../lib/typo";
  import type { ChallengeSummary, TeamDetail } from "../lib/types";
  import { construireVille } from "../lib/ville";

  type Action = "rejoindre" | "creer" | "quitter";

  let equipe = $state<TeamDetail | null>(null);
  // Les défis de l'équipe, pour dessiner l'immeuble de chaque quartier (facultatif).
  let defis = $state<ChallengeSummary[]>([]);
  let charge = $state(false);
  let nom = $state("");
  let code = $state("");
  let erreurChargement = $state<string | null>(null);
  // Les immeubles n'ont pas pu être dessinés (liste des défis indisponible).
  let erreurDefis = $state<string | null>(null);
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
      return;
    }
    if (equipe) await chargerDefis();
  }

  async function chargerDefis(): Promise<void> {
    try {
      defis = (await api.get<{ challenges: ChallengeSummary[] }>("/api/challenges")).challenges;
      erreurDefis = null;
    } catch (e) {
      // Sans la liste des défis, la page reste lisible : seuls les immeubles manquent. On le dit
      // quand il n'y a rien à dessiner (une liste déjà chargée reste valable).
      if (!defis.length) erreurDefis = errorMessage(e);
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

  // Les défis résolus, par quartier, dans l'ordre des quartiers de l'événement, chacun avec
  // l'immeuble de son quartier tel que l'équipe le voit sur le plan.
  const ville = $derived(
    defis.length ? construireVille(session.event?.categories ?? [], defis, session.event?.difficulties ?? []) : null,
  );
  const parQuartier = $derived.by(() => {
    if (!equipe) return [];
    const categories = session.event?.categories ?? [];
    const groupes = categories
      .map((c) => ({
        id: c.id,
        nom: c.name,
        quartier: ville?.find((q) => q.categorie.id === c.id) ?? null,
        defis: equipe?.solves.filter((s) => s.category === c.id) ?? [],
      }));
    // Tous les quartiers de l'événement restent affichés, même sans défi résolu ni dessin.
    const connus = new Set(categories.map((c) => c.id));
    const autres = equipe.solves.filter((s) => !connus.has(s.category));
    if (autres.length) groupes.push({ id: "", nom: t("team.solves"), quartier: null, defis: autres });
    return groupes;
  });

  const enPhrase = new Intl.ListFormat("fr", { style: "long", type: "conjunction" });
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
      <p><Reessayer action={charger} cible="titre-equipe" /></p>
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

    <section class="bloc" aria-labelledby="h-resolus">
      <h2 class="titre-section" id="h-resolus" tabindex="-1">{t("team.districts")}</h2>
      {#if erreurDefis}
        <div class="manque" role="alert">
          <p class="refus"><b>{t("error.title")}</b> {t("team.buildings_missing")} {erreurDefis}</p>
          <p><Reessayer action={chargerDefis} cible="h-resolus" /></p>
        </div>
      {/if}
      {#if !equipe.solves.length}
        <p class="secondaire">{t("team.no_solves")}</p>
        <p><a class="btn-ligne" href="/challenges">{t("team.go_board")}</a></p>
      {/if}
      {#each parQuartier as groupe (groupe.id)}
        <div class="q-tete">
          {#if groupe.quartier}
            <div class="q-dessin">
              <Immeuble quartier={groupe.quartier} />
            </div>
          {/if}
          <div>
            <h3 class="titre-bloc">{groupe.nom}</h3>
            {#if groupe.quartier}
              <!-- L'immeuble montre l'avancement ; on le dit aux lecteurs d'écran. -->
              <p class="sr-only">{tn("board.done", groupe.quartier.resolus, { total: groupe.quartier.defis.length })}</p>
            {/if}
          </div>
        </div>
        {#if groupe.defis.length}
          <ol class="resolus">
            {#each groupe.defis as r (r.challenge_id)}
              <li>
                <span class="r-nom">{typo(r.challenge_name)}</span>
                <span class="r-qui">{t("team.solved_by", { user: r.solved_by ?? "—", time: heure(r.solved_at) })}</span>
              </li>
            {/each}
          </ol>
        {:else if equipe.solves.length}
          <p class="secondaire vide-quartier">{t("team.district_empty")}</p>
        {/if}
      {/each}
    </section>
    <section class="bloc" aria-labelledby="h-fils">
      <h2 class="titre-section" id="h-fils">{t("team.items")}</h2>
      {#if equipe.items.length}
        <ul class="fils">
          {#each equipe.items as objet (objet.id)}
            <li>
              <p class="fil-nom">{typo(objet.name)}</p>
              <FilDeSoie motif={motif(objet.description)} />
              {#if objet.description}
                {@const m = motif(objet.description)}
                <p class="meta">{typo(m ? objet.description.replace(/,?\s*motif\s*:\s*[●○]+\.?\s*$/, ".") : objet.description)}</p>
                {#if m}
                  <!-- Disques dessinés (pleins et vides de même taille, quelle que soit la police) ;
                       le texte ●○ reste pour les lecteurs d'écran et le copier-coller. -->
                  <p class="motif">
                    {typo(t("team.pattern"))}
                    <span class="noeuds" aria-hidden="true">
                      {#each [...m] as c, i (i)}
                        <svg class="noeud" viewBox="0 0 12 12" focusable="false"
                          ><circle cx="6" cy="6" r={c === "●" ? 5.5 : 4.75} class:plein={c === "●"} /></svg
                        >
                      {/each}
                    </span><span class="sr-only">{m}</span>
                  </p>
                {/if}
              {/if}
            </li>
          {/each}
        </ul>
      {:else}
        <p class="secondaire">{t("team.no_items")}</p>
        <p><a class="btn-ligne" href="/challenges">{t("team.go_board")}</a></p>
      {/if}
    </section>

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
          <p class="membres">{enPhrase.format(equipe.members.map((m) => m.username))}.</p>
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
  .manque {
    margin-top: var(--e3);
  }
  .vide-quartier {
    padding: var(--e2) 0 var(--e3);
    border-top: 1px solid var(--pierre);
  }
  .motif {
    font-size: var(--t-nom);
  }
  .noeuds {
    display: inline-flex;
    flex-wrap: wrap;
    gap: 0.3em;
    vertical-align: -0.08em;
  }
  .noeud {
    width: 0.8em;
    height: 0.8em;
  }
  .noeud circle {
    fill: none;
    stroke: currentColor;
    stroke-width: 1.5;
  }
  .noeud circle.plein {
    fill: currentColor;
    stroke: none;
  }
  .q-tete {
    display: flex;
    align-items: center;
    gap: var(--e4);
    margin-top: var(--e6);
    margin-bottom: var(--e3);
  }
  /* Une case fixe : chaque immeuble y tient par sa hauteur (la tour reste fine, les ateliers
     larges), et les noms de quartier partent tous du même bord. */
  .q-dessin {
    flex: none;
    display: flex;
    align-items: flex-end;
    justify-content: flex-start;
    width: 96px;
    height: 64px;
  }
  .q-dessin :global(.bati) {
    width: auto;
    height: 100%;
    max-width: 100%;
  }
  .resolus {
    border-top: 1px solid var(--pierre);
  }
  .resolus li {
    display: grid;
    row-gap: var(--e1);
    padding: var(--e3) 0;
    border-bottom: 1px solid var(--pierre);
  }
  .r-nom {
    font-size: var(--t-nom);
    overflow-wrap: anywhere;
  }
  .r-qui {
    font-size: var(--t-meta);
    color: var(--douce);
    overflow-wrap: anywhere;
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
  .membres {
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
