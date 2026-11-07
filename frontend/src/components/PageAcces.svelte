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
    padding: var(--e6) var(--gouttiere) 0;
  }
  @media (min-width: 1100px) {
    /* L'écran moins l'en-tête, sur une ligne à partir de 1100 px (64 px et son filet) : la
       ville se pose au bas de l'écran. */
    .acces {
      min-height: calc(100svh - 65px);
    }
  }
  .contenu {
    max-width: 480px;
  }
  /* Le formulaire passe avant : la ville prend la hauteur qui reste sous lui (environ 640 px
     d'en-tête, de formulaire et de marges ; le panorama mesure 298 unités de haut), sans
     dépasser sa taille de l'accueil. Sur un écran bas, elle passe sous le formulaire. */
  .acces .panorama-zone :global(.panorama) {
    --u: clamp(0.55px, min(0.03vw + 0.55px, (100svh - 640px) / 298), 1.4px);
  }
  .panorama-zone {
    margin-top: auto;
    padding-top: var(--e5);
    width: 100vw;
    margin-left: calc(50% - 50vw);
  }
  @media (max-width: 640px) {
    .acces {
      padding-top: var(--e5);
    }
  }
</style>
