<script lang="ts">
  import ChallengeModal from "../components/ChallengeModal.svelte";
  import { getLayout } from "../components/layouts";
  import { api, errorMessage } from "../lib/api";
  import { poll } from "../lib/format";
  import { navigate } from "../lib/router.svelte";
  import { session } from "../lib/session.svelte";
  import { t } from "../lib/strings";
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
    return poll(load, 30_000);
  });

  const Layout = $derived(getLayout(session.event?.board.layout));
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
    <label class="checkbox"><input type="checkbox" bind:checked={hideSolved} /> {t("board.filter.unsolved")}</label>
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
  <Layout {data} onOpen={(id) => (openId = id)} />
{/if}

{#if openId}
  <ChallengeModal id={openId} onClose={() => (openId = null)} onSolved={load} />
{/if}
