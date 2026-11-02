<script lang="ts">
  import { untrack } from "svelte";

  import ChallengeModal from "../components/ChallengeModal.svelte";
  import { getLayout, ImageMapBoard } from "../components/layouts";
  import { api, errorMessage } from "../lib/api";
  import { poll } from "../lib/format";
  import { live } from "../lib/live.svelte";
  import { navigate } from "../lib/router.svelte";
  import { session } from "../lib/session.svelte";
  import { t } from "../lib/strings";
  import { theme } from "../lib/theme.svelte";
  import type { BoardData, ChallengeList } from "../lib/types";

  let list = $state<ChallengeList | null>(null);
  let error = $state<string | null>(null);
  let openId = $state<string | null>(null);
  let hideSolved = $state(false);

  async function load(): Promise<void> {
    try {
      list = await api.get<ChallengeList>("/api/challenges");
      error = null;
    } catch (e) {
      error = errorMessage(e);
    }
  }

  $effect(() => {
    if (!session.me) {
      navigate("/login", true);
      return;
    }
    return poll(load, 60_000);
  });

  // Rechargement immédiat quand une résolution ou un déblocage arrive en temps réel.
  $effect(() => {
    void live.ticks.solve;
    void live.ticks.unlock;
    void live.ticks.team;
    if (untrack(() => list)) void load();
  });

  const layoutId = $derived(session.event?.board.layout ?? "grid");
  const mapLayout = $derived(theme.data?.layouts[layoutId] ?? null);
  const Layout = $derived(getLayout(layoutId));

  // Choix carte / grille mémorisé dans le navigateur (simple confort).
  const VIEW_KEY = "jq_board_view";
  let gridView = $state(readGridPreference());
  function readGridPreference(): boolean {
    try {
      return localStorage.getItem(VIEW_KEY) === "grid";
    } catch {
      return false;
    }
  }
  function toggleView(): void {
    gridView = !gridView;
    try {
      localStorage.setItem(VIEW_KEY, gridView ? "grid" : "map");
    } catch {
      // stockage indisponible : le choix vaut pour cette page seulement
    }
  }
  const data = $derived<BoardData>({
    categories: session.event?.categories ?? [],
    difficulties: session.event?.difficulties ?? [],
    challenges: (list?.challenges ?? []).filter((c) => !hideSolved || !c.solved),
  });
  const needsTeam = $derived(session.me !== null && !session.me.team && session.me.user.role !== "admin");
</script>

<div class="page-header">
  <h1>{t("board.title")}</h1>
  {#if list?.challenges.length}
    <div class="board-tools">
      {#if mapLayout}
        <button class="small secondary" onclick={toggleView}>{gridView ? t("board.view_map") : t("board.view_grid")}</button>
      {/if}
      <label class="checkbox"><input type="checkbox" bind:checked={hideSolved} /> {t("board.filter.unsolved")}</label>
    </div>
  {/if}
</div>

{#if error}
  <p class="error">{error}</p>
{:else if needsTeam}
  <div class="card">
    <p>{t("board.need_team")}</p>
    <a class="button" href="/team">{t("home.cta.team")}</a>
  </div>
{:else if !list}
  <p class="muted">{t("loading")}</p>
{:else if list.phase === "not_started" && list.challenges.length === 0}
  <div class="card">{t("board.not_started")}</div>
{:else if list.challenges.length === 0}
  <div class="card">{t("board.empty")}</div>
{:else}
  {#if mapLayout && !gridView}
    <ImageMapBoard {data} layout={mapLayout} onOpen={(id) => (openId = id)} />
  {:else}
    <Layout {data} onOpen={(id) => (openId = id)} />
  {/if}
{/if}

{#if openId}
  <ChallengeModal id={openId} onClose={() => (openId = null)} onSolved={load} />
{/if}
