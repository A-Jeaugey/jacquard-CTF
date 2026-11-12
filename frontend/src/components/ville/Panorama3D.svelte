<script lang="ts">
  import { untrack } from "svelte";

  import { creerAllumage } from "../../lib/allumage.svelte";
  import { api } from "../../lib/api";
  import { carteGraphique } from "../../lib/carte-graphique";
  import type { Maquette, QuartierScene } from "../../lib/maquette3d";
  import { session } from "../../lib/session.svelte";
  import type { Scoreboard } from "../../lib/types";
  import { emplacementDe, etatDe, villeDuClassement, type Quartier } from "../../lib/ville";
  import Panorama from "./Panorama.svelte";

  // Lyon la nuit, vue de la Saône, en volume (frontend/DESIGN.md) : les huit immeubles de la
  // maquette alignés sur le quai, les toits lointains, l'eau où les fenêtres se reflètent. C'est
  // le premier plan de la bande-annonce, rendu en temps réel (lib/maquette3d.ts). Comme le
  // panorama à plat, qui le remplace sans carte graphique : décoratif, et une fenêtre s'allume
  // dès qu'une équipe a résolu son défi (classement public).
  let {
    quartiers = null,
    sol = 0.72,
    volume = $bindable(true),
  }: {
    quartiers?: Quartier[] | null;
    /** La hauteur du quai dans l'image (0 en haut, 1 en bas). */
    sol?: number;
    /** Vrai tant que la vue en volume est (ou sera) affichée : la page adapte sa mise en page. */
    volume?: boolean;
  } = $props();

  // Sans ville fournie (pages d'accès), le panorama lit lui-même le classement public.
  let classement = $state<Scoreboard | null>(null);
  $effect(() => {
    if (quartiers) return;
    api
      .get<Scoreboard>("/api/scoreboard")
      .then((c) => (classement = c))
      .catch(() => {
        // décor : en cas d'échec, la ville reste éteinte
      });
  });
  const ville = $derived(quartiers ?? villeDuClassement(session.event?.categories ?? [], classement));

  // L'allumage : à la première visite de la session, les fenêtres allumées s'éclairent une à
  // une dans la ville froide, dans un ordre mêlé. Il attend les premières lumières.
  const brouille = (texte: string): number => [...texte].reduce((h, c) => Math.imul(h ^ c.charCodeAt(0), 0x2c1b3c6d) >>> 0, 7);
  const allumes = $derived(ville.flatMap((q) => q.defis.filter((d) => etatDe(d) === "resolu").map((d) => d.id)));
  const lumieres = creerAllumage({ cle: "jq_allumage_panorama", depart: 400, pas: (n) => Math.min(90, 2000 / n) });
  $effect(() => {
    const ids = allumes;
    untrack(() => lumieres.lancer(ids.length > 0 ? [...ids].sort((a, b) => brouille(a) - brouille(b)) : null));
  });
  $effect(() => () => lumieres.arreter());

  const scene = $derived(
    ville.map(
      (q): QuartierScene => ({
        immeuble: emplacementDe(q),
        categorie: q.categorie.id,
        fenetres: q.defis.flatMap((d, i) => {
          const fen = q.fenetres[i];
          return fen ? [{ id: d.id, etat: lumieres.froides?.has(d.id) ? ("verrouille" as const) : etatDe(d), fen }] : [];
        }),
        fils: [],
        nominal: q.fenetres === q.gabarit.fixe,
        zone: q.gabarit.zone,
      }),
    ),
  );

  const calme = matchMedia("(prefers-reduced-motion: reduce)").matches;
  let toile = $state<HTMLCanvasElement>();
  let maquette = $state.raw<Maquette | null>(null);
  let echec = $state(!carteGraphique());
  $effect(() => {
    volume = !echec;
  });

  $effect(() => {
    const cible = toile;
    if (!cible) return;
    let vivante = true;
    let creee: Maquette | null = null;
    void import("../../lib/maquette3d")
      .then(({ Maquette }) => Maquette.creer(cible, { calme, disposition: "quai", sol: untrack(() => sol) }))
      .then((m) => {
        if (!vivante) {
          m.detruire();
          return;
        }
        creee = m;
        untrack(() => m.ville(scene));
        maquette = m;
      })
      .catch(() => {
        if (vivante) echec = true;
      });
    return () => {
      vivante = false;
      creee?.detruire();
      maquette = null;
    };
  });
  $effect(() => {
    maquette?.ville(scene);
  });
  $effect(() => {
    maquette?.asseoir(sol);
  });

  // La caméra se décale un peu avec le pointeur : les toits lointains glissent derrière le quai.
  function suivre(event: PointerEvent): void {
    if (event.pointerType === "mouse") maquette?.pencher((event.clientX / window.innerWidth) * 2 - 1);
  }
</script>

<svelte:window onpointermove={suivre} />

{#if echec}
  <Panorama quartiers={ville} />
{:else}
  <div class="quai" class:prete={maquette !== null} aria-hidden="true">
    <canvas bind:this={toile}></canvas>
  </div>
{/if}

<style>
  .quai {
    width: 100%;
    height: 100%;
    overflow: hidden;
  }
  canvas {
    display: block;
    width: 100%;
    height: 100%;
    opacity: 0;
    transition: opacity 700ms ease;
  }
  .prete canvas {
    opacity: 1;
  }
</style>
