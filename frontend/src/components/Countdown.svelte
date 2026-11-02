<script lang="ts">
  import { formatDuration } from "../lib/format";
  import { refreshEvent, serverNow, session } from "../lib/session.svelte";
  import { t } from "../lib/strings";

  let now = $state(serverNow());

  $effect(() => {
    const timer = setInterval(() => (now = serverNow()), 1000);
    return () => clearInterval(timer);
  });

  const target = $derived.by(() => {
    const event = session.event;
    if (!event) return null;
    if (event.phase === "not_started") return new Date(event.schedule.start).getTime();
    if (event.phase === "running") return new Date(event.schedule.end).getTime();
    return null;
  });

  // Quand une échéance est franchie, on recharge l'état de l'événement (une seule fois).
  let refreshedFor: number | null = null;
  $effect(() => {
    if (target !== null && now >= target && refreshedFor !== target) {
      refreshedFor = target;
      void refreshEvent();
    }
  });
</script>

{#if session.event}
  <div class="countdown" aria-live="off">
    {#if session.event.phase === "ended"}
      <span>{t("phase.ended")}</span>
    {:else if target !== null}
      <span class="muted">{t(`phase.${session.event.phase}`)}</span>
      <strong class="mono">{formatDuration(target - now)}</strong>
    {/if}
    {#if session.event.frozen}
      <span class="badge warn">{t("phase.frozen")}</span>
    {/if}
  </div>
{/if}
