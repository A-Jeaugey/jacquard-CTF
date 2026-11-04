<script lang="ts">
  import { formatDuration } from "../lib/format";
  import { refreshEvent, serverNow, session } from "../lib/session.svelte";
  import { t } from "../lib/strings";

  // Compte à rebours : la valeur en LUMEN, le libellé après (« 01:47:04 avant la fin »).
  let now = $state(serverNow());

  $effect(() => {
    const timer = setInterval(() => (now = serverNow()), 1000);
    return () => clearInterval(timer);
  });

  const echeance = $derived.by(() => {
    const event = session.event;
    if (!event) return null;
    if (event.phase === "not_started") return new Date(event.schedule.start).getTime();
    if (event.phase === "running") return new Date(event.schedule.end).getTime();
    return null;
  });

  // Une échéance franchie : on recharge l'état de l'événement, une seule fois.
  let rechargePour: number | null = null;
  $effect(() => {
    if (echeance !== null && now >= echeance && rechargePour !== echeance) {
      rechargePour = echeance;
      void refreshEvent();
    }
  });
</script>

{#if session.event}
  <p class="compte">
    {#if session.event.phase === "ended"}
      <span class="libelle">{t("phase.ended")}</span>
    {:else if echeance !== null}
      <span class="valeur tnum">{formatDuration(echeance - now)}</span>
      <span class="libelle">{t(`phase.${session.event.phase}`)}</span>
    {/if}
    {#if session.event.frozen}
      <span class="libelle gel">{t("phase.frozen")}</span>
    {/if}
  </p>
{/if}

<style>
  .compte {
    margin-left: auto;
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    justify-content: flex-end;
    column-gap: var(--e2);
  }
  .valeur {
    font-size: 21px;
    font-weight: 700;
    color: var(--lumen);
  }
  .libelle {
    font-size: var(--t-meta);
    color: var(--douce);
  }
  .gel {
    flex-basis: 100%;
    text-align: right;
  }
  @media (max-width: 1099px) {
    .compte {
      margin: 0;
      padding-left: var(--e4);
      flex-direction: column;
      align-items: flex-end;
      line-height: 1.25;
    }
  }
</style>
