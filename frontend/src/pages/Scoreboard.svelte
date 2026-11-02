<script lang="ts">
  import { untrack } from "svelte";

  import { api, errorMessage } from "../lib/api";
  import { formatTime, poll } from "../lib/format";
  import { live } from "../lib/live.svelte";
  import { session } from "../lib/session.svelte";
  import { t } from "../lib/strings";
  import type { Scoreboard } from "../lib/types";

  let board = $state<Scoreboard | null>(null);
  let error = $state<string | null>(null);

  async function load(): Promise<void> {
    try {
      board = await api.get<Scoreboard>("/api/scoreboard");
      error = null;
    } catch (e) {
      error = errorMessage(e);
    }
  }

  $effect(() => poll(load, 60_000));
  $effect(() => {
    void live.ticks.solve;
    void live.ticks.team;
    if (untrack(() => board)) void load();
  });

  const myTeam = $derived(session.me?.team?.id ?? null);
</script>

<h1>{t("scoreboard.title")}</h1>

{#if error}<p class="error">{error}</p>{/if}

{#if board}
  {#if board.frozen && board.frozen_at}
    <p class="feedback info">{t("scoreboard.frozen", { time: formatTime(board.frozen_at, session.event?.timezone) })}</p>
  {/if}
  {#if board.teams.length}
    <table class="scoreboard">
      <thead>
        <tr>
          <th class="num">{t("scoreboard.rank")}</th>
          <th>{t("scoreboard.team")}</th>
          <th class="num">{t("scoreboard.solves")}</th>
          <th class="num">{t("scoreboard.score")}</th>
        </tr>
      </thead>
      <tbody>
        {#each board.teams as entry (entry.team_id)}
          <tr class:mine={entry.team_id === myTeam} class:podium={entry.rank <= 3 && entry.score > 0}>
            <td class="num">{entry.rank}</td>
            <td>{entry.name}</td>
            <td class="num">{entry.solves}</td>
            <td class="num"><strong>{entry.score}</strong></td>
          </tr>
        {/each}
      </tbody>
    </table>
  {:else}
    <p class="muted">{t("scoreboard.empty")}</p>
  {/if}
{:else if !error}
  <p class="muted">{t("loading")}</p>
{/if}
