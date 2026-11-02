<script lang="ts">
  import { api, ApiError, errorMessage } from "../lib/api";
  import { formatSize } from "../lib/format";
  import { session } from "../lib/session.svelte";
  import { t } from "../lib/strings";
  import type { ChallengeDetail, HintView, SubmitResult } from "../lib/types";

  let { id, onClose, onSolved }: { id: string; onClose: () => void; onSolved: () => void } =
    $props();

  type Feedback = { kind: "ok" | "error" | "info"; text: string };

  let challenge = $state<ChallengeDetail | null>(null);
  let loadError = $state<string | null>(null);
  let flag = $state("");
  let submitting = $state(false);
  let feedback = $state<Feedback | null>(null);
  let rewards = $state<string[]>([]);
  let notifications = $state<string[]>([]);
  let hintError = $state<string | null>(null);
  let shake = $state(false);
  let dialog: HTMLDialogElement;

  const flagPrefix = $derived(session.event?.flag_format?.split("{")[0] ?? "");
  const formatWarning = $derived(
    flag.trim().length > 0 && flagPrefix !== "" && !flag.trim().toLowerCase().startsWith(flagPrefix.toLowerCase()),
  );
  const ended = $derived(session.event?.phase === "ended");
  const isPlayer = $derived(session.me?.user.role !== "admin");

  async function load(): Promise<void> {
    try {
      challenge = await api.get<ChallengeDetail>(`/api/challenges/${encodeURIComponent(id)}`);
    } catch (error) {
      loadError = errorMessage(error);
    }
  }

  function describeRewards(result: Extract<SubmitResult, { status: "correct" }>): string[] {
    const lines: string[] = [];
    if (result.first_blood === 1) lines.push(`🩸 ${t("challenge.first_blood")}`);
    else if (result.first_blood) lines.push(t("challenge.first_blood_rank", { n: result.first_blood }));
    for (const item of result.items) lines.push(`🎁 ${t("challenge.item_obtained", { name: item.name })}`);
    for (const c of result.unlocked.challenges) lines.push(`🔓 ${t("challenge.unlocked_challenge", { name: c.name })}`);
    for (const s of result.unlocked.story) lines.push(`📜 ${t("challenge.unlocked_story", { title: s.title })}`);
    return lines;
  }

  async function submit(event: SubmitEvent): Promise<void> {
    event.preventDefault();
    if (!flag.trim() || submitting) return;
    submitting = true;
    feedback = null;
    try {
      const result = await api.post<SubmitResult>(`/api/challenges/${encodeURIComponent(id)}/submit`, {
        flag: flag.trim(),
      });
      if (result.status === "incorrect") {
        feedback = { kind: "error", text: t("challenge.incorrect") };
        shake = true;
        setTimeout(() => (shake = false), 400);
        return;
      }
      feedback = { kind: result.status === "correct" ? "ok" : "info", text: t(`challenge.${result.status}`) };
      if (result.status === "correct") {
        rewards = describeRewards(result);
        notifications = result.notifications;
      }
      flag = "";
      if (challenge) challenge.solved = true;
      onSolved();
    } catch (error) {
      const retry = error instanceof ApiError ? error.extra.retry_after : undefined;
      feedback = { kind: "error", text: errorMessage(error) + (retry ? ` (${retry} s)` : "") };
    } finally {
      submitting = false;
    }
  }

  async function reveal(hint: HintView): Promise<void> {
    if (hint.cost > 0 && !confirm(t("challenge.hint.confirm", { n: hint.cost }))) return;
    hintError = null;
    try {
      const revealed = await api.post<{ text_html: string }>(
        `/api/challenges/${encodeURIComponent(id)}/hints/${encodeURIComponent(hint.id)}/unlock`,
      );
      hint.unlocked = true;
      hint.text_html = revealed.text_html;
    } catch (error) {
      hintError = errorMessage(error);
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

      {#if challenge.hints.length}
        <h3>{t("challenge.hints")}</h3>
        <ol class="hints">
          {#each challenge.hints as hint, index (hint.id)}
            <li class="hint">
              {#if hint.text_html !== null}
                <div class="prose">{@html hint.text_html}</div>
              {:else}
                <span>{t("challenge.hint", { n: index + 1 })}</span>
                <span class="muted small">
                  {hint.cost > 0 ? t("challenge.hint.cost", { n: hint.cost }) : t("challenge.hint.free")}
                </span>
                {#if !hint.available}
                  <span class="muted small">· {t("challenge.hint.unavailable")}</span>
                {:else if isPlayer && !ended}
                  <button class="small secondary" onclick={() => reveal(hint)}>{t("challenge.hint.reveal")}</button>
                {/if}
              {/if}
            </li>
          {/each}
        </ol>
        {#if hintError}<p class="error small">{hintError}</p>{/if}
      {/if}

      {#if feedback}
        <p class={`feedback ${feedback.kind}`} role="status">{feedback.text}</p>
      {/if}
      {#if rewards.length}
        <ul class="rewards">
          {#each rewards as line (line)}<li>{line}</li>{/each}
        </ul>
      {/if}
      {#each notifications as html, index (index)}
        <!-- Message de l'auteur du défi, assaini côté serveur. -->
        <div class="card prose notification">{@html html}</div>
      {/each}

      {#if challenge.solved}
        {#if !feedback}<p class="feedback ok">✓ {t("challenge.solved_banner")}</p>{/if}
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
    {/if}
  </div>
</dialog>
