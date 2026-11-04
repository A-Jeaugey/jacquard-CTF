<script lang="ts">
  import type { Snippet } from "svelte";

  import Decor from "./ville/Decor.svelte";

  // Mise en page des pages d'accès (connexion, inscription, équipe sans équipe) : le contenu
  // à gauche, la ville éteinte à droite (masquée sur petit écran).
  let { children }: { children: Snippet } = $props();
</script>

<div class="acces">
  <div class="contenu">{@render children()}</div>
  <div class="illustration"><Decor /></div>
</div>

<style>
  .acces {
    display: grid;
    grid-template-columns: minmax(0, 480px) minmax(0, 1fr);
    gap: var(--e8);
    align-items: start;
    padding: var(--e6) var(--gouttiere) var(--e8);
  }
  .illustration {
    position: sticky;
    top: var(--e5);
    max-width: 600px;
  }
  @media (max-width: 900px) {
    .acces {
      grid-template-columns: minmax(0, 1fr);
      padding-top: var(--e5);
    }
    .illustration {
      display: none;
    }
  }
</style>
