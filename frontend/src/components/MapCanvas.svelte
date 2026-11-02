<script lang="ts">
  // Affiche le SVG d'un layout image-map et applique à chaque zone son état
  // (classes is-locked, is-available, is-in-progress, is-completed) et sa progression
  // (variable CSS --progress entre 0 et 1). Le rendu visuel est laissé au thème.
  import { sanitizeSvg } from "../lib/theme.svelte";
  import type { ThemeLayout, ZoneConfig, ZoneState } from "../lib/types";

  interface ZoneView {
    state: ZoneState;
    progress: number;
    label: string;
  }

  let {
    layout,
    describe,
    selected = null,
    onSelect,
  }: {
    layout: ThemeLayout;
    describe: (zone: ZoneConfig) => ZoneView;
    selected?: string | null;
    onSelect?: (element: string) => void;
  } = $props();

  let svg = $state("");
  let container: HTMLDivElement;

  $effect(() => {
    const url = layout.background_url;
    if (!url) return;
    let cancelled = false;
    fetch(url, { credentials: "same-origin" })
      .then((r) => (r.ok ? r.text() : ""))
      .then((text) => {
        if (!cancelled) svg = sanitizeSvg(text);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  });

  $effect(() => {
    if (!svg || !container) return;
    const cleanups: (() => void)[] = [];
    for (const zone of layout.zones) {
      const element = container.querySelector<SVGElement>(zone.element);
      if (!element) continue;
      const view = describe(zone);
      element.classList.add("map-zone");
      for (const state of ["locked", "available", "in-progress", "completed"]) {
        element.classList.toggle(`is-${state}`, view.state === state);
      }
      element.classList.toggle("is-selected", selected === zone.element);
      element.style.setProperty("--progress", view.progress.toFixed(3));
      element.setAttribute("aria-label", view.label);
      if (onSelect) {
        element.setAttribute("tabindex", "0");
        element.setAttribute("role", "button");
        const select = () => onSelect(zone.element);
        const key = (e: KeyboardEvent) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            select();
          }
        };
        element.addEventListener("click", select);
        element.addEventListener("keydown", key);
        cleanups.push(() => {
          element.removeEventListener("click", select);
          element.removeEventListener("keydown", key);
        });
      }
    }
    return () => cleanups.forEach((c) => c());
  });
</script>

<div class="map-canvas" bind:this={container}>
  <!-- SVG du pack, validé à l'import puis nettoyé par sanitizeSvg. -->
  {@html svg}
</div>
