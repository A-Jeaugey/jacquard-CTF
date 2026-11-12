<script lang="ts">
  import { untrack, type Snippet } from "svelte";

  import { creerAllumage } from "../../lib/allumage.svelte";
  import { carteGraphique } from "../../lib/carte-graphique";
  import type { Maquette, Marges, QuartierScene, Reperes } from "../../lib/maquette3d";
  import { t } from "../../lib/strings";
  import { typo } from "../../lib/typo";
  import { emplacementDe, etatDe, fil, pointsDuFil, type Quartier } from "../../lib/ville";
  import Ville from "./Ville.svelte";

  // La ville en volume (frontend/DESIGN.md) : la maquette du plan de Lyon, rendue en temps réel
  // (lib/maquette3d.ts). La scène est un décor ; par-dessus, chaque immeuble garde son bouton et
  // son nom, comme sur le plan à plat. Sans carte graphique, ou si la maquette ne se charge
  // pas, le plan à plat (Ville.svelte) prend sa place.
  let {
    quartiers,
    choisi = null,
    ouvert = null,
    allumage = null,
    survol = null,
    degagement = { haut: 0, droite: 0, bas: 0, gauche: 0 },
    aPlat = false,
    volume = $bindable(true),
    decor = false,
    ronde = false,
    nuit = false,
    repli,
    onChoisir,
    onOuvrir,
    onSurvol,
  }: {
    quartiers: Quartier[];
    /** Catégorie choisie (filtre) : la caméra s'en approche. */
    choisi?: string | null;
    /** Défi ouvert dans le panneau : la caméra s'approche de sa fenêtre, qui est cernée. */
    ouvert?: string | null;
    /** Défis résolus dans l'ordre réel des résolutions, pour l'allumage ; `null` tant que la
     * progression de l'équipe n'est pas chargée. */
    allumage?: string[] | null;
    /** Défi survolé dans la liste : sa fenêtre se cerne sur la maquette. */
    survol?: string | null;
    /** La place prise par l'interface au-dessus de la scène, de chaque côté (pixels). */
    degagement?: Marges;
    /** Le joueur préfère le plan à plat. */
    aPlat?: boolean;
    /** Vrai tant que la maquette est (ou sera) affichée ; faux si le plan à plat la remplace.
     * La page adapte sa mise en page. */
    volume?: boolean;
    /** Décor sans interaction (grand écran) : ni boutons ni raccourcis, seulement les noms. */
    decor?: boolean;
    /** La maquette tourne lentement d'elle-même. */
    ronde?: boolean;
    /** Les fenêtres non résolues sont éteintes (sombres) au lieu d'être tenues par LUMEN. */
    nuit?: boolean;
    /** Ce qui remplace la maquette quand elle ne peut pas s'afficher (par défaut : le plan à plat). */
    repli?: Snippet;
    onChoisir: (categorie: string) => void;
    onOuvrir?: (event: MouseEvent, defi: string) => void;
    onSurvol?: (defi: string | null) => void;
  } = $props();

  const calme = matchMedia("(prefers-reduced-motion: reduce)").matches;
  let toile = $state<HTMLCanvasElement>();
  let maquette = $state.raw<Maquette | null>(null);
  let echec = $state(!carteGraphique());
  let reperes = $state.raw<Reperes>({ quartiers: {}, fenetres: {} });
  let taille = $state({ w: 0, h: 0 });

  const quartierEnAvant = $derived(
    (ouvert ? quartiers.find((q) => q.defis.some((d) => d.id === ouvert)) : undefined) ?? quartiers.find((q) => q.categorie.id === choisi) ?? null,
  );
  const enAvant = $derived(quartierEnAvant?.categorie.id ?? null);

  $effect(() => {
    volume = !(echec || aPlat);
  });

  const lumieres = creerAllumage();
  $effect(() => {
    const ordre = allumage;
    untrack(() => lumieres.lancer(ordre));
  });
  $effect(() => () => lumieres.arreter());

  // Ce que la scène doit montrer : une fenêtre par défi, et le fil qui les relie.
  const scene = $derived(
    quartiers.map((q): QuartierScene => {
      const froid = (id: string): boolean => lumieres.froides?.has(id) ?? false;
      return {
        immeuble: emplacementDe(q),
        categorie: q.categorie.id,
        fenetres: q.defis.flatMap((d, i) => {
          const fen = q.fenetres[i];
          return fen ? [{ id: d.id, etat: froid(d.id) ? ("verrouille" as const) : etatDe(d), fen, eteinte: nuit }] : [];
        }),
        fils: (decor ? [] : fil(q)).map((troncon) => ({
          vers: troncon.vers,
          etat: froid(troncon.vers) ? ("verrouille" as const) : troncon.etat,
          points: pointsDuFil(troncon.d),
        })),
        nominal: q.fenetres === q.gabarit.fixe,
        zone: q.gabarit.zone,
      };
    }),
  );

  $effect(() => {
    const cible = toile;
    if (!cible || aPlat) return;
    let vivante = true;
    let creee: Maquette | null = null;
    void import("../../lib/maquette3d")
      .then(({ Maquette }) => Maquette.creer(cible, { calme, ronde, surReperes: (r) => (reperes = r) }))
      .then((m) => {
        if (!vivante) {
          m.detruire();
          return;
        }
        creee = m;
        untrack(() => {
          m.degager(degagement);
          m.ville(scene);
          m.viser({ quartier: enAvant, defi: ouvert }, true);
        });
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
    maquette?.viser({ quartier: enAvant, defi: ouvert });
  });
  $effect(() => {
    maquette?.degager(degagement);
  });
  $effect(() => {
    maquette?.survoler(survol);
  });

  // Glisser sur la scène fait tourner la maquette. Au-delà de quelques pixels, le geste n'est
  // plus un clic : l'immeuble sous le pointeur n'est pas choisi.
  let geste: { id: number; x: number; y: number; glisse: boolean } | null = null;
  let clicAnnule = false;
  function appuyer(event: PointerEvent): void {
    if (event.button !== 0 || !maquette) return;
    geste = { id: event.pointerId, x: event.clientX, y: event.clientY, glisse: false };
  }
  function glisser(event: PointerEvent): void {
    if (!geste || event.pointerId !== geste.id || !maquette) return;
    const dx = event.clientX - geste.x;
    const dy = event.clientY - geste.y;
    if (!geste.glisse && Math.hypot(dx, dy) < 6) return;
    geste.glisse = true;
    geste.x = event.clientX;
    geste.y = event.clientY;
    maquette.tourner(-dx * 0.005, dy * 0.003);
  }
  function relacher(event: PointerEvent): void {
    if (!geste || event.pointerId !== geste.id) return;
    clicAnnule = geste.glisse;
    geste = null;
    if (clicAnnule) setTimeout(() => (clicAnnule = false), 0);
  }
  function filtrerClic(event: MouseEvent): void {
    if (!clicAnnule) return;
    event.preventDefault();
    event.stopPropagation();
  }

  // Le nom d'un immeuble : au-dessus de lui pour la rangée du nord, à ses pieds pour les autres
  // (au-dessus, il tomberait sur l'immeuble de derrière).
  const AU_DESSUS = new Set(["croix-rousse", "fourviere", "part-dieu"]);
  function nomVisible(r: Reperes["quartiers"][string], auDessus: boolean): boolean {
    const nx = auDessus ? r.x + r.w / 2 : r.pied.x;
    const ny = auDessus ? r.y - 24 : r.pied.y;
    if (nx < degagement.gauche + 40 || nx > taille.w - degagement.droite - 40 || ny < degagement.haut || ny > taille.h - degagement.bas - 16) return false;
    // Ni sur l'immeuble choisi, quand un voisin dépasse derrière lui.
    const choisi = enAvant ? reperes.quartiers[enAvant] : undefined;
    return !choisi || nx < choisi.x || nx > choisi.x + choisi.w || ny < choisi.y || ny > choisi.y + choisi.h;
  }
  const px = (valeur: number): string => `${Math.round(valeur * 10) / 10}px`;
  const borne = (valeur: number, min: number, max: number): number => Math.min(Math.max(valeur, min), max);
</script>

{#if echec || aPlat}
  {#if repli}{@render repli()}{:else}<Ville {quartiers} {choisi} {ouvert} {allumage} {onChoisir} />{/if}
{:else if decor}
  <div class="carte maquette decor" class:prete={maquette !== null} bind:clientWidth={taille.w} bind:clientHeight={taille.h}>
    <canvas bind:this={toile}></canvas>
    {#each quartiers as q (q.categorie.id)}
      {@const r = reperes.quartiers[q.categorie.id]}
      {#if r}
        <span class="nom au-dessus" style:left={px(r.x + r.w / 2)} style:top={px(r.y)} style:z-index={Math.max(1, Math.round(2000 - r.profondeur * 4))}
          >{q.categorie.name}</span
        >
      {/if}
    {/each}
  </div>
{:else}
  <!-- svelte-ignore a11y_no_static_element_interactions : le glisser fait tourner la scène à la
       souris ; le clavier a les boutons des quartiers et la liste des défis. -->
  <div
    class="carte maquette"
    class:prete={maquette !== null}
    class:en-avant={enAvant !== null}
    bind:clientWidth={taille.w}
    bind:clientHeight={taille.h}
    onpointerdown={appuyer}
    onpointermove={glisser}
    onpointerup={relacher}
    onpointercancel={relacher}
    onclickcapture={filtrerClic}
  >
    <canvas bind:this={toile} aria-hidden="true"></canvas>
    {#each quartiers as q (q.categorie.id)}
      {@const r = reperes.quartiers[q.categorie.id]}
      {@const avance = enAvant === q.categorie.id}
      {@const x = r ? borne(r.x, 0, Math.max(0, taille.w - 44)) : 0}
      {@const y = r ? borne(r.y, 0, Math.max(0, taille.h - 44)) : 0}
      <button
        type="button"
        class="quartier"
        class:avance
        class:hors-champ={!r || r.x + r.w < 0 || r.x > taille.w || r.y + r.h < 0 || r.y > taille.h}
        data-categorie={q.categorie.id}
        aria-pressed={choisi === q.categorie.id}
        aria-label={t("board.district_label", { name: q.categorie.name, n: q.resolus, total: q.defis.length })}
        style:left={px(x)}
        style:top={px(y)}
        style:width={px(r ? Math.max(44, Math.min(r.x + r.w, taille.w) - x) : 44)}
        style:height={px(r ? Math.max(44, Math.min(r.y + r.h, taille.h) - y) : 44)}
        style:z-index={r ? Math.max(1, Math.round(2000 - r.profondeur * 4)) : 1}
        onclick={() => onChoisir(q.categorie.id)}
      >
        <!-- L'état de chaque fenêtre, pour les outils qui lisent la page (comme le plan à plat). -->
        {#each q.defis as d (d.id)}<span class="fen" data-etat={etatDe(d)} hidden></span>{/each}
        <!-- Pas de nom sous l'interface (colonnes de texte, en-tête), ni pour l'immeuble choisi :
             son nom est le titre de la liste. -->
        {#if r && !avance && nomVisible(r, AU_DESSUS.has(emplacementDe(q)))}
          <span
            class="nom"
            class:au-dessus={AU_DESSUS.has(emplacementDe(q))}
            style:left={px(AU_DESSUS.has(emplacementDe(q)) ? r.x + r.w / 2 - x : r.pied.x - x)}
            style:top={px(AU_DESSUS.has(emplacementDe(q)) ? r.y - y : r.pied.y - y)}>{q.categorie.name}</span
          >
        {/if}
      </button>
    {/each}
    <!-- Les fenêtres du quartier choisi : des raccourcis à la souris vers les défis. La liste
         porte les mêmes liens pour le clavier et les lecteurs d'écran. -->
    {#if quartierEnAvant}
      {#each quartierEnAvant.defis as d (d.id)}
        {@const r = reperes.fenetres[d.id]}
        {@const etat = etatDe(d)}
        {#if r}
          {#if etat === "verrouille"}
            <span
              class="fenetre"
              aria-hidden="true"
              style:left={px(r.x)}
              style:top={px(r.y)}
              style:width={px(r.w)}
              style:height={px(r.h)}
              onpointerenter={() => onSurvol?.(d.id)}
              onpointerleave={() => onSurvol?.(null)}><span class="fen-nom">{typo(d.name)}</span></span
            >
          {:else}
            <a
              class="fenetre ouvrable"
              href="/challenges?defi={encodeURIComponent(d.id)}"
              tabindex="-1"
              aria-hidden="true"
              style:left={px(r.x)}
              style:top={px(r.y)}
              style:width={px(r.w)}
              style:height={px(r.h)}
              onclick={(event) => onOuvrir?.(event, d.id)}
              onpointerenter={() => onSurvol?.(d.id)}
              onpointerleave={() => onSurvol?.(null)}><span class="fen-nom">{typo(d.name)}</span></a
            >
          {/if}
        {/if}
      {/each}
    {/if}
  </div>
{/if}

<style>
  .maquette {
    position: relative;
    width: 100%;
    height: 100%;
    overflow: hidden;
    /* Sur un écran tactile, glisser de côté tourne la maquette ; de haut en bas, la page défile. */
    touch-action: pan-y;
    cursor: grab;
    user-select: none;
    -webkit-user-select: none;
  }
  .maquette:active {
    cursor: grabbing;
  }
  .maquette.decor {
    cursor: auto;
    touch-action: auto;
  }
  canvas {
    display: block;
    width: 100%;
    height: 100%;
    opacity: 0;
    transition: opacity 600ms ease;
  }
  .prete canvas {
    opacity: 1;
  }
  .quartier {
    position: absolute;
    padding: 0;
    border: 0;
    background: none;
    color: var(--claire);
    cursor: pointer;
  }
  .quartier.hors-champ {
    visibility: hidden;
  }
  /* L'immeuble choisi : ses fenêtres passent devant son bouton. */
  .quartier.avance {
    cursor: zoom-out;
  }
  .quartier:focus-visible {
    outline-offset: -2px;
  }
  .nom {
    position: absolute;
    transform: translate(-50%, 4px);
    width: max-content;
    font-family: var(--display);
    font-size: 24px;
    line-height: 1;
    /* Un liseré sombre détache le nom de la maquette, comme sur une carte. */
    -webkit-text-stroke: 5px var(--eau);
    paint-order: stroke fill;
    pointer-events: none;
  }
  .nom.au-dessus {
    transform: translate(-50%, calc(-100% - 6px));
  }
  .maquette:not(.prete) .nom {
    visibility: hidden;
  }
  @media (hover: hover) {
    .quartier:hover .nom {
      text-decoration: underline;
      text-decoration-thickness: 1px;
      text-underline-offset: 4px;
    }
  }
  .quartier[aria-pressed="true"] .nom {
    text-decoration: underline;
    text-decoration-thickness: 2px;
    text-underline-offset: 4px;
  }
  .fenetre {
    position: absolute;
    z-index: 3000;
    display: block;
  }
  .fenetre.ouvrable {
    cursor: pointer;
  }
  .fen-nom {
    position: absolute;
    left: 50%;
    bottom: calc(100% + 8px);
    transform: translateX(-50%);
    width: max-content;
    max-width: 16em;
    font-weight: 700;
    line-height: 1.2;
    text-align: center;
    color: var(--claire);
    -webkit-text-stroke: 5px var(--eau);
    paint-order: stroke fill;
    visibility: hidden;
    pointer-events: none;
  }
  @media (hover: hover) {
    .fenetre:hover .fen-nom {
      visibility: visible;
    }
  }
  @media (max-width: 640px) {
    .nom {
      font-size: 21px;
    }
  }
</style>
