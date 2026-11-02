<script lang="ts">
  import { api, ApiError, errorMessage } from "../lib/api";
  import { formatSize } from "../lib/format";
  import { session } from "../lib/session.svelte";
  import { t } from "../lib/strings";
  import type { ChallengeDetail, SubmitStatus } from "../lib/types";

  let { id, onClose, onSolved }: { id: string; onClose: () => void; onSolved: () => void } =
    $props();

  let challenge = $state<ChallengeDetail | null>(null);
  let loadError = $state<string | null>(null);
  let flag = $state("");
  let submitting = $state(false);
  let feedback = $state<{ kind: "ok" | "error" | "info"; text: string } | null>(null);
  let shake = $state(false);
  let dialog: HTMLDialogElement;

  const flagPrefix = $derived(session.event?.flag_format?.split("{")[0] ?? "");
  const formatWarning = $derived(
    flag.trim().length > 0 && flagPrefix !== "" && !flag.trim().toLowerCase().startsWith(flagPrefix.toLowerCase()),
  );
  const ended = $derived(session.event?.phase === "ended");

  async function load(): Promise<void> {
    try {
      challenge = await api.get<ChallengeDetail>(`/api/challenges/${encodeURIComponent(id)}`);
    } catch (error) {
      loadError = errorMessage(error);
    }
  }

  async function submit(event: SubmitEvent): Promise<void> {
    event.preventDefault();
    if (!flag.trim() || submitting) return;
    submitting = true;
    feedback = null;
    try {
      const { status } = await api.post<{ status: SubmitStatus }>(
        `/api/challenges/${encodeURIComponent(id)}/submit`,
        { flag: flag.trim() },
      );
      if (status === "correct" || status === "already_solved") {
        feedback = { kind: status === "correct" ? "ok" : "info", text: t(`challenge.${status}`) };
        flag = "";
        if (challenge) challenge.solved = true;
        onSolved();
      } else {
        feedback = { kind: "error", text: t("challenge.incorrect") };
        shake = true;
        setTimeout(() => (shake = false), 400);
      }
    } catch (error) {
      const retry = error instanceof ApiError ? error.extra.retry_after : undefined;
      feedback = { kind: "error", text: errorMessage(error) + (retry ? ` (${retry} s)` : "") };
    } finally {
      submitting = false;
    }
  }

  $effect(() => {
    dialog.showModal();
    void load();
  });
</script>

<dialog
  bind:this={dialog}
  class="modal"
  onclose={onClose}
  onclick={(e) => {
    if (e.target === dialog) dialog.close();
  }}
>
  <div class="modal-body">
    <button class="modal-close link" aria-label={t("challenge.close")} onclick={() => dialog.close()}>✕</button>
    {#if loadError}
      <p class="error">{loadError}</p>
    {:else if !challenge}
      <p class="muted">{t("loading")}</p>
    {:else}
      <header>
        <h2>{challenge.name}</h2>
        <p class="muted">
          {t("board.points", { n: challenge.value })} · {t("board.solves", { n: challenge.solves })}
          {#if challenge.difficulty} · {challenge.difficulty}{/if}
        </p>
        {#if challenge.authors.length}
          <p class="muted small">{t("challenge.authors", { names: challenge.authors.join(", ") })}</p>
        {/if}
      </header>

      <!-- HTML produit et assaini par le serveur (jacquard/markdown.py). -->
      <div class="prose">{@html challenge.description_html}</div>

      {#if challenge.connection}
        <h3>{t("challenge.connection")}</h3>
        <pre class="connection">{challenge.connection}</pre>
      {/if}

      {#if challenge.files.length}
        <h3>{t("challenge.files")}</h3>
        <ul class="files">
          {#each challenge.files as file (file.id)}
            <li>
              <a href={`/api/files/${file.id}`} download={file.name}>{file.name}</a>
              <span class="muted small">{formatSize(file.size)}</span>
            </li>
          {/each}
        </ul>
      {/if}

      {#if challenge.solved}
        <p class="feedback ok">✓ {t("challenge.solved_banner")}</p>
      {:else if ended}
        <p class="feedback info">{t("challenge.ended")}</p>
      {:else}
        <form class="flag-form" class:shake onsubmit={submit}>
          <label class="sr-only" for="flag">{t("challenge.flag")}</label>
          <input
            id="flag"
            class="mono"
            autocomplete="off"
            spellcheck="false"
            maxlength="512"
            placeholder={session.event?.flag_format ?? t("challenge.flag")}
            bind:value={flag}
          />
          <button type="submit" disabled={submitting || !flag.trim()}>{t("challenge.submit")}</button>
        </form>
        {#if formatWarning && session.event?.flag_format}
          <p class="muted small">{t("challenge.format_hint", { format: session.event.flag_format })}</p>
        {/if}
      {/if}

      {#if feedback}
        <p class={`feedback ${feedback.kind}`} role="status">{feedback.text}</p>
      {/if}
    {/if}
  </div>
</dialog>
