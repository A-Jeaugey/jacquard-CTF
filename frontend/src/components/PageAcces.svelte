<script lang="ts">
  import type { Snippet } from "svelte";

  import Decor from "./ville/Decor.svelte";

  // Mise en page des pages d'accès (connexion, inscription, page introuvable, équipe sans
  // équipe) : le contenu à gauche sur 480 px au plus, la ville éteinte à droite (dessous sur
  // petit écran).
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
  .contenu {
    max-width: 480px;
  }
  .illustration {
    position: sticky;
    top: var(--e5);
    justify-self: end;
    width: 100%;
    max-width: 640px;
  }
  /* Sous 900 px, la ville passe sous le contenu, comme sur l'accueil. */
  @media (max-width: 900px) {
    .acces {
      grid-template-columns: minmax(0, 1fr);
      row-gap: var(--e7);
      padding-top: var(--e5);
    }
    .illustration {
      position: static;
      justify-self: start;
      max-width: 520px;
    }
  }
</style>
