<script lang="ts">
  import { tick } from "svelte";

  import Reessayer from "../components/Reessayer.svelte";
  import { api, ApiError, errorMessage } from "../lib/api";
  import { formatTime, poll } from "../lib/format";
  import { navigate } from "../lib/router.svelte";
  import { session } from "../lib/session.svelte";
  import { t } from "../lib/strings";
  import type { AdminStats, AdminSubmission, AdminTeam, Announcement } from "../lib/types";

  type Tab = "submissions" | "teams" | "announcements" | "stats";
  const ONGLETS: Tab[] = ["submissions", "teams", "announcements", "stats"];
  let tab = $state<Tab>("submissions");

  let submissions = $state<AdminSubmission[]>([]);
  let filter = $state<"all" | "correct" | "incorrect">("all");
  let teams = $state<AdminTeam[]>([]);
  let announcements = $state<Announcement[]>([]);
  let stats = $state<AdminStats | null>(null);
  let title = $state("");
  let body = $state("");

  // Par onglet : données reçues au moins une fois, et dernière erreur de chargement.
  let charges = $state<Record<Tab, boolean>>({ submissions: false, teams: false, announcements: false, stats: false });
  let erreurs = $state<Record<Tab, string | null>>({ submissions: null, teams: null, announcements: null, stats: null });
  // Retour d'une action (publier, supprimer, masquer), affiché près de ce qui l'a provoquée.
  let retour = $state<{ ou: "form" | "liste"; sorte: "ok" | "erreur"; texte: string } | null>(null);
  let publication = $state(false);
  // Champs de l'annonce refusés par une validation du serveur.
  let champsAnnonce = $state<string[]>([]);
  const CHAMPS_ANNONCE: Record<string, { id: string; libelle: () => string }> = {
    title: { id: "annonce-titre", libelle: () => t("admin.announcement.title") },
    body: { id: "annonce-texte", libelle: () => t("admin.announcement.body") },
  };
  let aSupprimer = $state<number | null>(null);

  function submissionsUrl(beforeId?: number): string {
    const params = new URLSearchParams({ limit: "100" });
    if (filter !== "all") params.set("correct", String(filter === "correct"));
    if (beforeId) params.set("before_id", String(beforeId));
    return `/api/admin/submissions?${params}`;
  }

  async function charger(onglet: Tab, action: () => Promise<void>): Promise<void> {
    try {
      await action();
      charges[onglet] = true;
      erreurs[onglet] = null;
    } catch (e) {
      erreurs[onglet] = errorMessage(e);
    }
  }

  const loadSubmissions = () =>
    charger("submissions", async () => {
      submissions = await api.get<AdminSubmission[]>(submissionsUrl());
    });
  const loadMore = () =>
    charger("submissions", async () => {
      const last = submissions.at(-1);
      if (last) submissions = [...submissions, ...(await api.get<AdminSubmission[]>(submissionsUrl(last.id)))];
    });
  const loadTeams = () =>
    charger("teams", async () => {
      teams = await api.get<AdminTeam[]>("/api/admin/teams");
    });
  const loadAnnouncements = () =>
    charger("announcements", async () => {
      announcements = await api.get<Announcement[]>("/api/announcements");
    });
  const loadStats = () =>
    charger("stats", async () => {
      stats = await api.get<AdminStats>("/api/admin/stats");
    });
  const recharger: Record<Tab, () => Promise<void>> = {
    submissions: loadSubmissions,
    teams: loadTeams,
    announcements: loadAnnouncements,
    stats: loadStats,
  };

  async function toggleHidden(team: AdminTeam): Promise<void> {
    try {
      await api.patch(`/api/admin/teams/${team.id}`, { hidden: !team.hidden });
      retour = { ou: "liste", sorte: "ok", texte: t(team.hidden ? "admin.team.shown_done" : "admin.team.hidden_done", { team: team.name }) };
      await loadTeams();
    } catch (e) {
      retour = { ou: "liste", sorte: "erreur", texte: errorMessage(e) };
    }
  }

  async function publish(event: SubmitEvent): Promise<void> {
    event.preventDefault();
    // Bouton « en cours » par aria-disabled : il garde le focus pendant l'envoi.
    if (publication) return;
    publication = true;
    retour = null;
    champsAnnonce = [];
    try {
      await api.post("/api/admin/announcements", { title, body });
      title = "";
      body = "";
      retour = { ou: "form", sorte: "ok", texte: t("admin.announcement.published") };
      await loadAnnouncements();
    } catch (e) {
      const champs = e instanceof ApiError && Array.isArray(e.extra.fields) ? (e.extra.fields as string[]) : [];
      champsAnnonce = champs.filter((c) => c in CHAMPS_ANNONCE);
      const texte = champsAnnonce.length
        ? t("admin.announcement.invalid", { fields: champsAnnonce.map((c) => CHAMPS_ANNONCE[c]?.libelle() ?? c).join(", ") })
        : errorMessage(e);
      retour = { ou: "form", sorte: "erreur", texte };
    } finally {
      publication = false;
    }
    await tick();
    if (retour?.sorte === "erreur") {
      // Le champ en cause s'il est connu ; sinon le message lui-même, pas un champ au hasard.
      const premier = champsAnnonce[0];
      document.getElementById(premier ? (CHAMPS_ANNONCE[premier]?.id ?? "retour-annonce") : "retour-annonce")?.focus();
    }
  }

  async function demanderSuppression(id: number): Promise<void> {
    aSupprimer = id;
    await tick();
    document.getElementById(`confirmer-${id}`)?.focus();
  }

  async function annulerSuppression(id: number): Promise<void> {
    aSupprimer = null;
    await tick();
    document.getElementById(`supprimer-${id}`)?.focus();
  }

  async function supprimer(id: number): Promise<void> {
    aSupprimer = null;
    try {
      await api.delete(`/api/admin/announcements/${id}`);
      retour = { ou: "liste", sorte: "ok", texte: t("admin.announcement.deleted") };
      await loadAnnouncements();
    } catch (e) {
      retour = { ou: "liste", sorte: "erreur", texte: errorMessage(e) };
    }
    await tick();
    document.getElementById("h-annonces-publiees")?.focus();
  }

  function clavier(event: KeyboardEvent): void {
    if (event.key === "Escape" && aSupprimer !== null) {
      event.preventDefault();
      void annulerSuppression(aSupprimer);
    }
  }

  // Onglets : flèches, Début et Fin déplacent la sélection ; un seul onglet est tabulable.
  async function clavierOnglets(event: KeyboardEvent): Promise<void> {
    const i = ONGLETS.indexOf(tab);
    const cible =
      event.key === "ArrowRight"
        ? ONGLETS[(i + 1) % ONGLETS.length]
        : event.key === "ArrowLeft"
          ? ONGLETS[(i - 1 + ONGLETS.length) % ONGLETS.length]
          : event.key === "Home"
            ? ONGLETS[0]
            : event.key === "End"
              ? ONGLETS[ONGLETS.length - 1]
              : null;
    if (!cible) return;
    event.preventDefault();
    choisir(cible);
    await tick();
    document.getElementById(`onglet-${cible}`)?.focus();
  }

  function choisir(onglet: Tab): void {
    tab = onglet;
    retour = null;
    aSupprimer = null;
  }

  // Depuis un état vide : l'onglet Annonces s'ouvre et le focus va au champ à remplir.
  async function allerAuxAnnonces(): Promise<void> {
    choisir("announcements");
    await tick();
    document.getElementById("annonce-titre")?.focus();
  }

  $effect(() => {
    if (session.me?.user.role !== "admin") {
      navigate("/", true);
      return;
    }
    void filter;
    if (tab === "submissions") return poll(loadSubmissions, 10_000);
    if (tab === "teams") return poll(loadTeams, 30_000);
    if (tab === "stats") return poll(loadStats, 30_000);
    void loadAnnouncements();
  });

  // Toujours une décimale : les virgules s'alignent dans les colonnes.
  const unChiffre = new Intl.NumberFormat("fr-FR", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
  // Les identifiants du pack deviennent les noms que tout le monde lit ailleurs.
  const nomQuartier = (id: string): string => session.event?.categories.find((c) => c.id === id)?.name ?? id;
  const nomDefi = (id: string): string => stats?.challenges.find((c) => c.id === id)?.name ?? id;
  const minutes = (valeur: number | null): string => (valeur === null ? "—" : unChiffre.format(valeur));
</script>

<svelte:window onkeydown={clavier} />

{#snippet etat(onglet: Tab)}
  {#if erreurs[onglet]}
    <div class="etat" role="alert">
      <p class="refus">
        <b>{t("error.title")}</b>
        {erreurs[onglet]}
        {#if charges[onglet]}{t("admin.stale")}{/if}
      </p>
      <p><Reessayer action={recharger[onglet]} cible="panneau-admin" /></p>
    </div>
  {:else if !charges[onglet]}
    <p class="secondaire">{t("loading")}</p>
  {/if}
{/snippet}

{#snippet message(ou: "form" | "liste")}
  {#if retour?.ou === ou}
    {#if retour.sorte === "ok"}
      <p class="succes" role="status">{retour.texte}</p>
    {:else}
      <p class="refus" id={ou === "form" ? "retour-annonce" : undefined} tabindex="-1" role="alert">
        <b>{t("error.title")}</b>
        {retour.texte}
      </p>
    {/if}
  {/if}
{/snippet}

<div class="page">
  <h1 class="titre-page">{t("admin.title")}</h1>

  <div class="onglets" role="tablist" aria-label={t("admin.title")} tabindex="-1" onkeydown={clavierOnglets}>
    {#each ONGLETS as id (id)}
      <button
        type="button"
        role="tab"
        id="onglet-{id}"
        aria-selected={tab === id}
        aria-controls="panneau-admin"
        tabindex={tab === id ? 0 : -1}
        onclick={() => choisir(id)}
      >
        {t(`admin.tab.${id}`)}
      </button>
    {/each}
  </div>

  <div class="contenu" role="tabpanel" id="panneau-admin" aria-labelledby="onglet-{tab}" tabindex="-1">
    {#if tab === "submissions"}
      <div class="outils">
        <label class="etiquette" for="filtre">{t("admin.filter.label")}</label>
        <select id="filtre" class="saisie choix" bind:value={filter}>
          <option value="all">{t("admin.filter.all")}</option>
          <option value="correct">{t("admin.filter.correct")}</option>
          <option value="incorrect">{t("admin.filter.incorrect")}</option>
        </select>
      </div>
      {@render etat("submissions")}
      {#if submissions.length}
        <!-- Région qui défile : atteignable au clavier pour lire les colonnes masquées (WCAG 2.1.1). -->
        <!-- svelte-ignore a11y_no_noninteractive_tabindex -->
        <div class="defile" tabindex="0" role="region" aria-label={t("admin.scroll", { name: t("admin.tab.submissions") })}>
          <table>
            <thead>
              <tr>
                <th>{t("admin.col.time")}</th>
                <th>{t("admin.col.team")}</th>
                <th>{t("admin.col.challenge")}</th>
                <th>{t("admin.col.flag")}</th>
                <th>{t("admin.col.result")}</th>
                <th>{t("admin.col.ip")}</th>
              </tr>
            </thead>
            <tbody>
              {#each submissions as s (s.id)}
                <tr>
                  <td class="tnum secondaire">{formatTime(s.created_at, session.event?.timezone)}</td>
                  <td>{s.team}<br /><span class="meta">{s.user ?? "—"}</span></td>
                  <td>{s.challenge}</td>
                  <td><code class="valeur">{s.provided}</code></td>
                  <td class:correct={s.correct}>{s.correct ? t("admin.result.correct") : t("admin.result.wrong")}</td>
                  <td class="tnum meta">{s.ip}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
        {#if submissions.length >= 100}
          <p class="suite"><button type="button" class="btn-ligne" onclick={loadMore}>{t("admin.load_more")}</button></p>
        {/if}
      {:else if charges.submissions && filter !== "all"}
        <p class="secondaire">{t("admin.submissions.none_filtered")}</p>
        <p class="suite"><button type="button" class="btn-ligne" onclick={() => (filter = "all")}>{t("admin.filter.reset")}</button></p>
      {:else if charges.submissions}
        <p class="secondaire">{t("admin.submissions.none")}</p>
        <p class="suite"><button type="button" class="btn-ligne" onclick={allerAuxAnnonces}>{t("admin.go_announce")}</button></p>
      {/if}
    {:else if tab === "teams"}
      {@render etat("teams")}
      {@render message("liste")}
      {#if teams.length}
        <!-- Région qui défile : atteignable au clavier pour lire les colonnes masquées (WCAG 2.1.1). -->
        <!-- svelte-ignore a11y_no_noninteractive_tabindex -->
        <div class="defile" tabindex="0" role="region" aria-label={t("admin.scroll", { name: t("admin.tab.teams") })}>
          <table>
            <thead>
              <tr>
                <th>{t("admin.col.rank")}</th>
                <th>{t("admin.col.team")}</th>
                <th class="nombre">{t("admin.col.solves")}</th>
                <th class="nombre">{t("admin.col.score")}</th>
                <th><span class="sr-only">{t("admin.col.actions")}</span></th>
              </tr>
            </thead>
            <tbody>
              {#each teams as team (team.id)}
                <tr class:masquee={team.hidden}>
                  <td class="tnum">{team.rank ?? "—"}</td>
                  <td>
                    {team.name}
                    {#if team.hidden}<span class="meta">{t("admin.hidden")}</span>{/if}
                    <br /><span class="meta">{team.members.join(", ")}</span>
                  </td>
                  <td class="nombre tnum">{team.solves}</td>
                  <td class="nombre tnum">{team.score}</td>
                  <td class="nombre">
                    <button type="button" class="btn-ligne" onclick={() => toggleHidden(team)}>
                      {team.hidden ? t("admin.show") : t("admin.hide")}
                    </button>
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      {:else if charges.teams}
        <p class="secondaire">{t("admin.teams.none")}</p>
        <p class="suite"><button type="button" class="btn-ligne" onclick={allerAuxAnnonces}>{t("admin.go_announce")}</button></p>
      {/if}
    {:else if tab === "stats"}
      {@render etat("stats")}
      {#if stats && stats.challenges.length === 0}
        <p class="secondaire">{t("admin.stats.none")}</p>
      {:else if stats}
        <!-- Région qui défile : atteignable au clavier pour lire les colonnes masquées (WCAG 2.1.1). -->
        <!-- svelte-ignore a11y_no_noninteractive_tabindex -->
        <div class="defile" tabindex="0" role="region" aria-label={t("admin.scroll", { name: t("admin.tab.stats") })}>
          <table>
            <thead>
              <tr>
                <th>{t("admin.stats.challenge")}</th>
                <th class="nombre">{t("admin.stats.solves")}</th>
                <th class="nombre">{t("admin.stats.wrong")}</th>
                <th class="nombre">{t("admin.stats.hints")}</th>
                <th class="nombre">{t("admin.stats.first")}</th>
                <th class="nombre">{t("admin.stats.median")}</th>
                <th>{t("admin.stats.top_wrong")}</th>
              </tr>
            </thead>
            <tbody>
              {#each stats.challenges as c (c.id)}
                <tr class:inactif={c.attempts === 0}>
                  <td>
                    {c.name}<br /><span class="meta">{nomQuartier(c.category)}{#if c.attempts === 0}, {t("admin.no_attempts")}{/if}</span>
                  </td>
                  <td class="nombre tnum">{c.solves}</td>
                  <td class="nombre tnum">{c.wrong}</td>
                  <td class="nombre tnum">{c.hints}</td>
                  <td class="nombre tnum">{minutes(c.first_solve_minutes)}</td>
                  <td class="nombre tnum">{minutes(c.median_solve_minutes)}</td>
                  <td>
                    {#each c.top_wrong as w (w.value)}
                      <div><code class="valeur">{w.value}</code> <span class="meta">{t("admin.times", { n: w.count })}</span></div>
                    {/each}
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
        <section class="signaux" aria-labelledby="h-signaux">
          <h2 class="titre-bloc" id="h-signaux">{t("admin.signals")}</h2>
          <p class="aide">{t("admin.signals.note")}</p>
          {#each stats.signals as signal, i (i)}
            <p class="signal">
              {#if signal.kind === "shared_ip"}{t("admin.signal.shared_ip", { ip: signal.ip, teams: signal.teams.join(", ") })}
              {:else if signal.kind === "burst"}{t("admin.signal.burst", { team: signal.team, at: minutes(signal.at_minutes) })}
              {:else}{t("admin.signal.same_wrong", { challenge: nomDefi(signal.challenge), value: signal.value, teams: signal.teams.join(", ") })}{/if}
            </p>
          {:else}
            <p class="secondaire">{t("admin.signals.none")}</p>
          {/each}
        </section>
      {/if}
    {:else}
      <form class="annonce-form" onsubmit={publish}>
        <div class="champ">
          <label for="annonce-titre">{t("admin.announcement.title")}</label>
          <input
            id="annonce-titre"
            class="saisie"
            required
            maxlength="128"
            bind:value={title}
            aria-invalid={champsAnnonce.includes("title") ? "true" : undefined}
            aria-describedby={retour?.ou === "form" && retour.sorte === "erreur" ? "retour-annonce" : undefined}
          />
        </div>
        <div class="champ">
          <label for="annonce-texte">{t("admin.announcement.body")}</label>
          <textarea
            id="annonce-texte"
            class="saisie zone"
            required
            rows="5"
            maxlength="10000"
            bind:value={body}
            aria-invalid={champsAnnonce.includes("body") ? "true" : undefined}
            aria-describedby={retour?.ou === "form" && retour.sorte === "erreur" ? "retour-annonce" : undefined}
          ></textarea>
        </div>
        {@render message("form")}
        <p>
          <button type="submit" class="btn-principal" aria-disabled={publication ? "true" : undefined}>
            {publication ? t("admin.announcement.publishing") : t("admin.announcement.publish")}
          </button>
        </p>
      </form>
      <h2 class="titre-bloc publiees" id="h-annonces-publiees" tabindex="-1">{t("admin.tab.announcements")}</h2>
      {@render etat("announcements")}
      {@render message("liste")}
      {#each announcements as a (a.id)}
        <article class="annonce">
          <div class="annonce-tete">
            <h3 class="titre-bloc">{a.title}</h3>
            {#if aSupprimer !== a.id}
              <button type="button" class="btn-texte" id="supprimer-{a.id}" onclick={() => demanderSuppression(a.id)}>
                {t("admin.announcement.delete")}
              </button>
            {/if}
          </div>
          {#if aSupprimer === a.id}
            <div class="confirmation">
              <p>{t("admin.announcement.confirm_delete", { title: a.title })}</p>
              <p class="choix-actions">
                <button type="button" class="btn-ligne" id="confirmer-{a.id}" onclick={() => supprimer(a.id)}>
                  {t("admin.announcement.delete")}
                </button>
                <button type="button" class="btn-texte" onclick={() => annulerSuppression(a.id)}>{t("action.cancel")}</button>
              </p>
            </div>
          {/if}
          <!-- HTML assaini côté serveur. -->
          <div class="prose">{@html a.body_html}</div>
        </article>
      {:else}
        {#if charges.announcements}<p class="secondaire">{t("admin.announcements.none")}</p>{/if}
      {/each}
    {/if}
  </div>
</div>

<style>
  .onglets {
    display: flex;
    flex-wrap: wrap;
    gap: var(--e4);
    margin-top: var(--e5);
    border-bottom: 1px solid var(--pierre);
  }
  .onglets:focus {
    outline: none;
  }
  /* Le texte des onglets part du même bord que le titre. */
  .onglets button {
    min-height: 44px;
    padding: 0;
    border: 0;
    background: none;
    color: var(--douce);
  }
  .onglets button:hover {
    color: var(--claire);
  }
  .onglets button:active {
    color: var(--claire);
    text-decoration: underline;
    text-underline-offset: 8px;
  }
  .onglets button[aria-selected="true"] {
    color: var(--claire);
    font-weight: 700;
    text-decoration: underline;
    text-decoration-thickness: 2px;
    text-underline-offset: 8px;
  }
  .contenu {
    margin-top: var(--e5);
  }
  .outils {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: var(--e3);
    margin-bottom: var(--e4);
  }
  .choix {
    width: auto;
    min-width: 12rem;
  }
  .etat {
    margin-bottom: var(--e4);
  }
  .etat .refus {
    max-width: 72ch;
    margin-bottom: var(--e2);
  }
  .succes {
    margin-bottom: var(--e4);
    font-weight: 700;
  }
  .defile {
    position: relative;
    overflow-x: auto;
  }
  table {
    width: 100%;
    border-collapse: collapse;
  }
  th {
    text-align: left;
    font-size: var(--t-meta);
    font-weight: 700;
    color: var(--douce);
    padding: var(--e2) var(--e3);
    border-bottom: 1px solid var(--pierre);
  }
  td {
    padding: var(--e3);
    border-bottom: 1px solid var(--pierre);
    vertical-align: top;
  }
  /* Un seul bord gauche et un seul bord droit : ceux du titre de la page. */
  th:first-child,
  td:first-child {
    padding-left: 0;
  }
  th:last-child,
  td:last-child {
    padding-right: 0;
  }
  .nombre {
    text-align: right;
  }
  .valeur {
    font-family: var(--texte);
    background: var(--eau);
    padding: 0 var(--e1);
    border-radius: 2px;
    overflow-wrap: anywhere;
  }
  .correct {
    color: var(--lumignon);
    font-weight: 700;
  }
  .masquee td,
  .inactif td {
    color: var(--voile);
  }
  .suite {
    margin-top: var(--e5);
  }
  .signaux {
    margin-top: var(--e6);
  }
  /* Luciole est large : 60ch tient environ 80 caractères réels par ligne. */
  .signaux .aide,
  .signal {
    max-width: 60ch;
  }
  .signaux .aide {
    margin: var(--e2) 0 var(--e3);
  }
  .signal {
    padding: var(--e3) 0;
    border-bottom: 1px solid var(--pierre);
  }
  .annonce-form {
    display: grid;
    gap: var(--e4);
    max-width: 640px;
  }
  .zone {
    min-height: 120px;
    padding: var(--e3);
    font-size: var(--t-texte);
  }
  .publiees {
    margin: var(--e7) 0 var(--e3);
  }
  .annonce {
    margin-top: var(--e5);
    padding-top: var(--e4);
    border-top: 1px solid var(--pierre);
  }
  .annonce-tete {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: var(--e4);
  }
  .confirmation {
    margin-top: var(--e2);
  }
  .choix-actions {
    display: flex;
    flex-wrap: wrap;
    gap: var(--e3);
    align-items: center;
    margin-top: var(--e2);
  }
  .annonce .prose {
    margin-top: var(--e2);
  }
</style>
