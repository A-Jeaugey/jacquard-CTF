<script lang="ts">
  import { api, errorMessage } from "../lib/api";
  import { formatTime } from "../lib/format";
  import { navigate } from "../lib/router.svelte";
  import { refreshMe, session } from "../lib/session.svelte";
  import { t } from "../lib/strings";
  import type { TeamDetail } from "../lib/types";

  let team = $state<TeamDetail | null>(null);
  let loaded = $state(false);
  let name = $state("");
  let code = $state("");
  let error = $state<string | null>(null);
  let busy = $state(false);

  const teamsMode = $derived(session.event?.participation.mode === "teams");

  async function load(): Promise<void> {
    team = await api.get<TeamDetail | null>("/api/teams/me");
    loaded = true;
  }

  async function run(action: () => Promise<unknown>): Promise<void> {
    busy = true;
    error = null;
    try {
      await action();
      await Promise.all([load(), refreshMe()]);
    } catch (e) {
      error = errorMessage(e);
    } finally {
      busy = false;
    }
  }

  function create(event: SubmitEvent): void {
    event.preventDefault();
    void run(() => api.post("/api/teams", { name }));
  }

  function join(event: SubmitEvent): void {
    event.preventDefault();
    void run(() => api.post("/api/teams/join", { invite_code: code }));
  }

  function leave(): void {
    if (confirm(t("team.leave.confirm"))) void run(() => api.post("/api/teams/leave"));
  }

  $effect(() => {
    if (!session.me) navigate("/login", true);
    else void load();
  });
</script>

{#if error}<p class="error" role="alert">{error}</p>{/if}

{#if !loaded}
  <p class="muted">{t("loading")}</p>
{:else if team}
  <section class="card">
    <h1>{team.name}</h1>
    <div class="stats">
      <div><span class="muted small">{t("team.score")}</span><strong>{team.score}</strong></div>
      <div><span class="muted small">{t("team.rank")}</span><strong>{team.rank ?? "—"}</strong></div>
      <div><span class="muted small">{t("team.solves")}</span><strong>{team.solves.length}</strong></div>
    </div>

    {#if team.invite_code}
      <p>
        <span class="muted small">{t("team.invite")}</span><br />
        <code class="invite">{team.invite_code}</code>
      </p>
    {:else if !teamsMode}
      <p class="muted">{t("team.solo")}</p>
    {/if}

    <h2>{t("team.members")} ({team.members.length}/{team.max_size})</h2>
    <ul>
      {#each team.members as member (member.id)}<li>{member.username}</li>{/each}
    </ul>

    <h2>{t("team.solves")}</h2>
    {#if team.solves.length}
      <table>
        <tbody>
          {#each team.solves as solve (solve.challenge_id)}
            <tr>
              <td>{solve.challenge_name}</td>
              <td class="muted">{solve.solved_by ?? ""}</td>
              <td class="muted">{formatTime(solve.solved_at, session.event?.timezone)}</td>
              <td class="num">{solve.points}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    {:else}
      <p class="muted">{t("team.no_solves")}</p>
    {/if}

    {#if teamsMode && team.solves.length === 0}
      <button class="secondary" disabled={busy} onclick={leave}>{t("team.leave")}</button>
    {/if}
  </section>
{:else if teamsMode}
  <div class="split">
    <form class="card form" onsubmit={create}>
      <h2>{t("team.create")}</h2>
      <label>
        {t("team.create.name")}
        <input required minlength="2" maxlength="64" bind:value={name} />
      </label>
      <button type="submit" disabled={busy}>{t("team.create.submit")}</button>
    </form>
    <form class="card form" onsubmit={join}>
      <h2>{t("team.join")}</h2>
      <label>
        {t("team.join.code")}
        <input required class="mono" autocomplete="off" bind:value={code} />
      </label>
      <button type="submit" disabled={busy}>{t("team.join.submit")}</button>
    </form>
  </div>
{/if}
