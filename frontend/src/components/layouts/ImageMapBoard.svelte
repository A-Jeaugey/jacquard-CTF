<script lang="ts">
  // Layout « image-map » : carte du pack dont les zones reflètent la progression de
  // l'équipe. Cliquer sur une zone filtre la grille affichée en dessous.
  import { t } from "../../lib/strings";
  import type { BoardData, ThemeLayout, ZoneConfig, ZoneState } from "../../lib/types";
  import MapCanvas from "../MapCanvas.svelte";
  import GridBoard from "./GridBoard.svelte";

  let { data, onOpen, layout }: { data: BoardData; onOpen: (id: string) => void; layout: ThemeLayout } = $props();

  let selected = $state<string | null>(null);

  function challengesOf(zone: ZoneConfig) {
    const { category, challenge } = zone.target;
    return data.challenges.filter((c) => (category ? c.category === category : c.id === challenge));
  }

  function describe(zone: ZoneConfig): { state: ZoneState; progress: number; label: string; count: string } {
    const items = challengesOf(zone);
    const solved = items.filter((c) => c.solved).length;
    const unlocked = items.filter((c) => !c.locked).length;
    const state: ZoneState =
      items.length === 0 || unlocked === 0
        ? "locked"
        : solved === items.length
          ? "completed"
          : solved > 0
            ? "in-progress"
            : "available";
    const name =
      zone.label ??
      (zone.target.category
        ? (data.categories.find((c) => c.id === zone.target.category)?.name ?? zone.target.category)
        : (items[0]?.name ?? t("board.locked")));
    const count = items.length ? `${solved}/${items.length}` : "—";
    return { state, progress: items.length ? solved / items.length : 0, label: `${name} : ${count}`, count };
  }

  const zoneOf = $derived(layout.zones.find((z) => z.element === selected) ?? null);
  const filtered = $derived<BoardData>(
    zoneOf ? { ...data, challenges: challengesOf(zoneOf) } : data,
  );

  function toggle(element: string): void {
    selected = selected === element ? null : element;
  }
</script>

<div class="map-board">
  <MapCanvas {layout} {describe} {selected} onSelect={toggle} />
  <div class="zone-chips" role="group" aria-label={t("board.zones")}>
    {#each layout.zones as zone (zone.element)}
      {@const view = describe(zone)}
      <button
        class={`zone-chip is-${view.state}`}
        class:active={selected === zone.element}
        aria-pressed={selected === zone.element}
        onclick={() => toggle(zone.element)}
      >
        {view.label}
      </button>
    {/each}
  </div>
  <p class="muted small">{zoneOf ? t("board.zone_selected") : t("board.zone_hint")}</p>
</div>

<GridBoard data={filtered} {onOpen} />
