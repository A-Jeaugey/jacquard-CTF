<script lang="ts">
  import { api, errorMessage } from "../lib/api";
  import { formatTime, poll } from "../lib/format";
  import { navigate } from "../lib/router.svelte";
  import { session } from "../lib/session.svelte";
  import { t } from "../lib/strings";
  import type { AdminSubmission, AdminTeam, Announcement } from "../lib/types";

  type Tab = "submissions" | "teams" | "announcements";
  let tab = $state<Tab>("submissions");
  let error = $state<string | null>(null);

  let submissions = $state<AdminSubmission[]>([]);
  let filter = $state<"all" | "correct" | "incorrect">("all");
  let teams = $state<AdminTeam[]>([]);
  let announcements = $state<Announcement[]>([]);
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
    void loadAnnouncements();
  });
</script>

<h1>{t("admin.title")}</h1>

<div class="tabs" role="tablist">
  {#each ["submissions", "teams", "announcements"] as const as id (id)}
    <button role="tab" class:active={tab === id} aria-selected={tab === id} onclick={() => (tab = id)}>
      {t(`admin.tab.${id}`)}
    </button>
  {/each}
</div>

{#if error}<p class="error">{error}</p>{/if}

{#if tab === "submissions"}
  <div class="toolbar">
    <select bind:value={filter}>
      <option value="all">{t("admin.filter.all")}</option>
      <option value="correct">{t("admin.filter.correct")}</option>
      <option value="incorrect">{t("admin.filter.incorrect")}</option>
    </select>
  </div>
  <div class="table-wrap">
    <table>
      <tbody>
        {#each submissions as s (s.id)}
          <tr class:ok={s.correct}>
            <td class="muted mono">{formatTime(s.created_at, session.event?.timezone)}</td>
            <td>{s.team}<span class="muted small"> · {s.user ?? "?"}</span></td>
            <td>{s.challenge}</td>
            <td class="mono break">{s.provided}</td>
            <td>{s.correct ? "✓" : "✗"}</td>
            <td class="muted mono small">{s.ip}</td>
          </tr>
        {/each}
      </tbody>
    </table>
  </div>
  {#if submissions.length >= 100}
    <button class="secondary" onclick={loadMore}>{t("admin.load_more")}</button>
  {/if}
{:else if tab === "teams"}
  <div class="table-wrap">
    <table>
      <tbody>
        {#each teams as team (team.id)}
          <tr class:muted={team.hidden}>
            <td class="num">{team.rank ?? "—"}</td>
            <td>
              {team.name}
              {#if team.hidden}<span class="badge">{t("admin.hidden")}</span>{/if}
              <br /><span class="muted small">{team.members.join(", ")}</span>
            </td>
            <td class="num">{team.solves}</td>
            <td class="num"><strong>{team.score}</strong></td>
            <td>
              <button class="small secondary" onclick={() => toggleHidden(team)}>
                {team.hidden ? t("admin.show") : t("admin.hide")}
              </button>
            </td>
          </tr>
        {/each}
      </tbody>
    </table>
  </div>
{:else}
  <form class="card form" onsubmit={publish}>
    <label>
      {t("admin.announcement.title")}
      <input required maxlength="128" bind:value={title} />
    </label>
    <label>
      {t("admin.announcement.body")}
      <textarea required rows="4" maxlength="10000" bind:value={body}></textarea>
    </label>
    <button type="submit">{t("admin.announcement.publish")}</button>
  </form>
  {#each announcements as a (a.id)}
    <article class="card announcement">
      <header>
        <strong>{a.title}</strong>
        <button class="small secondary" onclick={() => remove(a.id)}>{t("admin.announcement.delete")}</button>
      </header>
      <div class="prose">{@html a.body_html}</div>
    </article>
  {/each}
{/if}
