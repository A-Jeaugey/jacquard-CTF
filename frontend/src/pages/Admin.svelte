<script lang="ts">
  import { api, errorMessage } from "../lib/api";
  import { formatTime, poll } from "../lib/format";
  import { navigate } from "../lib/router.svelte";
  import { session } from "../lib/session.svelte";
  import { t } from "../lib/strings";
  import type { AdminStats, AdminSubmission, AdminTeam, Announcement } from "../lib/types";

  type Tab = "submissions" | "teams" | "announcements" | "stats";
  let tab = $state<Tab>("submissions");
  let error = $state<string | null>(null);

  let submissions = $state<AdminSubmission[]>([]);
  let filter = $state<"all" | "correct" | "incorrect">("all");
  let teams = $state<AdminTeam[]>([]);
  let announcements = $state<Announcement[]>([]);
  let stats = $state<AdminStats | null>(null);
  let title = $state("");
  let body = $state("");

  function submissionsUrl(beforeId?: number): string {
    const params = new URLSearchParams({ limit: "100" });
    if (filter !== "all") params.set("correct", String(filter === "correct"));
    if (beforeId) params.set("before_id", String(beforeId));
    return `/api/admin/submissions?${params}`;
  }

  async function guard(action: () => Promise<void>): Promise<void> {
    try {
      await action();
      error = null;
    } catch (e) {
      error = errorMessage(e);
    }
  }

  const loadSubmissions = () =>
    guard(async () => {
      submissions = await api.get<AdminSubmission[]>(submissionsUrl());
    });
  const loadMore = () =>
    guard(async () => {
      const last = submissions.at(-1);
      if (last) submissions = [...submissions, ...(await api.get<AdminSubmission[]>(submissionsUrl(last.id)))];
    });
  const loadTeams = () =>
    guard(async () => {
      teams = await api.get<AdminTeam[]>("/api/admin/teams");
    });
  const loadAnnouncements = () =>
    guard(async () => {
      announcements = await api.get<Announcement[]>("/api/announcements");
    });

  const loadStats = () =>
    guard(async () => {
      stats = await api.get<AdminStats>("/api/admin/stats");
    });

  const toggleHidden = (team: AdminTeam) =>
    guard(async () => {
      await api.patch(`/api/admin/teams/${team.id}`, { hidden: !team.hidden });
      await loadTeams();
    });

  function publish(event: SubmitEvent): void {
    event.preventDefault();
    void guard(async () => {
      await api.post("/api/admin/announcements", { title, body });
      title = "";
      body = "";
      await loadAnnouncements();
    });
  }

  const remove = (id: number) =>
    guard(async () => {
      await api.delete(`/api/admin/announcements/${id}`);
      await loadAnnouncements();
    });

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

  const unChiffre = new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 1 });
  const minutes = (valeur: number | null): string => (valeur === null ? "—" : unChiffre.format(valeur));
</script>

<div class="page">
  <h1 class="titre-page">{t("admin.title")}</h1>

  <div class="onglets" role="tablist" aria-label={t("admin.title")}>
    {#each ["submissions", "teams", "announcements", "stats"] as const as id (id)}
      <button type="button" role="tab" aria-selected={tab === id} onclick={() => (tab = id)}>
        {t(`admin.tab.${id}`)}
      </button>
    {/each}
  </div>

  {#if error}
    <p class="refus" role="alert"><b>{t("error.title")}</b> {error}</p>
  {/if}

  <div class="contenu" role="tabpanel">
    {#if tab === "submissions"}
      <div class="outils">
        <label class="etiquette" for="filtre">{t("admin.filter.label")}</label>
        <select id="filtre" class="saisie choix" bind:value={filter}>
          <option value="all">{t("admin.filter.all")}</option>
          <option value="correct">{t("admin.filter.correct")}</option>
          <option value="incorrect">{t("admin.filter.incorrect")}</option>
        </select>
      </div>
      {#if submissions.length}
        <div class="defile">
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
          <p><button type="button" class="btn-ligne" onclick={loadMore}>{t("admin.load_more")}</button></p>
        {/if}
      {:else}
        <p class="secondaire">{t("admin.submissions.none")}</p>
      {/if}
    {:else if tab === "teams"}
      {#if teams.length}
        <div class="defile">
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
                  <td>
                    <button type="button" class="btn-ligne" onclick={() => toggleHidden(team)}>
                      {team.hidden ? t("admin.show") : t("admin.hide")}
                    </button>
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      {:else}
        <p class="secondaire">{t("scoreboard.empty")}</p>
      {/if}
    {:else if tab === "stats"}
      {#if stats}
        <div class="defile">
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
                  <td>{c.name}<br /><span class="meta">{c.category}</span></td>
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
              {:else if signal.kind === "burst"}{t("admin.signal.burst", { team: signal.team, at: signal.at_minutes })}
              {:else}{t("admin.signal.same_wrong", { challenge: signal.challenge, value: signal.value, teams: signal.teams.join(", ") })}{/if}
            </p>
          {:else}
            <p class="secondaire">{t("admin.signals.none")}</p>
          {/each}
        </section>
      {:else}
        <p class="secondaire">{t("loading")}</p>
      {/if}
    {:else}
      <form class="annonce-form" onsubmit={publish}>
        <div class="champ">
          <label for="annonce-titre">{t("admin.announcement.title")}</label>
          <input id="annonce-titre" class="saisie" required maxlength="128" bind:value={title} />
        </div>
        <div class="champ">
          <label for="annonce-texte">{t("admin.announcement.body")}</label>
          <textarea id="annonce-texte" class="saisie zone" required rows="5" maxlength="10000" bind:value={body}></textarea>
        </div>
        <p><button type="submit" class="btn-principal">{t("admin.announcement.publish")}</button></p>
      </form>
      {#each announcements as a (a.id)}
        <article class="annonce">
          <div class="annonce-tete">
            <h2 class="titre-bloc">{a.title}</h2>
            <button type="button" class="btn-texte" onclick={() => remove(a.id)}>{t("admin.announcement.delete")}</button>
          </div>
          <!-- HTML assaini côté serveur. -->
          <div class="prose">{@html a.body_html}</div>
        </article>
      {:else}
        <p class="secondaire">{t("home.no_announcements")}</p>
      {/each}
    {/if}
  </div>
</div>

<style>
  .onglets {
    display: flex;
    flex-wrap: wrap;
    gap: var(--e1);
    margin-top: var(--e5);
    border-bottom: 1px solid var(--pierre);
  }
  .onglets button {
    min-height: 44px;
    padding: 0 var(--e3);
    border: 0;
    background: none;
    color: var(--douce);
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
  .defile {
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
  .signaux {
    margin-top: var(--e6);
  }
  .signaux .aide {
    margin: var(--e2) 0 var(--e3);
    max-width: 72ch;
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
  .annonce .prose {
    margin-top: var(--e2);
  }
</style>
