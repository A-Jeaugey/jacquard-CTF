<script lang="ts">
  import Reessayer from "../Reessayer.svelte";
  import { tick } from "svelte";

  import { api, ApiError, errorMessage } from "../../lib/api";
  import { equipe, refreshEquipe } from "../../lib/equipe.svelte";
  import { formatHeure, formatPoints, formatSize } from "../../lib/format";
  import { session } from "../../lib/session.svelte";
  import { t, tn } from "../../lib/strings";
  import { typo, typographie } from "../../lib/typo";
  import type { ChallengeDetail, ChallengeSummary, HintView, SubmitResult } from "../../lib/types";
  import { ordreEnPhrases, type Quartier } from "../../lib/ville";
  import Immeuble from "./Immeuble.svelte";
  import Marque from "./Marque.svelte";

  let {
    id,
    quartier,
    tous,
    onFermer,
    onResolu,
  }: {
    id: string;
    quartier: Quartier | null;
    tous: ChallengeSummary[];
    onFermer: () => void;
    onResolu: () => void;
  } = $props();

  // « refus » : le flag est refusé ; « erreur » : autre problème (réseau, serveur) ;
  // « session » : il faut se reconnecter ; « info » : simple information.
  type Retour = { sorte: "refus" | "erreur" | "session" | "info"; texte: string };
  interface Recompense {
    texte: string;
  }

  let defi = $state<ChallengeDetail | null>(null);
  let erreurChargement = $state<string | null>(null);
  let flag = $state("");
  let envoi = $state(false);
  let retour = $state<Retour | null>(null);
  let reussite = $state<{ recompenses: Recompense[]; messages: string[] } | null>(null);
  let confirmation = $state<string | null>(null);
  let erreurIndice = $state<string | null>(null);
  let copie = $state<string | null>(null);

  let titre = $state<HTMLHeadingElement>();
  let champ = $state<HTMLInputElement>();
  let defilement = $state<HTMLDivElement>();
  let formulaire = $state<HTMLFormElement>();
  let hauteurFlag = $state(0);

  const resume = $derived(tous.find((c) => c.id === id) ?? null);
  const heure = (iso: string): string => formatHeure(iso, session.event?.timezone);
  const phrase = $derived(resume && quartier ? ordreEnPhrases(resume, quartier, tous, heure) : null);
  const termine = $derived(session.event?.phase === "ended");
  const joueur = $derived(session.me?.user.role !== "admin");
  const formatFlag = $derived(session.event?.flag_format ?? null);
  const prefixe = $derived(formatFlag?.split("{")[0] ?? "");
  const resolution = $derived(equipe.data?.solves.find((s) => s.challenge_id === id) ?? null);
  const majuscule = (texte: string): string => texte.charAt(0).toUpperCase() + texte.slice(1);

  async function charger(): Promise<void> {
    defi = null;
    erreurChargement = null;
    retour = null;
    reussite = null;
    flag = "";
    try {
      defi = await api.get<ChallengeDetail>(`/api/challenges/${encodeURIComponent(id)}`);
    } catch (error) {
      erreurChargement = errorMessage(error);
    }
    await tick();
    titre?.focus({ preventScroll: true });
    defilement?.scrollTo(0, 0);
  }

  $effect(() => {
    void id;
    void charger();
  });

  // Le formulaire du flag est fixé en bas : le contenu garde une marge au moins égale à sa
  // hauteur, pour qu'aucun texte ni élément focalisé ne passe dessous.
  $effect(() => {
    if (!formulaire) {
      hauteurFlag = 0;
      return;
    }
    const observer = new ResizeObserver(() => (hauteurFlag = formulaire?.offsetHeight ?? 0));
    observer.observe(formulaire);
    return () => observer.disconnect();
  });

  function decrireRecompenses(resultat: Extract<SubmitResult, { status: "correct" }>): Recompense[] {
    const lignes: Recompense[] = [];
    if (resultat.first_blood === 1) lignes.push({ texte: t("challenge.first_blood") });
    else if (resultat.first_blood) lignes.push({ texte: t("challenge.first_blood_rank", { n: resultat.first_blood }) });
    for (const objet of resultat.items) lignes.push({ texte: t("challenge.item_obtained", { name: objet.name }) });
    const ouverts = resultat.unlocked.challenges.map((c) => c.name);
    if (ouverts.length > 2) {
      lignes.push({ texte: t("challenge.unlocked_challenges", { n: ouverts.length, names: ouverts.join(", ") }) });
    } else {
      for (const name of ouverts) lignes.push({ texte: t("challenge.unlocked_challenge", { name }) });
    }
    for (const s of resultat.unlocked.story) lignes.push({ texte: t("challenge.unlocked_story", { title: s.title }) });
    return lignes;
  }

  async function valider(event: SubmitEvent): Promise<void> {
    event.preventDefault();
    const valeur = flag.trim();
    if (envoi) return;
    if (!valeur) {
      retour = { sorte: "refus", texte: t("challenge.flag_empty") };
      champ?.focus();
      return;
    }
    envoi = true;
    retour = null;
    try {
      const resultat = await api.post<SubmitResult>(`/api/challenges/${encodeURIComponent(id)}/submit`, { flag: valeur });
      if (resultat.status === "incorrect") {
        const malForme = prefixe !== "" && !valeur.toLowerCase().startsWith(prefixe.toLowerCase());
        retour = {
          sorte: "refus",
          texte: malForme ? t("challenge.flag_format_wrong", { format: formatFlag ?? "" }) : t("challenge.incorrect"),
        };
        champ?.focus();
        return;
      }
      if (resultat.status === "correct") {
        reussite = { recompenses: decrireRecompenses(resultat), messages: resultat.notifications };
      } else {
        retour = { sorte: "info", texte: t("challenge.already_solved") };
      }
      flag = "";
      if (defi) defi.solved = true;
      onResolu();
      await refreshEquipe();
      await tick();
      titre?.focus();
    } catch (error) {
      const delai = error instanceof ApiError ? error.extra.retry_after : undefined;
      if (error instanceof ApiError && error.status === 401) retour = { sorte: "session", texte: "" };
      else if (delai) retour = { sorte: "refus", texte: t("challenge.rate_limited", { n: String(delai) }) };
      else retour = { sorte: "erreur", texte: errorMessage(error) };
      champ?.focus();
    } finally {
      envoi = false;
    }
  }

  async function demanderIndice(indice: HintView): Promise<void> {
    erreurIndice = null;
    if (indice.cost > 0 && confirmation !== indice.id) {
      confirmation = indice.id;
      await tick();
      document.getElementById(`confirmer-${indice.id}`)?.focus();
      return;
    }
    confirmation = null;
    try {
      const revele = await api.post<{ text_html: string }>(
        `/api/challenges/${encodeURIComponent(id)}/hints/${encodeURIComponent(indice.id)}/unlock`,
      );
      indice.unlocked = true;
      indice.text_html = revele.text_html;
      void refreshEquipe();
      await tick();
      document.getElementById(`texte-${indice.id}`)?.focus();
    } catch (error) {
      erreurIndice = errorMessage(error);
    }
  }

  async function annulerIndice(indice: HintView): Promise<void> {
    confirmation = null;
    await tick();
    document.getElementById(`indice-${indice.id}`)?.focus();
  }

  async function copier(texte: string): Promise<void> {
    try {
      await navigator.clipboard.writeText(texte);
      copie = t("challenge.copied");
    } catch {
      const zone = document.getElementById("adresse-defi");
      if (zone) {
        const plage = document.createRange();
        plage.selectNodeContents(zone);
        const selection = getSelection();
        selection?.removeAllRanges();
        selection?.addRange(plage);
      }
      copie = t("challenge.copy_blocked");
    }
  }

  let racine = $state<HTMLDivElement>();

  function focusables(): HTMLElement[] {
    if (!racine) return [];
    return Array.from(
      racine.querySelectorAll<HTMLElement>("a[href], button:not([disabled]), input:not([disabled]), [tabindex]:not([tabindex='-1'])"),
    ).filter((el) => el.offsetParent !== null);
  }

  // Écouté sur la fenêtre : Échap et Tab marchent même si le focus est sorti du panneau.
  function clavier(event: KeyboardEvent): void {
    if (event.key === "Escape") {
      event.preventDefault();
      // Échap ferme la couche la plus interne : la confirmation d'un indice d'abord.
      const indice = defi?.hints.find((h) => h.id === confirmation);
      if (indice) void annulerIndice(indice);
      else onFermer();
      return;
    }
    if (event.key !== "Tab") return;
    // Tab boucle dans le panneau (fenêtre modale).
    const liste = focusables();
    if (liste.length === 0) return;
    const premier = liste[0] as HTMLElement;
    const dernier = liste[liste.length - 1] as HTMLElement;
    const actif = document.activeElement;
    const dedans = racine?.contains(actif) ?? false;
    if (event.shiftKey && (actif === premier || !dedans || actif === titre)) {
      event.preventDefault();
      dernier.focus();
    } else if (!event.shiftKey && (actif === dernier || !dedans)) {
      event.preventDefault();
      premier.focus();
    }
  }
</script>

<svelte:window onkeydown={clavier} />

<div
  class="panneau"
  role="dialog"
  aria-modal="true"
  aria-labelledby="titre-defi"
  bind:this={racine}
  style:--hauteur-flag="{hauteurFlag}px"
>
  <div class="defilement" bind:this={defilement}>
    <div class="haut">
      <h2 class="titre" id="titre-defi" tabindex="-1" bind:this={titre}>{typo(resume?.name ?? defi?.name ?? "")}</h2>
      <button type="button" class="btn-texte" onclick={onFermer}>{t("challenge.close")}</button>
    </div>

    {#if quartier && resume}
      <div class="lieu">
        <figure class="elevation">
          <div class="dessin" style:aspect-ratio="{quartier.gabarit.w} / {quartier.gabarit.h + 4}">
            <Immeuble {quartier} avecFil cadre={id} />
          </div>
          <figcaption class="titre-bloc">{quartier.categorie.name}</figcaption>
        </figure>
        {#if phrase}<p class="ordre">{typo(phrase)}</p>{/if}
      </div>
    {/if}

    {#if erreurChargement}
      <p class="refus" role="alert"><b>{t("error.title")}</b> {erreurChargement}</p>
      <Reessayer action={charger} cible="titre-defi" />
    {:else if !defi}
      <p class="secondaire">{t("loading")}</p>
    {:else}
      <p class="faits">
        {defi.difficulty
          ? t("challenge.facts", { difficulty: majuscule(defi.difficulty), points: formatPoints(defi.value) })
          : t("challenge.facts_no_difficulty", { points: formatPoints(defi.value) })}
        {majuscule(tn("board.solves", defi.solves))}.
        {#if defi.authors.length}{t("challenge.by", { names: defi.authors.join(", ") })}{/if}
      </p>

      <!-- HTML produit et assaini par le serveur (jacquard/markdown.py). -->
      <div class="prose enonce" use:typographie>{@html defi.description_html}</div>
      {#if defi.tags.length}
        <p class="meta">{t("challenge.tags", { tags: defi.tags.map((tag) => tag.replace(/-/g, " ")).join(", ") })}</p>
      {/if}

      {#if defi.connection}
        <section class="bloc" aria-labelledby="h-adresse">
          <h3 class="etiquette" id="h-adresse">{t("challenge.connection")}</h3>
          <div class="adresse">
            <code id="adresse-defi">{defi.connection}</code>
            <button type="button" class="btn-ligne" onclick={() => copier(defi?.connection ?? "")}>{t("challenge.copy")}</button>
          </div>
          <p class="meta" role="status">{copie ?? ""}</p>
        </section>
      {/if}

      {#if defi.files.length}
        <section class="bloc" aria-labelledby="h-fichiers">
          <h3 class="etiquette" id="h-fichiers">{t("challenge.files")}</h3>
          <ul class="liste">
            {#each defi.files as fichier (fichier.id)}
              <li>
                <a href={`/api/files/${fichier.id}`} download={fichier.name}>{fichier.name}</a>
                <span class="meta tnum">{formatSize(fichier.size)}</span>
              </li>
            {/each}
          </ul>
        </section>
      {/if}

      {#if defi.hints.length}
        <section class="bloc" aria-labelledby="h-indices">
          <h3 class="etiquette" id="h-indices">{t("challenge.hints")}</h3>
          <ol class="liste indices">
            {#each defi.hints as indice, index (indice.id)}
              <li>
                <div class="indice-tete">
                  <span class="indice-nom">{t("challenge.hint", { n: index + 1 })}</span>
                  <span class="meta">
                    {indice.cost > 0 ? t("challenge.hint.cost", { points: formatPoints(indice.cost) }) : t("challenge.hint.free")}
                  </span>
                  {#if indice.text_html !== null}
                    <span class="meta">{t("challenge.hint.unlocked")}</span>
                  {:else if !indice.available}
                    <span class="meta">{t("challenge.hint.unavailable")}</span>
                  {:else if joueur && !termine && confirmation !== indice.id}
                    <button type="button" class="btn-ligne" id="indice-{indice.id}" onclick={() => demanderIndice(indice)}>
                      {indice.cost > 0
                        ? t("challenge.hint.buy", { points: formatPoints(indice.cost) })
                        : t("challenge.hint.reveal")}
                    </button>
                  {/if}
                </div>
                {#if confirmation === indice.id}
                  <div class="confirmation">
                    <p>{t("challenge.hint.confirm", { points: formatPoints(indice.cost) })}</p>
                    <p class="choix">
                      <button type="button" class="btn-ligne" id="confirmer-{indice.id}" onclick={() => demanderIndice(indice)}>
                        {t("challenge.hint.confirm_action")}
                      </button>
                      <button type="button" class="btn-texte" onclick={() => annulerIndice(indice)}>{t("action.cancel")}</button>
                    </p>
                  </div>
                {/if}
                {#if indice.text_html !== null}
                  <!-- Indice assaini côté serveur. -->
                  <div class="prose texte-indice" id="texte-{indice.id}" tabindex="-1" use:typographie>
                    {@html indice.text_html}
                  </div>
                {/if}
              </li>
            {/each}
          </ol>
          {#if erreurIndice}<p class="refus" role="alert"><b>{t("error.title")}</b> {erreurIndice}</p>{/if}
        </section>
      {/if}

      {#if reussite}
        <section class="reussite" aria-labelledby="h-reussite">
          <h3 class="titre-bloc" id="h-reussite">{t("challenge.correct_title")}</h3>
          <p>{t("challenge.correct")}</p>
          {#if reussite.recompenses.length}
            <ul class="liste">
              {#each reussite.recompenses as ligne (ligne.texte)}<li>{ligne.texte}</li>{/each}
            </ul>
          {/if}
          {#each reussite.messages as html, index (index)}
            <!-- Message de l'auteur du défi, assaini côté serveur. -->
            <div class="prose message" use:typographie>{@html html}</div>
          {/each}
        </section>
      {:else if defi.solved}
        <p class="resolu">
          <Marque etat="resolu" />
          <span>
            {#if resolution}
              <b>{t("challenge.solved_by_member", { user: resolution.solved_by ?? "—", time: heure(resolution.solved_at) })}</b>
              {t("challenge.solved_points", { points: formatPoints(resolution.points) })}
            {:else}
              <b>{t("challenge.solved_banner")}</b>
            {/if}
          </span>
        </p>
      {:else if termine}
        <p class="secondaire bloc">{t("challenge.ended")}</p>
      {/if}
      {#if retour?.sorte === "info"}<p class="secondaire bloc" role="status">{retour.texte}</p>{/if}
    {/if}
  </div>

  {#if defi && !defi.solved && !termine && joueur}
    <form class="flag" bind:this={formulaire} onsubmit={valider} novalidate>
      <label class="etiquette" for="flag">{t("challenge.flag")}</label>
      <div class="ligne-flag">
        <input
          id="flag"
          class="saisie"
          bind:this={champ}
          bind:value={flag}
          oninput={() => {
            if (retour?.sorte === "refus") retour = null;
          }}
          autocomplete="off"
          autocapitalize="off"
          spellcheck="false"
          maxlength="512"
          placeholder={formatFlag ?? ""}
          aria-invalid={retour?.sorte === "refus" ? "true" : undefined}
          aria-describedby="flag-aide"
        />
        <button type="submit" class="btn-principal" disabled={envoi}>
          {envoi ? t("challenge.submitting") : t("challenge.submit")}
        </button>
      </div>
      <p id="flag-aide" aria-live="polite" class={retour && retour.sorte !== "info" ? "refus" : "aide"}>
        {#if retour?.sorte === "refus"}
          <b>{t("challenge.refused")}</b> {retour.texte}
        {:else if retour?.sorte === "erreur"}
          <b>{t("error.title")}</b> {retour.texte}
        {:else if retour?.sorte === "session"}
          <span class="session">
            <b>{t("challenge.session_expired")}</b>
            <a class="btn-ligne" href="/login">{t("challenge.login_again")}</a>
          </span>
        {:else if formatFlag}
          {t("challenge.format_hint", { format: formatFlag })}
        {/if}
      </p>
    </form>
  {/if}
</div>

<style>
  .panneau {
    display: flex;
    flex-direction: column;
    min-height: 0;
    background: var(--pierre-sombre);
  }
  .defilement {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    overscroll-behavior: contain;
    padding: var(--e5) var(--gouttiere) var(--e7);
    scroll-padding-bottom: calc(var(--hauteur-flag) + var(--e4));
  }
  .haut {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: var(--e4);
  }
  .titre {
    min-width: 0;
    font-family: var(--display);
    font-weight: 400;
    font-size: 48px;
    line-height: 1;
    padding-top: var(--e1);
    overflow-wrap: anywhere;
  }
  .haut .btn-texte {
    flex: none;
  }
  .lieu {
    display: grid;
    grid-template-columns: auto minmax(0, 1fr);
    align-items: end;
    gap: var(--e5);
    margin-top: var(--e5);
  }
  .elevation {
    display: flex;
    flex-direction: column;
    align-items: center;
    min-width: 120px;
  }
  .dessin {
    height: 136px;
    max-width: 200px;
  }
  .dessin :global(.bati) {
    height: 100%;
    width: auto;
  }
  figcaption {
    margin-top: var(--e1);
    text-align: center;
  }
  .ordre {
    max-width: 40ch;
    padding-bottom: var(--e1);
  }
  .faits {
    overflow-wrap: anywhere;
    margin-top: var(--e4);
    padding: var(--e3) 0;
    border-top: 1px solid var(--pierre);
    border-bottom: 1px solid var(--pierre);
  }
  .enonce {
    margin-top: var(--e5);
    font-size: var(--t-nom);
  }
  .enonce + .meta {
    margin-top: var(--e4);
  }
  .bloc {
    margin-top: var(--e6);
  }
  .bloc .etiquette {
    display: block;
    margin-bottom: var(--e2);
  }
  .adresse {
    display: flex;
    gap: var(--e2);
    align-items: stretch;
  }
  .adresse code {
    flex: 1;
    display: flex;
    align-items: center;
    min-height: 44px;
    padding: var(--e2) var(--e3);
    background: var(--eau);
    border-radius: 2px;
    font-family: var(--texte);
    overflow-wrap: anywhere;
  }
  .liste {
    border-top: 1px solid var(--pierre);
  }
  .liste a {
    display: inline-flex;
    align-items: center;
    min-height: 44px;
    overflow-wrap: anywhere;
  }
  .liste > li {
    padding: var(--e2) 0;
    border-bottom: 1px solid var(--pierre);
    min-height: 56px;
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: var(--e2) var(--e4);
  }
  .indices > li {
    display: block;
  }
  .indice-tete {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: var(--e2) var(--e4);
    min-height: 44px;
  }
  .indice-tete .btn-ligne {
    margin-left: auto;
  }
  .indice-nom {
    font-weight: 700;
  }
  .confirmation {
    margin-top: var(--e2);
  }
  .choix {
    display: flex;
    flex-wrap: wrap;
    gap: var(--e3);
    align-items: center;
    margin-top: var(--e2);
  }
  .texte-indice {
    margin-top: var(--e2);
  }
  .reussite {
    margin-top: var(--e6);
    padding-top: var(--e5);
    border-top: 1px solid var(--lumignon);
  }
  .reussite > * + * {
    margin-top: var(--e3);
  }
  .resolu {
    display: flex;
    gap: var(--e3);
    align-items: flex-start;
    margin-top: var(--e6);
    padding-top: var(--e5);
    border-top: 1px solid var(--pierre);
  }
  .resolu b {
    color: var(--lumignon);
  }
  .resolu :global(.marque) {
    margin-top: var(--e1);
  }
  .flag {
    flex: none;
    padding: var(--e4) var(--gouttiere) var(--e5);
    background: var(--pierre-sombre);
    border-top: 1px solid var(--pierre);
  }
  .flag .etiquette {
    display: block;
    margin-bottom: var(--e2);
  }
  .ligne-flag {
    display: flex;
    gap: var(--e2);
  }
  .ligne-flag .saisie {
    flex: 1;
    min-width: 0;
  }
  #flag-aide {
    margin-top: var(--e2);
    min-height: 1.5em;
  }
  .session {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: var(--e2) var(--e3);
  }

  @media (max-width: 640px) {
    .titre {
      font-size: 36px;
    }
    .flag {
      padding: var(--e3) var(--gouttiere);
    }
    .flag .etiquette {
      margin-bottom: var(--e1);
    }
    #flag-aide {
      margin-top: var(--e1);
    }
    .lieu {
      gap: var(--e4);
    }
    .elevation {
      min-width: 96px;
    }
    .dessin {
      height: 104px;
      max-width: 144px;
    }
    .enonce {
      font-size: var(--t-texte);
    }
    .indice-tete .btn-ligne {
      margin-left: 0;
    }
  }
</style>
