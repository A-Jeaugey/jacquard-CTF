<script lang="ts">
  import type { Snippet } from "svelte";

  import { carteGraphique } from "../lib/carte-graphique";
  import Panorama3D from "./ville/Panorama3D.svelte";

  // Mise en page des pages d'accès (connexion, inscription, page introuvable, équipe sans
  // équipe) : le contenu en haut à gauche sur 480 px au plus, Lyon la nuit au pied de l'écran,
  // sur toute la largeur, comme sur l'accueil.
  let { children }: { children: Snippet } = $props();

  // Le quai en volume (frontend/DESIGN.md) : derrière le formulaire, sur tout l'écran.
  let volume = $state(carteGraphique());
</script>

<div class="acces" class:en-volume={volume}>
  <div class="contenu">{@render children()}</div>
  <div class="panorama-zone"><Panorama3D sol={0.82} bind:volume /></div>
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
    /* En volume : le quai et la Saône occupent toute la page, sous le formulaire. */
    .acces.en-volume {
      position: relative;
    }
    .acces.en-volume .contenu {
      position: relative;
      z-index: 1;
    }
    .acces.en-volume .panorama-zone {
      position: absolute;
      top: 0;
      bottom: 0;
      left: 0;
      height: auto;
      padding-top: 0;
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
  /* En volume, sur un écran étroit : un bloc sous le formulaire. */
  @media (max-width: 1099px) {
    .acces.en-volume .panorama-zone {
      height: clamp(240px, 60vw, 420px);
    }
  }
  @media (max-width: 640px) {
    .acces {
      padding-top: var(--e5);
    }
  }
</style>
