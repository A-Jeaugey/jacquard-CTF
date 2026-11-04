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

  // La ville de chaque équipe : la même silhouette pour toutes (un immeuble par quartier, une
  // fenêtre par défi public, toujours à la même place) ; ses fenêtres résolues sont allumées.
  // Fenêtres de 8 × 12 (deux tiers de la marque du plan) : des façades, pas une barre. Un
  // quartier fourni monte en étages (quatre au plus) plutôt qu'en largeur, pour que la ville
  // reste lisible quand l'événement compte beaucoup de défis. Les quartiers sont dans l'ordre
  // du plan, nommés une fois dans la légende.
  const PAS = 11;
  const ETAGE = 15;
  const ECART = 6;
  const HAUTEURS = [44, 54, 38, 58, 42, 50, 38, 46];
  const etagesPour = (n: number): number => (n <= 2 ? 1 : n <= 8 ? 2 : n <= 15 ? 3 : 4);
  // Chaque défi garde sa fenêtre pour toutes les équipes, mais les places ne suivent pas
  // l'ordre des défis : une façade remplie dans l'ordre se lirait comme une jauge. L'ordre des
  // places est un mélange fixe, propre à chaque immeuble.
  const brouille = (x: number): number => Math.imul(x ^ (x >>> 15), 0x2c1b3c6d) >>> 0;
  const melange = (n: number, graine: number): number[] => {
    const places = Array.from({ length: n }, (_, k) => k);
    const cle = places.map((k) => brouille(k * 97 + graine * 7919 + 1));
    return places.sort((a, b) => (cle[a] ?? 0) - (cle[b] ?? 0));
  };
  const ville = $derived.by(() => {
    let x = 0;
    let premier = 0;
    return (classement?.districts ?? []).map((d, i) => {
      const etages = etagesPour(d.count);
      const colonnes = Math.ceil(d.count / etages);
      const largeur = colonnes * PAS + 3;
      const hauteur = Math.max(HAUTEURS[i % HAUTEURS.length] ?? 44, etages * ETAGE + 8);
      const immeuble = { x, largeur, hauteur, premier, n: d.count, etages, colonnes, places: melange(d.count, i) };
      x += largeur + ECART;
      premier += d.count;
      return immeuble;
    });
  });
  const HAUT = $derived(Math.max(...HAUTEURS, ...ville.map((b) => b.hauteur)) + 4);
  const legende = $derived(
    (classement?.districts ?? [])
      .map((d) => session.event?.categories.find((c) => c.id === d.category)?.name ?? d.category)
      .join(", "),
  );
  const largeurVille = $derived(ville.length ? (ville.at(-1)?.x ?? 0) + (ville.at(-1)?.largeur ?? 0) : 0);
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
                    <rect class="toit" x={b.x - 1} y={HAUT - b.hauteur - 3} width={b.largeur + 2} height="3" />
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
  .toit {
    fill: var(--toit);
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
