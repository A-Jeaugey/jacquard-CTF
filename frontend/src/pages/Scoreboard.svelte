<script lang="ts">
  import { untrack } from "svelte";

  import Reessayer from "../components/Reessayer.svelte";
  import { api, errorMessage } from "../lib/api";
  import { formatHeure, formatPoints, poll } from "../lib/format";
  import { live } from "../lib/live.svelte";
  import { session } from "../lib/session.svelte";
  import { t, tn } from "../lib/strings";
  import { typo } from "../lib/typo";
  import type { Scoreboard } from "../lib/types";
  import { gabaritsDe, type NomGabarit } from "../lib/ville";

  let classement = $state<Scoreboard | null>(null);
  let erreur = $state<string | null>(null);

  async function charger(): Promise<void> {
    try {
      classement = await api.get<Scoreboard>("/api/scoreboard");
      erreur = null;
    } catch (e) {
      erreur = errorMessage(e);
    }
  }

  $effect(() => poll(charger, 60_000));
  $effect(() => {
    void live.ticks.solve;
    void live.ticks.team;
    if (untrack(() => classement)) void charger();
  });

  const monEquipe = $derived(session.me?.team?.id ?? null);

  // La ville de chaque équipe : la même pour toutes (un immeuble par quartier, une fenêtre par
  // défi public, toujours à la même place) ; ses fenêtres résolues sont allumées. Chaque
  // immeuble reprend la silhouette de son quartier sur le plan (la tour de la Part-Dieu, la
  // flèche de Fourvière, les sheds de Gerland…) : on reconnaît le quartier sans légende, et la
  // hauteur a un sens. Fenêtres de 8 × 12 (deux tiers de la marque du plan) ; un quartier
  // fourni monte en étages (quatre au plus) plutôt qu'en largeur.
  const PAS = 11;
  const ETAGE = 15;
  const ECART = 7;
  type Piece = { x: number; y: number; w: number; h: number } | { points: string };
  const rect = (x: number, y: number, w: number, h: number): Piece => ({ x, y, w, h });
  const poly = (...sommets: [number, number][]): Piece => ({ points: sommets.map(([a, b]) => `${a},${b}`).join(" ") });
  // Une rangée de pignons (pointes) ou de sheds (dents de scie) sur la largeur `w`.
  const dents = (x: number, w: number, n: number, haut: number, scie: boolean): Piece[] =>
    Array.from({ length: n }, (_, k) => {
      const a = x + (k * w) / n;
      const b = x + ((k + 1) * w) / n;
      return scie ? poly([a, 0], [a, -haut], [b, 0]) : poly([a, 0], [(a + b) / 2, -haut], [b, 0]);
    });
  const etagesPour = (n: number): number => (n <= 2 ? 1 : n <= 8 ? 2 : n <= 15 ? 3 : 4);
  const bas = (n: number): number => (n <= 4 ? 1 : etagesPour(n));
  interface Silhouette {
    /** Hauteur de la façade, au moins celle de ses étages. */
    hauteur: number;
    /** Hauteur du toit au-dessus de la façade. */
    cime: number;
    etages: (n: number) => number;
    /** Le toit, posé sur la façade (y = 0 en haut de la façade). */
    toit: (x: number, w: number) => Piece[];
  }
  const SILHOUETTES: Record<NomGabarit | "autre", Silhouette> = {
    // Immeuble de canuts : corniche et deux cheminées.
    canuts: { hauteur: 44, cime: 10, etages: etagesPour, toit: (x, w) => [rect(x - 1, -3, w + 2, 3), rect(x + 3, -10, 3, 7), rect(x + w - 6, -9, 3, 6)] },
    // Tour de la Part-Dieu : une colonne de fenêtres qu'on gravit, coiffée de sa pointe.
    tour: { hauteur: 62, cime: 16, etages: (n) => Math.min(Math.max(n, 1), 4), toit: (x, w) => [poly([x, 0], [x + w / 2, -16], [x + w, 0])] },
    // Maisons Renaissance du Vieux Lyon : une suite de pignons.
    renaissance: { hauteur: 40, cime: 8, etages: etagesPour, toit: (x, w) => dents(x, w, Math.max(2, Math.round(w / 12)), 8, false) },
    // Basilique de Fourvière : la flèche à gauche, le fronton.
    basilique: { hauteur: 38, cime: 20, etages: etagesPour, toit: (x, w) => [poly([x, 0], [x + 3, -20], [x + 6, 0]), poly([x + 7, 0], [x + (w + 7) / 2, -7], [x + w, 0])] },
    // Musée de Confluence : un volume oblique.
    musee: { hauteur: 36, cime: 12, etages: etagesPour, toit: (x, w) => [poly([x, 0], [x + 3, -12], [x + w + 4, -5], [x + w, 0])] },
    // Immeuble traversé par une traboule : un toit à deux pans.
    traboule: { hauteur: 40, cime: 9, etages: etagesPour, toit: (x, w) => [poly([x - 2, 0], [x + w / 2, -9], [x + w + 2, 0])] },
    // Usine de Gerland : basse et large, toit en sheds et cheminée.
    usine: { hauteur: 26, cime: 18, etages: bas, toit: (x, w) => [...dents(x, w - 6, Math.max(2, Math.round((w - 6) / 11)), 7, true), rect(x + w - 5, -18, 4, 18)] },
    // L'école du Terrain : basse, toit plat débordant.
    ecole: { hauteur: 24, cime: 3, etages: bas, toit: (x, w) => [rect(x - 2, -3, w + 4, 3)] },
    // Une catégorie sans place sur le plan : un immeuble simple.
    autre: { hauteur: 40, cime: 3, etages: etagesPour, toit: (x, w) => [rect(x - 1, -3, w + 2, 3)] },
  };
  // Chaque défi garde sa fenêtre pour toutes les équipes, mais les places ne suivent pas
  // l'ordre des défis : une façade remplie dans l'ordre se lirait comme une jauge. L'ordre des
  // places est un mélange fixe, propre à chaque immeuble.
  const brouille = (x: number): number => Math.imul(x ^ (x >>> 15), 0x2c1b3c6d) >>> 0;
  const melange = (n: number, graine: number): number[] => {
    const places = Array.from({ length: n }, (_, k) => k);
    const cle = places.map((k) => brouille(k * 97 + graine * 7919 + 1));
    return places.sort((a, b) => (cle[a] ?? 0) - (cle[b] ?? 0));
  };
  // Largeur que la colonne de la ville lui donne au plus (18 rem) : au-delà, chaque immeuble
  // gagne un étage (quatre au plus) avant que le dessin ne soit réduit.
  const CIBLE = 288;
  const ville = $derived.by(() => {
    const districts = classement?.districts ?? [];
    const gabarits = gabaritsDe(districts.map((d) => d.category));
    const construire = (bonus: number) => {
      let x = 2;
      let premier = 0;
      return districts.map((d, i) => {
        const s = SILHOUETTES[gabarits[i] ?? "autre"];
        const etages = d.count ? Math.min(4, d.count, s.etages(d.count) + bonus) : 1;
        const colonnes = Math.max(1, Math.ceil(d.count / etages));
        const largeur = colonnes * PAS + 3;
        const hauteur = Math.max(s.hauteur, etages * ETAGE + 8);
        const immeuble = { x, largeur, hauteur, cime: s.cime, toit: s.toit(x, largeur), premier, etages, colonnes, places: melange(d.count, i) };
        x += largeur + ECART;
        premier += d.count;
        return immeuble;
      });
    };
    const largeur = (immeubles: ReturnType<typeof construire>): number =>
      (immeubles.at(-1)?.x ?? 0) + (immeubles.at(-1)?.largeur ?? 0) + 2;
    let immeubles = construire(0);
    for (let bonus = 1; bonus <= 3 && largeur(immeubles) > CIBLE; bonus++) immeubles = construire(bonus);
    return immeubles;
  });
  const HAUT = $derived(Math.max(0, ...ville.map((b) => b.hauteur + b.cime)) + 2);
  const legende = $derived(
    (classement?.districts ?? [])
      .map((d) => session.event?.categories.find((c) => c.id === d.category)?.name ?? d.category)
      .join(", "),
  );
  const largeurVille = $derived(ville.length ? (ville.at(-1)?.x ?? 0) + (ville.at(-1)?.largeur ?? 0) + 2 : 0);
</script>

<div class="page">
  <h1 class="titre-page" id="titre-classement" tabindex="-1">{t("scoreboard.title")}</h1>
  <p class="intro">{t("scoreboard.intro")}</p>
  {#if legende}<p class="legende">{t("scoreboard.legend", { names: legende })}</p>{/if}

  {#if erreur}
    <div class="etat" role="alert">
      <p class="refus">
        <b>{t("error.title")}</b>
        {erreur}
        {#if classement}{t("error.stale")}{/if}
      </p>
      <p class="relance"><Reessayer action={charger} cible="titre-classement" /></p>
    </div>
  {:else if !classement}
    <p class="secondaire etat">{t("loading")}</p>
  {/if}

  {#if classement}
    <p class="secondaire etat">
      {#if classement.frozen && classement.frozen_at}
        {t("scoreboard.frozen", { time: formatHeure(classement.frozen_at, session.event?.timezone) })}
      {:else}
        {tn("scoreboard.teams", classement.teams.length)}
      {/if}
    </p>
    {#if classement.teams.length}
      <ol class="classement">
        {#each classement.teams as ligne (ligne.team_id)}
          {@const mien = ligne.team_id === monEquipe}
          <li class:mien aria-current={mien ? "true" : undefined}>
            <span class="rang tnum">{ligne.rank}<span class="sup">{ligne.rank === 1 ? "re" : "e"}</span></span>
            <span class="nom">
              {typo(ligne.name)}
              {#if mien}<span class="meta">{t("scoreboard.yours")}</span>{/if}
            </span>
            <span class="facade">
              {#if ville.length}
                {@const allumees = new Set(ligne.lit ?? [])}
                <svg viewBox="0 0 {largeurVille} {HAUT}" width={largeurVille} height={HAUT} aria-hidden="true" focusable="false">
                  {#each ville as b, j (j)}
                    <g transform="translate(0 {HAUT - b.hauteur})">
                      {#each b.toit as piece, k (k)}
                        {#if "points" in piece}
                          <polygon class="facade-mur" points={piece.points} />
                        {:else}
                          <rect class="facade-mur" x={piece.x} y={piece.y} width={piece.w} height={piece.h} />
                        {/if}
                      {/each}
                    </g>
                    <rect class="facade-mur" x={b.x} y={HAUT - b.hauteur} width={b.largeur} height={b.hauteur} />
                    {#each b.places as place, k (k)}
                      <rect
                        class="fenetre"
                        class:allumee={allumees.has(b.premier + k)}
                        x={b.x + 3 + (place % b.colonnes) * PAS}
                        y={HAUT - 4 - (b.etages - Math.floor(place / b.colonnes)) * ETAGE}
                        width="8"
                        height="12"
                      />
                    {/each}
                  {/each}
                </svg>
              {/if}
              <span class="nombre tnum" aria-hidden="true">{ligne.solves}</span>
              <span class="sr-only">{tn("scoreboard.solves", ligne.solves)}</span>
            </span>
            <span class="score tnum">{formatPoints(ligne.score)}</span>
          </li>
        {/each}
      </ol>
    {:else if session.me && !session.me.team}
      <p><a class="btn-principal" href="/team">{t("home.cta.team")}</a></p>
    {/if}
  {/if}
</div>

<style>
  .page {
    max-width: 880px;
  }
  .intro {
    margin-top: var(--e3);
    font-size: var(--t-nom);
    max-width: 56ch;
  }
  .legende {
    margin-top: var(--e2);
    max-width: 64ch;
    color: var(--douce);
  }
  .etat {
    margin-top: var(--e3);
  }
  .relance {
    margin-top: var(--e2);
  }
  /* Le fond de « ton équipe » déborde de 8 px ; les filets et le contenu restent alignés. */
  /* Les rangées partagent les colonnes de la liste (subgrid) : façades et points alignés. */
  .classement {
    position: relative;
    isolation: isolate;
    display: grid;
    /* Le nom garde au moins 10rem ; la ville se réduit (18rem au plus) au lieu de l'écraser. */
    grid-template-columns: 4rem minmax(10rem, 1fr) minmax(0, 18rem) auto;
    column-gap: var(--e4);
    margin-top: var(--e5);
    border-top: 1px solid var(--pierre);
  }
  .classement li {
    position: relative;
    grid-column: 1 / -1;
    display: grid;
    grid-template-columns: subgrid;
    align-items: center;
    min-height: 56px;
    padding: var(--e3) 0;
    border-bottom: 1px solid var(--pierre);
  }
  .mien::before {
    content: "";
    position: absolute;
    inset: 0 calc(-1 * var(--e2));
    z-index: -1;
    background: var(--pierre-sombre);
  }
  .rang {
    font-size: 24px;
    font-weight: 700;
    color: var(--douce);
  }
  .classement li:nth-child(-n + 3) .rang {
    color: var(--claire);
  }
  .nom {
    font-size: var(--t-nom);
    overflow-wrap: anywhere;
  }
  .nom .meta {
    margin-left: var(--e2);
  }
  .facade {
    display: flex;
    align-items: center;
    gap: var(--e2);
    min-width: 0;
  }
  .facade svg {
    display: block;
    flex: 0 1 auto;
    min-width: 0;
    max-width: 100%;
    height: auto;
  }
  .facade-mur {
    fill: var(--pierre);
  }
  .fenetre {
    fill: var(--eau);
  }
  .fenetre.allumee {
    fill: var(--lumignon);
  }
  .nombre {
    order: -1;
    min-width: 2ch;
    font-size: var(--t-meta);
    color: var(--douce);
    text-align: right;
  }
  .score {
    font-size: var(--t-nom);
    font-weight: 700;
    text-align: right;
  }
  .mien .nom {
    font-weight: 700;
  }
  .mien .score {
    color: var(--lumignon);
  }
  /* Empilé dès 760 px : sous cette largeur, la ville passe sous le nom. */
  @media (max-width: 760px) {
    .classement {
      display: block;
    }
    .classement li {
      grid-template-columns: 3rem minmax(0, 1fr) auto;
      grid-template-areas: "rang nom score" ". facade facade";
      column-gap: var(--e4);
      row-gap: var(--e2);
    }
    .rang {
      grid-area: rang;
    }
    .nom {
      grid-area: nom;
    }
    .facade {
      grid-area: facade;
    }
    .score {
      grid-area: score;
    }
  }
</style>
