<script lang="ts">
  // Layout « grid » : une colonne par catégorie, façon Jeopardy.
  import { t } from "../../lib/strings";
  import type { BoardData } from "../../lib/types";

  let { data, onOpen }: { data: BoardData; onOpen: (id: string) => void } = $props();

  const columns = $derived(
    data.categories
      .map((category) => ({
        category,
        challenges: data.challenges.filter((c) => c.category === category.id),
      }))
      .filter((column) => column.challenges.length > 0),
  );
</script>

<div class="grid-board">
  {#each columns as { category, challenges } (category.id)}
    <section class="column" style:--category-color={category.color ?? "var(--color-accent)"}>
      <h2 class="column-title">
        {category.name}
        <span class="muted small">{challenges.filter((c) => c.solved).length}/{challenges.length}</span>
      </h2>
      {#each challenges as challenge (challenge.id)}
        {#if challenge.locked}
          <div class="challenge-card locked">
            <span class="challenge-name">🔒 {challenge.name}</span>
            <span class="muted small">{challenge.locked_message ?? t("board.locked")}</span>
          </div>
        {:else}
        <button class="challenge-card" class:solved={challenge.solved} onclick={() => onOpen(challenge.id)}>
          <span class="challenge-name">{challenge.name}</span>
          <span class="challenge-meta">
            <strong>{t("board.points", { n: challenge.value })}</strong>
            {#if challenge.difficulty}<span class="badge">{challenge.difficulty}</span>{/if}
          </span>
          <span class="muted small">
            {challenge.solved ? `✓ ${t("board.solved")}` : t("board.solves", { n: challenge.solves })}
          </span>
        </button>
        {/if}
      {/each}
    </section>
  {/each}
</div>
