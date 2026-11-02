<script lang="ts">
  import { api } from "../lib/api";
  import { formatDateTime, poll } from "../lib/format";
  import { session } from "../lib/session.svelte";
  import { t } from "../lib/strings";
  import type { Announcement } from "../lib/types";

  let announcements = $state<Announcement[]>([]);

  $effect(() =>
    poll(async () => {
      announcements = await api.get<Announcement[]>("/api/announcements").catch(() => announcements);
    }, 60_000),
  );

  const event = $derived(session.event);
</script>

{#if event}
  <section class="hero">
    <h1>{event.name}</h1>
    {#if event.tagline}<p class="tagline">{event.tagline}</p>{/if}
    <p class="muted">
      {formatDateTime(event.schedule.start, event.timezone)} → {formatDateTime(event.schedule.end, event.timezone)}
    </p>
    <div class="actions">
      {#if !session.me}
        {#if event.participation.registration !== "closed"}
          <a class="button" href="/register">{t("home.cta.register")}</a>
        {/if}
        <a class="button secondary" href="/login">{t("nav.login")}</a>
      {:else if !session.me.team && session.me.user.role !== "admin"}
        <a class="button" href="/team">{t("home.cta.team")}</a>
      {:else}
        <a class="button" href="/challenges">{t("home.cta.board")}</a>
      {/if}
    </div>
  </section>
{/if}

<section>
  <h2>{t("home.announcements")}</h2>
  {#each announcements as announcement (announcement.id)}
    <article class="card announcement">
      <header>
        <strong>{announcement.title}</strong>
        <span class="muted small">{formatDateTime(announcement.created_at, event?.timezone)}</span>
      </header>
      <!-- HTML assaini côté serveur. -->
      <div class="prose">{@html announcement.body_html}</div>
    </article>
  {:else}
    <p class="muted">{t("home.no_announcements")}</p>
  {/each}
</section>
