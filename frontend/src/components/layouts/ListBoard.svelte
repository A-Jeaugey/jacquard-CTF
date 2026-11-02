<script lang="ts">
  // Layout « list » : tous les défis dans un tableau triable par colonne.
  import { t } from "../../lib/strings";
  import type { BoardData, ChallengeSummary } from "../../lib/types";

  let { data, onOpen }: { data: BoardData; onOpen: (id: string) => void } = $props();

  type Key = "category" | "name" | "value" | "solves";
  let sortKey = $state<Key>("category");
  let ascending = $state(true);

  const categoryName = (id: string) => data.categories.find((c) => c.id === id)?.name ?? id;
  const rows = $derived(
    [...data.challenges].sort((a: ChallengeSummary, b: ChallengeSummary) => {
      const va = sortKey === "category" ? categoryName(a.category) : a[sortKey];
      const vb = sortKey === "category" ? categoryName(b.category) : b[sortKey];
      const order = typeof va === "number" && typeof vb === "number" ? va - vb : String(va).localeCompare(String(vb), "fr");
      return ascending ? order : -order;
    }),
  );

  function sortBy(key: Key): void {
    ascending = sortKey === key ? !ascending : true;
    sortKey = key;
  }
</script>

<div class="table-wrap">
  <table class="list-board">
    <thead>
      <tr>
        {#each [["category", "list.category"], ["name", "list.name"], ["value", "list.value"], ["solves", "list.solves"]] as const as [key, label] (key)}
          <th><button class="link" onclick={() => sortBy(key)}>{t(label)}{sortKey === key ? (ascending ? " ▲" : " ▼") : ""}</button></th>
        {/each}
        <th>{t("list.status")}</th>
      </tr>
    </thead>
    <tbody>
      {#each rows as c (c.id)}
        <tr class:solved={c.solved}>
          <td>{categoryName(c.category)}</td>
          <td>
            {#if c.locked}🔒 {c.name}{:else}<button class="link strong" onclick={() => onOpen(c.id)}>{c.name}</button>{/if}
          </td>
          <td class="num">{c.value}</td>
          <td class="num">{c.solves}</td>
          <td>{c.solved ? `✓ ${t("board.solved")}` : c.locked ? (c.locked_message ?? t("board.locked")) : ""}</td>
        </tr>
      {/each}
    </tbody>
  </table>
</div>
