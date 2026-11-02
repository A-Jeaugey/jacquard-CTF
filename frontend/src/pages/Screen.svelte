<script lang="ts">
  // Grand écran public (vidéoprojecteur) : carte en progression globale, classement,
  // fil d'actualité et compte à rebours. Aucune information sur le contenu des défis.
  import { untrack } from "svelte";

  import MapCanvas from "../components/MapCanvas.svelte";
  import { api, errorMessage } from "../lib/api";
  import { formatDuration, formatTime, poll } from "../lib/format";
  import { live } from "../lib/live.svelte";
  import { serverNow, session } from "../lib/session.svelte";
  import { t } from "../lib/strings";
  import { theme } from "../lib/theme.svelte";
  import type { FeedItem, Scoreboard, ScreenData, ZoneConfig, ZoneState } from "../lib/types";

  let { id }: { id: string } = $props();

  let screen = $state<ScreenData | null>(null);
  let board = $state<Scoreboard | null>(null);
  let feed = $state<FeedItem[]>([]);
  let error = $state<string | null>(null);
  let now = $state(serverNow());

  async function load(): Promise<void> {
    try {
      [screen, board, feed] = await Promise.all([
        api.get<ScreenData>(`/api/screens/${encodeURIComponent(id)}`),
        api.get<Scoreboard>("/api/scoreboard"),
        api.get<FeedItem[]>("/api/feed"),
      ]);
      error = null;
    } catch (e) {
      error = errorMessage(e);
    }
  }

  $effect(() => poll(load, 20_000));
  $effect(() => {
    void live.ticks.solve;
    void live.ticks.announcement;
    if (untrack(() => screen)) void load();
  });
  $effect(() => {
    const timer = setInterval(() => (now = serverNow()), 1000);
    return () => clearInterval(timer);
  });

  const layout = $derived(screen?.layout ? (theme.data?.layouts[screen.layout] ?? null) : null);
  const remaining = $derived.by(() => {
    const event = session.event;
    if (!event) return null;
    const target = event.phase === "not_started" ? event.schedule.start : event.schedule.end;
    return event.phase === "ended" ? null : new Date(target).getTime() - now;
  });

  function describe(zone: ZoneConfig): { state: ZoneState; progress: number; label: string } {
    const category = screen?.categories.find((c) => c.id === zone.target.category);
    const progress = category?.progress ?? 0;
    const state: ZoneState = progress >= 1 ? "completed" : progress > 0 ? "in-progress" : "available";
    return { state, progress, label: `${zone.label ?? category?.name ?? ""} : ${Math.round(progress * 100)} %` };
  }
</script>

<div class="screen">
  {#if error}
    <p class="error">{error}</p>
  {:else if screen}
    <header class="screen-header">
      <h1>{screen.title}</h1>
      <div class="screen-clock">
        {#if remaining !== null}
          <span class="muted">{t(`phase.${session.event?.phase ?? "running"}`)}</span>
          <strong class="mono">{formatDuration(remaining)}</strong>
        {:else}
          <strong>{t("phase.ended")}</strong>
        {/if}
      </div>
    </header>
    <div class="screen-body">
      <section class="screen-map">
        {#if layout}
          <MapCanvas {layout} {describe} />
        {:else}
          {#each screen.categories as category (category.id)}
            <div class="progress-row">
              <span>{category.name}</span>
              <div class="progress-bar" style:--progress={category.progress} style:--bar-color={category.color ?? "var(--color-accent)"}></div>
            </div>
          {/each}
        {/if}
        <p class="muted">{t("screen.active_teams", { n: screen.active_teams })}</p>
      </section>
      <aside class="screen-side">
        <h2>{t("screen.top")}</h2>
        {#if board?.frozen}<p class="feedback info small">{t("screen.frozen")}</p>{/if}
        <ol class="screen-top">
          {#each (board?.teams ?? []).slice(0, 10) as entry (entry.team_id)}
            <li><span class="rank">{entry.rank}</span><span class="name">{entry.name}</span><strong>{entry.score}</strong></li>
          {/each}
        </ol>
        <h2>{t("screen.feed")}</h2>
        <ul class="screen-feed">
          {#each feed.slice(0, 8) as item (item.kind + item.at)}
            <li>
              <span class="muted mono">{formatTime(item.at, session.event?.timezone)}</span>
              {item.kind === "first_blood"
                ? t("screen.first_blood", { team: item.team, challenge: item.challenge })
                : t("screen.announcement", { title: item.title })}
            </li>
          {/each}
        </ul>
      </aside>
    </div>
  {:else}
    <p class="muted center">{t("loading")}</p>
  {/if}
</div>
