<script lang="ts">
  import { tick, untrack } from "svelte";

  import Marque from "../components/ville/Marque.svelte";
  import Panneau from "../components/ville/Panneau.svelte";
  import Ville from "../components/ville/Ville.svelte";
  import { api, errorMessage } from "../lib/api";
  import { equipe } from "../lib/equipe.svelte";
  import { formatHeure, formatPoints, poll } from "../lib/format";
  import { live } from "../lib/live.svelte";
  import { navigate, param, route } from "../lib/router.svelte";
  import { session } from "../lib/session.svelte";
  import { t, tn } from "../lib/strings";
  import { typo } from "../lib/typo";
  import type { ChallengeList, ChallengeSummary, FeedItem } from "../lib/types";
  import { avant, construireVille, etatDe, ordonner, type Etat, type Quartier } from "../lib/ville";

  let liste = $state<ChallengeList | null>(null);
  let erreur = $state<string | null>(null);
  let flux = $state<FeedItem[]>([]);
  let choisi = $state<string | null>(null);
  let annonce = $state("");
  let chroniqueFermee = $state<string | null>(null);
  let declencheur: HTMLElement | null = null;
  let ouvertParNous = false;

  async function charger(): Promise<void> {
    try {
      const [defis, evenements] = await Promise.all([
        api.get<ChallengeList>("/api/challenges"),
        api.get<FeedItem[]>("/api/feed").catch(() => [] as FeedItem[]),
      ]);
      liste = defis;
      flux = evenements;
      erreur = null;
    } catch (e) {
      erreur = errorMessage(e);
    }
  }

  $effect(() => {
    if (!session.me) {
      navigate("/login", true);
      return;
    }
    return poll(charger, 60_000);
  });

  // Rechargement immédiat quand une résolution ou un déblocage arrive en temps réel.
  $effect(() => {
    void live.ticks.solve;
    void live.ticks.unlock;
    void live.ticks.team;
    if (untrack(() => liste)) void charger();
  });

  // Sur grand écran, la page devient un cadre d'application : la carte reste visible.
  $effect(() => {
    document.body.classList.add("cadre-plan");
    return () => document.body.classList.remove("cadre-plan");
  });

  const defis = $derived(liste?.challenges ?? []);
  const parId = $derived(new Map(defis.map((c) => [c.id, c])));
  const categories = $derived(session.event?.categories ?? []);
  const difficultes = $derived(session.event?.difficulties ?? []);
  const ville = $derived(construireVille(categories, defis, difficultes));
  // Sans plan (trop de catégories), la liste reste groupée par catégorie, dans l'ordre de déblocage.
  const sections = $derived.by((): { id: string; nom: string; description: string | null; defis: ChallengeSummary[] }[] => {
    if (ville) return ville.map((q) => ({ id: q.categorie.id, nom: q.categorie.name, description: q.categorie.description, defis: q.defis }));
    const ordre = ordonner(defis, difficultes);
    return categories
      .map((c) => ({ id: c.id, nom: c.name, description: c.description, defis: ordre.filter((d) => d.category === c.id) }))
      .filter((s) => s.defis.length > 0);
  });
  const visibles = $derived(choisi ? sections.filter((s) => s.id === choisi) : sections);
  const comptes = $derived.by(() => {
    const total: Record<Etat, number> = { resolu: 0, disponible: 0, verrouille: 0 };
    for (const d of defis) total[etatDe(d)]++;
    return total;
  });
  const allumage = $derived(
    [...(equipe.data?.solves ?? [])].sort((a, b) => a.solved_at.localeCompare(b.solved_at)).map((s) => s.challenge_id),
  );
  const resolutions = $derived(new Map((equipe.data?.solves ?? []).map((s) => [s.challenge_id, s])));
  const heure = (iso: string): string => formatHeure(iso, session.event?.timezone);

  const ouvert = $derived(route.path === "/challenges" ? param("defi") : null);
  const defiOuvert = $derived(ouvert ? (parId.get(ouvert) ?? null) : null);
  const quartierOuvert = $derived<Quartier | null>(
    defiOuvert && ville ? (ville.find((q) => q.categorie.id === defiOuvert.category) ?? null) : null,
  );

  // Un défi verrouillé ou inconnu ne s'ouvre pas : on revient au plan.
  $effect(() => {
    if (ouvert && liste && (!defiOuvert || defiOuvert.locked)) navigate("/challenges", true);
  });

  // Panneau ouvert : le reste de la page devient inerte (fenêtre modale à toutes les largeurs).
  $effect(() => {
    const actif = Boolean(defiOuvert && !defiOuvert.locked);
    const zones = document.querySelectorAll<HTMLElement>(".barre, .plan > .tete, .plan > .ville-zone, .plan > .volet");
    zones.forEach((zone) => (zone.inert = actif));
    document.body.classList.toggle("panneau-ouvert", actif);
    return () => {
      zones.forEach((zone) => (zone.inert = false));
      document.body.classList.remove("panneau-ouvert");
    };
  });

  // À la fermeture (bouton, Échap ou retour du navigateur), le focus revient au déclencheur,
  // sinon au quartier du défi sur la carte.
  let precedent: string | null = null;
  $effect(() => {
    const courant = ouvert;
    const ancien = untrack(() => precedent);
    precedent = courant;
    if (ancien && !courant) {
      const categorie = parId.get(ancien)?.category;
      void tick().then(() => {
        if (declencheur?.isConnected) declencheur.focus();
        else boutonQuartier(categorie)?.focus();
        declencheur = null;
        ouvertParNous = false;
      });
    }
  });

  function boutonQuartier(categorie: string | undefined): HTMLElement | null {
    if (!categorie) return null;
    return document.querySelector<HTMLElement>(`.carte .quartier[data-categorie="${CSS.escape(categorie)}"]`);
  }

  const cadreBureau = (): boolean => matchMedia("(min-width: 1100px) and (min-height: 700px)").matches;

  async function choisir(categorie: string): Promise<void> {
    choisi = choisi === categorie ? null : categorie;
    const section = sections.find((s) => s.id === categorie);
    annonce = choisi && section ? t("board.district_announce", { name: section.nom, n: section.defis.length }) : "";
    await tick();
    if (choisi) {
      // Sur mobile, la liste est sous la carte : on y va, sinon le choix ne se voit pas.
      if (!cadreBureau()) {
        const calme = matchMedia("(prefers-reduced-motion: reduce)").matches;
        document.getElementById(`q-${choisi}`)?.scrollIntoView({ behavior: calme ? "auto" : "smooth", block: "start" });
      } else {
        document.querySelector(".volet")?.scrollTo(0, 0);
      }
    }
  }

  async function revoirTout(): Promise<void> {
    const ancien = choisi;
    choisi = null;
    annonce = "";
    await tick();
    boutonQuartier(ancien ?? undefined)?.focus();
  }

  function ouvrir(event: MouseEvent): void {
    declencheur = event.currentTarget as HTMLElement;
    ouvertParNous = true;
  }

  function fermer(): void {
    if (ouvertParNous) history.back();
    else navigate("/challenges", true);
  }

  // La dernière chronique (premier sang ou annonce), refermable.
  const chronique = $derived(flux[0] ?? null);
  const cleChronique = $derived(chronique ? `${chronique.kind}-${chronique.at}` : null);
  const quartierChronique = $derived.by(() => {
    if (chronique?.kind !== "first_blood") return null;
    const defi = defis.find((d) => d.name === chronique.challenge);
    return defi ? (sections.find((s) => s.id === defi.category) ?? null) : null;
  });

  function etatLigne(d: ChallengeSummary): { mot: string; suite: string } {
    const etat = etatDe(d);
    if (etat === "resolu") {
      const r = resolutions.get(d.id);
      return { mot: t("board.row.solved"), suite: r ? ` ${t("board.row.solved_by", { user: r.solved_by ?? "—", time: heure(r.solved_at) })}.` : "." };
    }
    if (etat === "verrouille") return { mot: t("board.row.locked"), suite: d.locked_message ? ` ${typo(d.locked_message)}` : "" };
    const parties: string[] = [];
    if (d.opens_at) parties.push(` ${t("board.row.since", { time: heure(d.opens_at) })}`);
    const a = avant(d, parId);
    if (a) parties.push(`, ${t("board.row.after", { name: a.name })}`);
    return { mot: t("board.row.available"), suite: `${parties.join("")}.` };
  }

  const besoinEquipe = $derived(session.me !== null && !session.me.team && session.me.user.role !== "admin");
</script>

{#snippet corps(d: ChallengeSummary, etat: Etat, ligne: { mot: string; suite: string })}
  <Marque {etat} />
  <span class="d-nom">{typo(d.name)}</span>
  <span class="d-meta">
    {#if d.difficulty}<span class="d-diff">{d.difficulty}</span><span class="d-sep">, </span>{/if}
    <span class="d-res tnum">{tn("board.solves", d.solves)}</span>
  </span>
  <span class="d-pts tnum">{formatPoints(d.value)}</span>
  <span class="d-etat"><span class="mot">{ligne.mot}</span>{typo(ligne.suite)}</span>
{/snippet}

<div class="plan">
  <div class="tete">
    <h1 class="titre-page">{t("board.title")}</h1>
    <p class="indice">
      {#if choisi}
        {t("board.district_selected", { name: sections.find((s) => s.id === choisi)?.nom ?? "" })}
        <button type="button" class="btn-texte" onclick={revoirTout}>{t("board.show_all")}</button>
      {:else if ville}
        {t("board.zone_hint")} {t("board.windows_hint")}
      {/if}
    </p>
    <p class="sr-only" aria-live="polite">{annonce}</p>
  </div>

  {#if erreur}
    <div class="volet etat">
      <p class="refus" role="alert"><b>{t("board.error")}</b> {erreur}</p>
      <button type="button" class="btn-ligne" onclick={charger}>{t("action.retry")}</button>
    </div>
  {:else if besoinEquipe}
    <div class="volet etat">
      <p>{t("board.need_team")}</p>
      <a class="btn-principal" href="/team">{t("home.cta.team")}</a>
    </div>
  {:else if !liste}
    <div class="volet etat"><p class="secondaire">{t("loading")}</p></div>
  {:else if liste.phase === "not_started" && defis.length === 0}
    <div class="volet etat"><p>{t("board.not_started")}</p></div>
  {:else if defis.length === 0}
    <div class="volet etat"><p>{t("board.empty")}</p></div>
  {:else}
    {#if ville}
      <div class="ville-zone">
        <div class="carte-cadre">
          <Ville quartiers={ville} {choisi} ouvert={defiOuvert ? ouvert : null} {allumage} onChoisir={choisir} />
        </div>
        <ul class="legende" aria-label={t("board.legend.label")}>
          <li><Marque etat="resolu" /><span><b class="tnum">{comptes.resolu}</b> {tn("board.legend.solved", comptes.resolu)}</span></li>
          <li><Marque etat="disponible" /><span><b class="tnum">{comptes.disponible}</b> {tn("board.legend.available", comptes.disponible)}</span></li>
          <li><Marque etat="verrouille" /><span><b class="tnum">{comptes.verrouille}</b> {tn("board.legend.locked", comptes.verrouille)}</span></li>
        </ul>
        {#if chronique && cleChronique !== chroniqueFermee}
          <div class="chronique">
            {#if chronique.kind === "first_blood"}
              <p class="chronique-titre">{t("live.first_blood_title")}</p>
              <p class="chronique-texte">
                {t("live.first_blood_text", { team: chronique.team, challenge: chronique.challenge, time: heure(chronique.at) })}
              </p>
            {:else}
              <p class="chronique-titre">{typo(chronique.title)}</p>
              <p class="chronique-texte"><a href="/">{t("home.announcements")}</a>, {heure(chronique.at)}</p>
            {/if}
            <p class="chronique-actions">
              {#if quartierChronique}
                <button type="button" class="btn-ligne" onclick={() => quartierChronique && choisi !== quartierChronique.id && choisir(quartierChronique.id)}>
                  {t("live.see_district", { name: quartierChronique.nom })}
                </button>
              {/if}
              <button type="button" class="btn-texte" onclick={() => (chroniqueFermee = cleChronique)}>{t("live.dismiss")}</button>
            </p>
          </div>
        {/if}
      </div>
    {/if}

    <div class="volet" aria-label={t("board.list_label")} role="region">
      {#each visibles as section (section.id)}
        {@const resolus = section.defis.filter((d) => d.solved).length}
        <section class="quartier-liste" id="q-{section.id}" aria-labelledby="h-{section.id}">
          <div class="q-tete">
            <h2 class="titre-section" id="h-{section.id}">{section.nom}</h2>
            <p class="q-compte tnum">{tn("board.count", resolus, { total: section.defis.length })}</p>
          </div>
          {#if section.description}<p class="q-desc">{typo(section.description)}</p>{/if}
          <ol class="etages">
            {#each section.defis as d (d.id)}
              {@const etat = etatDe(d)}
              {@const ligne = etatLigne(d)}
              <li class="etage" data-etat={etat}>
                {#if etat === "verrouille"}
                  <div class="defi">{@render corps(d, etat, ligne)}</div>
                {:else}
                  <a class="defi" href="/challenges?defi={encodeURIComponent(d.id)}" onclick={ouvrir}>{@render corps(d, etat, ligne)}</a>
                {/if}
              </li>
            {/each}
          </ol>
        </section>
      {:else}
        <p>{t("board.filtered_empty")}</p>
      {/each}
      <p class="credits">{t("credits.fonts")}</p>
    </div>
  {/if}

  {#if defiOuvert && !defiOuvert.locked && ouvert}
    <div class="panneau-zone">
      <Panneau id={ouvert} quartier={quartierOuvert} tous={defis} onFermer={fermer} onResolu={charger} />
    </div>
  {/if}
</div>

<style>
  .tete {
    padding: var(--e5) var(--gouttiere) var(--e4);
  }
  .indice {
    margin-top: var(--e3);
    color: var(--douce);
    max-width: 56ch;
  }
  .indice .btn-texte {
    min-height: 0;
    margin-left: var(--e1);
  }
  .ville-zone {
    padding: var(--e4) var(--gouttiere) 0;
    display: flex;
    flex-direction: column;
  }
  .legende {
    display: flex;
    flex-wrap: wrap;
    gap: var(--e2) var(--e5);
    margin-top: var(--e3);
    color: var(--douce);
  }
  .legende li {
    display: flex;
    align-items: center;
    gap: var(--e2);
  }
  .legende b {
    color: var(--claire);
  }
  .chronique {
    margin-top: var(--e4);
    padding-top: var(--e3);
    border-top: 1px solid var(--pierre);
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: var(--e2) var(--e5);
  }
  .chronique-titre {
    font-family: var(--display);
    font-size: 24px;
    line-height: 1;
  }
  .chronique-texte {
    flex: 1 1 18rem;
  }
  .chronique-actions {
    display: flex;
    flex-wrap: wrap;
    gap: var(--e2) var(--e4);
    align-items: center;
  }
  .volet {
    padding: 0 var(--gouttiere) var(--e7);
  }
  .volet.etat {
    display: grid;
    gap: var(--e4);
    justify-items: start;
    padding-top: var(--e4);
  }
  .quartier-liste {
    margin-top: var(--e6);
  }
  .quartier-liste:first-child {
    margin-top: var(--e3);
  }
  .q-tete {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: var(--e4);
  }
  .q-compte {
    color: var(--douce);
    white-space: nowrap;
  }
  .q-desc {
    color: var(--douce);
    margin: var(--e1) 0 var(--e3);
    max-width: 60ch;
  }
  .etages {
    border-top: 1px solid var(--pierre);
  }
  .etage {
    border-bottom: 1px solid var(--pierre);
  }
  .defi {
    display: grid;
    grid-template-columns: 12px minmax(0, 1fr) 4.5rem 7rem 5rem;
    grid-template-areas: "m nom diff res pts" ". etat etat etat etat";
    column-gap: var(--e3);
    row-gap: var(--e1);
    align-items: baseline;
    /* Le fond de survol déborde de 8 px ; le contenu reste sur le bord commun. */
    margin: 0 calc(-1 * var(--e2));
    padding: var(--e3) var(--e2);
    min-height: 56px;
    color: inherit;
    text-decoration: none;
  }
  .defi :global(.marque) {
    grid-area: m;
    align-self: start;
    margin-top: var(--e1);
  }
  .d-nom {
    grid-area: nom;
    font-size: var(--t-nom);
    line-height: 1.33;
  }
  .d-meta {
    display: contents;
  }
  .d-sep {
    display: none;
  }
  .d-diff {
    grid-area: diff;
    font-size: var(--t-meta);
    color: var(--douce);
  }
  .d-res {
    grid-area: res;
    font-size: var(--t-meta);
    color: var(--douce);
  }
  .d-pts {
    grid-area: pts;
    text-align: right;
    white-space: nowrap;
  }
  .d-etat {
    grid-area: etat;
    font-size: var(--t-meta);
    color: var(--douce);
  }
  .mot {
    font-weight: 700;
  }
  .etage[data-etat="disponible"] .d-nom {
    font-weight: 700;
  }
  .etage[data-etat="disponible"] .mot {
    color: var(--claire);
  }
  .etage[data-etat="resolu"] .mot {
    color: var(--lumignon);
  }
  .etage[data-etat="verrouille"] .defi,
  .etage[data-etat="verrouille"] .d-diff,
  .etage[data-etat="verrouille"] .d-res,
  .etage[data-etat="verrouille"] .d-etat {
    color: var(--voile);
  }
  a.defi:hover {
    background: var(--pierre-sombre);
  }
  a.defi:hover .d-nom {
    text-decoration: underline;
  }
  a.defi:focus-visible {
    outline-offset: -2px;
  }
  .credits {
    margin-top: var(--e7);
    font-size: var(--t-meta);
    color: var(--douce);
    max-width: 64ch;
  }

  /* Les crédits sont en bas de la liste : pas de second pied de page sur le plan. */
  :global(body.cadre-plan .pied) {
    display: none;
  }

  /* ---------- Bureau : cadre d'application (la carte reste visible) ---------- */
  @media (min-width: 1100px) and (min-height: 700px) {
    :global(body.cadre-plan) {
      height: 100vh;
      height: 100dvh;
      overflow: hidden;
      display: flex;
      flex-direction: column;
    }
    :global(body.cadre-plan #app) {
      flex: 1;
      min-height: 0;
      display: flex;
      flex-direction: column;
    }
    :global(body.cadre-plan main) {
      flex: 1;
      min-height: 0;
    }
    .plan {
      height: 100%;
      display: grid;
      grid-template-columns: minmax(0, 1fr) clamp(460px, 44vw, 640px);
      grid-template-rows: auto minmax(0, 1fr);
      grid-template-areas: "ville tete" "ville volet";
    }
    .ville-zone {
      grid-area: ville;
      min-height: 0;
      padding: var(--e4) var(--gouttiere);
      border-right: 1px solid var(--pierre);
    }
    .carte-cadre {
      flex: 1;
      min-height: 0;
      container-type: size;
      display: grid;
      place-items: start center;
    }
    .carte-cadre :global(.carte) {
      width: min(100cqw, 100cqh * 600 / 650);
    }
    .tete {
      grid-area: tete;
    }
    .volet {
      grid-area: volet;
      overflow-y: auto;
      overscroll-behavior: contain;
    }
    .panneau-zone {
      grid-column: 2;
      grid-row: 1 / 3;
      min-height: 0;
      display: flex;
      flex-direction: column;
      z-index: 5;
    }
    .panneau-zone :global(.panneau) {
      flex: 1;
    }
  }

  /* ---------- Tablette et mobile ---------- */
  @media (max-width: 1099px), (max-height: 699px) {
    .panneau-zone {
      position: fixed;
      inset: 0;
      z-index: 50;
      display: flex;
      flex-direction: column;
    }
    .panneau-zone :global(.panneau) {
      flex: 1;
    }
    :global(body.panneau-ouvert) {
      overflow: hidden;
    }
    .volet {
      padding-top: var(--e5);
    }
  }

  @media (max-width: 640px) {
    .carte-cadre :global(.carte) {
      aspect-ratio: 600 / 820;
    }
    .legende {
      flex-direction: column;
      gap: var(--e2);
    }
    .defi {
      grid-template-columns: 12px minmax(0, 1fr) auto;
      grid-template-areas: "m nom pts" ". meta meta" ". etat etat";
    }
    .d-meta {
      display: block;
      grid-area: meta;
      color: var(--douce);
    }
    .d-sep {
      display: inline;
    }
  }
</style>
