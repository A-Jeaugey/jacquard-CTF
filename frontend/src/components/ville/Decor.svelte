<script lang="ts">
  import { session } from "../../lib/session.svelte";
  import { NOMS_RIVIERES, PLAN, PONTS, RIVIERES, villeEteinte } from "../../lib/ville";
  import Immeuble from "./Immeuble.svelte";

  // La ville de nuit tenue par LUMEN : décor de l'accueil et des pages de connexion.
  // Purement illustratif (aria-hidden), sans interaction ni donnée de défi.
  const quartiers = $derived(villeEteinte(session.event?.categories ?? []));
  const pct = (valeur: number, total: number): string => `${(valeur / total) * 100}%`;
  // Le décor est recadré à droite sur le quai du Rhône et à gauche sur le pied de la flèche de
  // Fourvière : la ville touche les bords de la colonne, qu'elle soit à droite ou dessous.
  const GAUCHE = 13;
  const LARGEUR = 585;
  const VUE = LARGEUR - GAUCHE;
</script>

{#if quartiers}
  <div class="decor" aria-hidden="true">
    <svg class="fond" viewBox="{GAUCHE} 0 {VUE} {PLAN.h}" preserveAspectRatio="none" focusable="false">
      {#each RIVIERES as riviere (riviere.points)}
        <polyline class="quai" points={riviere.points} stroke-width={riviere.largeur + 4} />
      {/each}
      {#each RIVIERES as riviere (riviere.points)}
        <polyline class="eau" points={riviere.points} stroke-width={riviere.largeur} />
      {/each}
      {#each PONTS as [x, y, w] (`${x}-${y}`)}
        <rect class="pont" {x} {y} width={w} height="4" />
      {/each}
    </svg>
    {#each NOMS_RIVIERES as riviere (riviere.nom)}
      <span class="riviere" style:left={pct(riviere.x - GAUCHE, VUE)} style:top={pct(riviere.y, PLAN.h)} style:--angle="{riviere.angle}deg"
        >{riviere.nom}</span
      >
    {/each}
    {#each quartiers as q (q.categorie.id)}
      <div class="immeuble" style:left={pct(q.x - GAUCHE, VUE)} style:top={pct(q.y, PLAN.h)} style:width={pct(q.w, VUE)}>
        <Immeuble quartier={q} />
        <span class="nom">{q.categorie.name}</span>
      </div>
    {/each}
  </div>
{/if}

<style>
  .decor {
    position: relative;
    width: 100%;
    aspect-ratio: 572 / 650;
    container-type: inline-size;
  }
  .fond {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    display: block;
  }
  .quai {
    fill: none;
    stroke: var(--lumen);
  }
  .eau {
    fill: none;
    stroke: var(--eau);
  }
  .pont {
    fill: var(--pierre);
  }
  .riviere {
    position: absolute;
    transform: translate(-50%, -50%) rotate(var(--angle));
    font-style: italic;
    color: var(--douce);
    white-space: nowrap;
  }
  .immeuble {
    position: absolute;
    display: flex;
    flex-direction: column;
    align-items: center;
  }
  .nom {
    margin-top: var(--e1);
    font-family: var(--display);
    font-size: 24px;
    line-height: 1;
    white-space: nowrap;
  }
  @container (max-width: 600px) {
    .nom {
      font-size: 21px;
    }
  }
</style>
