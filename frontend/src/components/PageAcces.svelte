<script lang="ts">
  import type { Snippet } from "svelte";

  import Panorama from "./ville/Panorama.svelte";

  // Mise en page des pages d'accès (connexion, inscription, page introuvable, équipe sans
  // équipe) : le contenu en haut à gauche sur 480 px au plus, Lyon la nuit au pied de l'écran,
  // sur toute la largeur, comme sur l'accueil.
  let { children }: { children: Snippet } = $props();
</script>

<div class="acces">
  <div class="contenu">{@render children()}</div>
  <div class="panorama-zone"><Panorama /></div>
</div>

<style>
  .acces {
    display: flex;
    flex-direction: column;
    /* L'écran moins l'en-tête : la ville se pose au bas de l'écran, sous le contenu. */
    min-height: calc(100svh - 65px);
    padding: var(--e6) var(--gouttiere) 0;
  }
  .contenu {
    max-width: 480px;
  }
  /* Le formulaire passe avant : une ville un peu plus petite que sur l'accueil. */
  .acces .panorama-zone :global(.panorama) {
    --u: clamp(0.78px, 0.03vw + 0.55px, 1.05px);
  }
  .panorama-zone {
    margin-top: auto;
    padding-top: var(--e7);
    width: 100vw;
    margin-left: calc(50% - 50vw);
  }
  @media (max-width: 640px) {
    .acces {
      padding-top: var(--e5);
    }
  }
</style>
