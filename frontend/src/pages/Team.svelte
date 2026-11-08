<script lang="ts">
  import { tick } from "svelte";

  import PageAcces from "../components/PageAcces.svelte";
  import Reessayer from "../components/Reessayer.svelte";
  import FilDeSoie from "../components/ville/FilDeSoie.svelte";
  import Immeuble from "../components/ville/Immeuble.svelte";
  import { api, ApiError, errorMessage } from "../lib/api";
  import { copierTexte } from "../lib/copie";
  import { equipe as suiviEquipe, refreshEquipe } from "../lib/equipe.svelte";
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
    if (await copierTexte(texte)) {
      copie = t("team.invite_copied");
    } else {
      // Aucune copie possible : le code est sélectionné, prêt pour Ctrl+C.
      const zone = document.getElementById("code-invitation");
      if (zone) getSelection()?.selectAllChildren(zone);
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
  // La rue : les immeubles des quartiers, dans l'ordre de l'événement.
  const rue = $derived(ville ?? []);
  // Le journal : les défis résolus, du plus récent au plus ancien.
  const journal = $derived(equipe ? [...equipe.solves].sort((a, b) => b.solved_at.localeCompare(a.solved_at)) : []);
  const JOURNAL_COURT = 6;
  let journalComplet = $state(false);
  const journalVisible = $derived(journalComplet ? journal : journal.slice(0, JOURNAL_COURT));
  const nomQuartier = (id: string): string => session.event?.categories.find((c) => c.id === id)?.name ?? "";
  const totalDefis = $derived(defis.length);
  const nombreEquipes = $derived(suiviEquipe.nombreEquipes);
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
    <header class="entete-equipe">
      <h1 class="titre-page" id="titre-equipe" tabindex="-1">{typo(equipe.name)}</h1>
      <dl class="chiffres">
        <div>
          <dt>{t("team.rank")}</dt>
          <dd>
            {#if equipe.rank}{equipe.rank}<span class="sup">e</span>{#if nombreEquipes}<span class="sur">{t("team.out_of", { n: nombreEquipes })}</span>{/if}{:else}—{/if}
          </dd>
        </div>
        <div>
          <dt>{t("team.score")}</dt>
          <dd class="score tnum">{formatPoints(equipe.score)}</dd>
        </div>
        <div>
          <dt>{t("team.solves")}</dt>
          <dd class="tnum">{equipe.solves.length}{#if totalDefis}<span class="sur">{t("team.out_of", { n: totalDefis })}</span>{/if}</dd>
        </div>
        <div>
          <dt>{t("team.items")}</dt>
          <dd class="tnum">{equipe.items.length}</dd>
        </div>
      </dl>
      {#if equipe.penalty > 0}<p class="penalite">{t("team.penalty", { points: formatPoints(equipe.penalty) })}</p>{/if}
    </header>

    <section class="bloc ville-equipe" aria-labelledby="h-resolus">
      <h2 class="titre-section" id="h-resolus" tabindex="-1">{t("team.districts")}</h2>
      {#if erreurDefis}
        <div class="manque" role="alert">
          <p class="refus"><b>{t("error.title")}</b> {t("team.buildings_missing")} {erreurDefis}</p>
          <p><Reessayer action={chargerDefis} cible="h-resolus" /></p>
        </div>
      {/if}
      {#if rue.length}
        <!-- La rue de l'équipe : chaque immeuble à la même échelle, ses fenêtres allumées par les
             défis résolus ; un clic mène au quartier sur le plan. -->
        <ul class="rue" style:grid-template-columns={rue.map((q) => `${q.gabarit.w}fr`).join(" ")}>
          {#each rue as q (q.categorie.id)}
            <li class="maison">
              <a href="/challenges?quartier={encodeURIComponent(q.categorie.id)}" aria-label={t("team.district_link", { name: q.categorie.name, n: q.resolus, total: q.defis.length })}>
                <span class="facade" style:--w={q.gabarit.w} style:--h={q.gabarit.h + 4}><Immeuble quartier={q} /></span>
                <span class="m-nom">{q.categorie.name}</span>
                <span class="m-avance tnum" class:complet={q.resolus === q.defis.length}>{t("board.district_progress", { n: q.resolus, total: q.defis.length })}</span>
              </a>
            </li>
          {/each}
        </ul>
      {/if}
      {#if !equipe.solves.length}
        <div class="vide">
          <p>{t("team.no_solves_cta")}</p>
          <a class="btn-principal" href="/challenges">{t("team.go_board")}</a>
        </div>
      {/if}
    </section>

    <div class="colonnes">
      <section class="bloc journal" aria-labelledby="h-journal">
        <h2 class="titre-section" id="h-journal">{t("team.log")}</h2>
        {#if journal.length}
          <ol class="resolus" id="journal-liste">
            {#each journalVisible as r (r.challenge_id)}
              <li>
                <span class="r-nom">{typo(r.challenge_name)}</span>
                <span class="r-pts tnum">+{formatPoints(r.points)}</span>
                <span class="r-qui">{[nomQuartier(r.category), t("team.solved_by", { user: r.solved_by ?? "—", time: heure(r.solved_at) })].filter(Boolean).join(" · ")}</span>
              </li>
            {/each}
          </ol>
          {#if journal.length > JOURNAL_COURT}
            <p class="deplier">
              <button type="button" class="btn-texte" aria-expanded={journalComplet} aria-controls="journal-liste" onclick={() => (journalComplet = !journalComplet)}>
                {journalComplet ? t("team.log_less") : t("team.log_all", { n: journal.length })}
              </button>
            </p>
          {/if}
        {:else}
          <p class="secondaire">{t("team.log_empty")}</p>
        {/if}
      </section>

      <aside class="cote" aria-label={t("team.side_label")}>
        {#if equipe.invite_code}
          <section class="bloc" aria-labelledby="h-invitation">
            <h2 class="titre-bloc" id="h-invitation">{t("team.invite")}</h2>
            <p class="aide">{t("team.invite_hint")}</p>
            <div class="code">
              <span class="code-valeur tnum" id="code-invitation">{equipe.invite_code}</span>
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
            {#each equipe.members as m (m.id)}<li>{m.username}</li>{/each}
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
      </aside>
    </div>

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
      {/if}
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
  .equipe {
    max-width: none;
  }
  .titre-page {
    overflow-wrap: anywhere;
  }
  /* En-tête : le nom, puis les chiffres de l'équipe sur une ligne, séparés par des filets. */
  .chiffres {
    display: flex;
    flex-wrap: wrap;
    margin-top: var(--e5);
    border-top: 1px solid var(--pierre);
    border-bottom: 1px solid var(--pierre);
  }
  .chiffres > div {
    display: flex;
    flex-direction: column-reverse;
    justify-content: flex-end;
    gap: var(--e1);
    padding: var(--e4) var(--e6) var(--e4) 0;
    min-width: 9rem;
  }
  .chiffres > div + div {
    padding-left: var(--e6);
    border-left: 1px solid var(--pierre);
  }
  .chiffres dt {
    font-size: var(--t-meta);
    color: var(--douce);
  }
  .chiffres dd {
    font-family: var(--display);
    font-size: 40px;
    line-height: 1;
  }
  .chiffres .sur {
    margin-left: var(--e2);
    font-family: var(--texte);
    font-size: var(--t-texte);
    color: var(--douce);
  }
  .chiffres .sup {
    font-family: var(--texte);
    font-size: 16px;
    vertical-align: 1.1em;
  }
  .score {
    color: var(--lumignon);
  }
  .penalite {
    margin-top: var(--e2);
    font-size: var(--t-meta);
    color: var(--douce);
  }
  .bloc {
    margin-top: var(--e7);
  }
  .bloc > h2 {
    margin-bottom: var(--e4);
  }

  /* La rue : les huit immeubles à la même échelle, posés sur un même quai. */
  .rue {
    display: grid;
    column-gap: var(--e6);
    grid-template-rows: auto auto auto;
    max-width: 1280px;
    padding-bottom: var(--e2);
  }
  .maison {
    display: grid;
    grid-row: span 3;
    grid-template-rows: subgrid;
    min-width: 0;
  }
  .maison a {
    display: grid;
    grid-row: span 3;
    grid-template-rows: subgrid;
    row-gap: var(--e1);
    color: inherit;
    text-decoration: none;
  }
  .facade {
    display: block;
    align-self: end;
    aspect-ratio: var(--w) / var(--h);
    border-bottom: 2px solid var(--lumen);
    transition: transform 200ms cubic-bezier(0.2, 0.7, 0.2, 1);
    transform-origin: 50% 100%;
  }
  .facade :global(.bati) {
    display: block;
    width: 100%;
    height: 100%;
  }
  .m-nom {
    margin-top: var(--e2);
    font-family: var(--display);
    font-size: 22px;
    line-height: 1;
    overflow-wrap: anywhere;
  }
  .m-avance {
    font-size: var(--t-meta);
    color: var(--douce);
  }
  .m-avance.complet {
    color: var(--lumignon);
  }
  @media (hover: hover) {
    .maison a:hover .facade {
      transform: translateY(-4px);
    }
    .maison a:hover .m-nom {
      text-decoration: underline;
      text-decoration-thickness: 1px;
      text-underline-offset: 4px;
    }
  }
  .maison a:focus-visible {
    outline-offset: 4px;
  }
  .vide {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: var(--e3) var(--e5);
    margin-top: var(--e5);
  }
  .vide p {
    max-width: 52ch;
  }
  .manque {
    margin-bottom: var(--e4);
  }

  /* Le journal à gauche, l'invitation et les membres à droite. */
  .colonnes {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(280px, 360px);
    column-gap: var(--e8);
    align-items: start;
  }
  .resolus {
    border-top: 1px solid var(--pierre);
  }
  .deplier {
    margin-top: var(--e2);
  }
  .resolus li {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    column-gap: var(--e4);
    row-gap: var(--e1);
    padding: var(--e3) 0;
    border-bottom: 1px solid var(--pierre);
  }
  .r-nom {
    font-size: var(--t-nom);
    overflow-wrap: anywhere;
  }
  .r-pts {
    color: var(--lumignon);
    font-weight: 700;
  }
  .r-qui {
    grid-column: 1 / -1;
    font-size: var(--t-meta);
    color: var(--douce);
    overflow-wrap: anywhere;
  }
  .cote .bloc:first-child {
    margin-top: var(--e7);
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
    border-top: 1px solid var(--pierre);
  }
  .membres li {
    padding: var(--e2) 0;
    border-bottom: 1px solid var(--pierre);
    overflow-wrap: anywhere;
  }
  .depart {
    margin-top: var(--e4);
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

  /* Une colonne : l'invitation et les membres passent avant le journal. */
  @media (max-width: 900px) {
    .colonnes {
      grid-template-columns: minmax(0, 1fr);
    }
    .cote {
      order: -1;
    }
  }
  /* Petit écran : la rue passe sur deux rangées de quatre, toujours à la même échelle. */
  @media (max-width: 760px) {
    .rue {
      grid-template-columns: repeat(4, minmax(0, 1fr)) !important;
      grid-template-rows: none;
      grid-auto-rows: auto auto auto;
      column-gap: var(--e3);
      row-gap: var(--e5);
    }
    .facade {
      width: calc(var(--w) * 0.5px);
      max-width: 100%;
      justify-self: start;
    }
    .m-nom {
      font-size: 18px;
    }
  }
  @media (max-width: 640px) {
    .chiffres > div {
      min-width: 0;
      flex: 1 1 40%;
      padding: var(--e3) var(--e3) var(--e3) 0;
    }
    .chiffres > div + div {
      padding-left: var(--e3);
    }
    .chiffres > div:nth-child(3) {
      border-left: 0;
      padding-left: 0;
      border-top: 1px solid var(--pierre);
    }
    .chiffres > div:nth-child(4) {
      border-top: 1px solid var(--pierre);
    }
    .chiffres dd {
      font-size: 32px;
    }
  }
</style>
