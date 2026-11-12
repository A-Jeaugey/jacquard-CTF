<script lang="ts">
  // Grand écran public (vidéoprojecteur) : Lyon s'illumine avec la progression de toutes les
  // équipes ; à côté, le compte à rebours, le classement et le dernier événement. Rien sur le
  // contenu des défis. Lisible à cinq mètres : rien sous 24 px en 1920 × 1080. Aucune
  // interaction : une coupure réseau garde la dernière image et réessaie seule.
  import { untrack } from "svelte";

  import Immeuble from "../components/ville/Immeuble.svelte";
  import Ville3D from "../components/ville/Ville3D.svelte";
  import { api, ApiError } from "../lib/api";
  import { carteGraphique } from "../lib/carte-graphique";
  import { formatDuration, formatHeure, formatPoints, poll } from "../lib/format";
  import { live } from "../lib/live.svelte";
  import { serverNow, session } from "../lib/session.svelte";
  import { t, tn } from "../lib/strings";
  import { typo } from "../lib/typo";
  import type { Marges } from "../lib/maquette3d";
  import type { FeedItem, Scoreboard, ScreenData } from "../lib/types";
  import { NOMS_RIVIERES, PLAN, PONTS, RIVIERES, villeEteinte, type Quartier } from "../lib/ville";

  let { id }: { id: string } = $props();

  let ecran = $state<ScreenData | null>(null);
  let classement = $state<Scoreboard | null>(null);
  let flux = $state<FeedItem[]>([]);
  // Erreur de premier chargement seulement : ensuite, la dernière image valide reste affichée.
  let erreur = $state<"introuvable" | "injoignable" | null>(null);
  let maintenant = $state(serverNow());

  async function charger(): Promise<void> {
    try {
      [ecran, classement, flux] = await Promise.all([
        api.get<ScreenData>(`/api/screens/${encodeURIComponent(id)}`),
        api.get<Scoreboard>("/api/scoreboard"),
        api.get<FeedItem[]>("/api/feed"),
      ]);
      erreur = null;
    } catch (e) {
      if (!untrack(() => ecran)) erreur = e instanceof ApiError && e.status === 404 ? "introuvable" : "injoignable";
    }
  }

  $effect(() => poll(charger, 20_000));
  $effect(() => {
    void live.ticks.solve;
    void live.ticks.announcement;
    if (untrack(() => ecran)) void charger();
  });
  $effect(() => {
    const minuteur = setInterval(() => (maintenant = serverNow()), 1000);
    return () => clearInterval(minuteur);
  });

  const reste = $derived.by(() => {
    const evenement = session.event;
    if (!evenement || evenement.phase === "ended") return null;
    const echeance = evenement.phase === "not_started" ? evenement.schedule.start : evenement.schedule.end;
    return new Date(echeance).getTime() - maintenant;
  });

  // La ville : chaque quartier allume une part de ses fenêtres égale à sa progression globale ;
  // les autres restent éteintes (sombres), pas verrouillées.
  const quartiers = $derived.by((): Quartier[] | null => {
    if (!ecran) return null;
    const ville = villeEteinte(session.event?.categories ?? []);
    if (!ville) return null;
    return ville.map((q) => {
      const progression = ecran?.categories.find((c) => c.id === q.categorie.id)?.progress ?? 0;
      const allumees = Math.round(progression * q.defis.length);
      const defis = q.defis.map((d, i) => ({ ...d, solved: i < allumees, locked: i >= allumees }));
      return { ...q, defis, resolus: allumees };
    });
  });
  const pct = (valeur: number, total: number): string => `${(valeur / total) * 100}%`;
  const heure = (iso: string): string => formatHeure(iso, session.event?.timezone);

  const equipes = $derived(classement?.teams ?? []);
  const resolutions = $derived(equipes.reduce((total, e) => total + e.solves, 0));
  const dernier = $derived(flux[0] ?? null);

  // Autant de rangées que la hauteur disponible en montre, et on le dit. Sur un petit écran
  // (repli empilé, la page défile), toutes les équipes sont listées.
  let hauteurListe = $state(0);
  let hauteurRangee = $state(0);
  let empile = $state(false);
  $effect(() => {
    const requete = window.matchMedia("(max-width: 900px)");
    const suivre = (): void => {
      empile = requete.matches;
    };
    suivre();
    requete.addEventListener("change", suivre);
    return () => requete.removeEventListener("change", suivre);
  });
  const visibles = $derived(
    empile
      ? equipes.length
      : hauteurRangee > 0
        ? Math.max(1, Math.floor(hauteurListe / hauteurRangee))
        : 10,
  );
  function mesurer(noeud: HTMLElement): void {
    hauteurRangee = noeud.getBoundingClientRect().height;
  }

  // La maquette en volume (frontend/DESIGN.md) : elle occupe tout l'écran, derrière le texte, et
  // tourne lentement. La caméra la cadre dans la place que le plan à plat occupait. Sans carte
  // graphique, ce plan à plat reste.
  let volume = $state(carteGraphique());
  let elCadre = $state<HTMLElement>();
  let degagement = $state<Marges>({ haut: 0, droite: 0, bas: 0, gauche: 0 });
  $effect(() => {
    document.body.classList.toggle("ecran-volume", volume);
    return () => document.body.classList.remove("ecran-volume");
  });
  $effect(() => {
    const cadre = elCadre;
    if (!cadre || !volume) return;
    const mesurerCadre = (): void => {
      if (empile) {
        degagement = { haut: 0, droite: 0, bas: 0, gauche: 0 };
        return;
      }
      const r = cadre.getBoundingClientRect();
      degagement = { haut: r.top, droite: window.innerWidth - r.right, bas: window.innerHeight - r.bottom, gauche: r.left };
    };
    const observateur = new ResizeObserver(mesurerCadre);
    observateur.observe(cadre);
    observateur.observe(document.body);
    mesurerCadre();
    return () => observateur.disconnect();
  });
</script>

<main class="ecran" class:en-volume={volume}>
  {#if erreur}
    <div class="panne">
      <h1 class="titre">{erreur === "introuvable" ? t("screen.not_found") : t("screen.unreachable")}</h1>
      <p>{erreur === "introuvable" ? t("screen.not_found_hint") : t("screen.unreachable_hint")}</p>
    </div>
  {:else if !ecran}
    <p class="attente">{t("loading")}</p>
  {:else}
    <section class="ville" aria-labelledby="titre-ecran">
      <h1 class="titre" id="titre-ecran">{typo(ecran.title)}</h1>
      <div class="cadre-carte" aria-hidden="true" bind:this={elCadre}>
        {#if quartiers}
          <div class="scene">
          <Ville3D {quartiers} decor ronde nuit {degagement} bind:volume onChoisir={() => {}}>
          {#snippet repli()}
          <div class="carte">
            <svg class="fond" viewBox="0 0 {PLAN.w} {PLAN.h}" preserveAspectRatio="none" focusable="false">
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
              <span class="riviere" style:left={pct(riviere.x, PLAN.w)} style:top={pct(riviere.y, PLAN.h)} style:--angle="{riviere.angle}deg"
                >{riviere.nom}</span
              >
            {/each}
            {#each quartiers as q (q.categorie.id)}
              <div class="immeuble" style:left={pct(q.x, PLAN.w)} style:top={pct(q.y, PLAN.h)} style:width={pct(q.w, PLAN.w)}>
                <Immeuble quartier={q} nuit />
                <span class="nom">{q.categorie.name}</span>
              </div>
            {/each}
          </div>
          {/snippet}
          </Ville3D>
          </div>
        {/if}
      </div>
      <p class="progression">{tn("screen.progress", resolutions)}</p>
      {#if dernier}
        <!-- La même chronique que sous le plan, sans action : personne ne touche cet écran. -->
        <div class="chronique">
          {#if dernier.kind === "first_blood"}
            <p class="chronique-titre">{t("live.first_blood_title")}</p>
            <p class="chronique-texte">
              {t("live.first_blood_text", { team: dernier.team, challenge: dernier.challenge, time: heure(dernier.at) })}
            </p>
          {:else}
            <p class="chronique-titre">{typo(dernier.title)}</p>
            <p class="chronique-texte">{t("screen.announcement_at", { time: heure(dernier.at) })}</p>
          {/if}
        </div>
      {/if}
    </section>

    <div class="cote">
      {#if reste !== null}
        <p class="compte">
          <b class="valeur tnum">{formatDuration(reste)}</b>
          {t(`phase.${session.event?.phase ?? "running"}`)}
        </p>
      {:else}
        <p class="compte">{t("phase.ended")}</p>
      {/if}

      <section class="classement-zone" aria-labelledby="h-classement">
        <h2 class="sous-titre" id="h-classement">{t("screen.top")}</h2>
        <p class="note">
          {tn("screen.active_teams", ecran.active_teams)}{#if equipes.length > visibles}.
            {tn("screen.top_n", visibles, { total: equipes.length })}{/if}
          {#if ecran.frozen}<br />{t("screen.frozen")}{/if}
        </p>
        {#if equipes.length === 0}
          <p class="vide">{t("screen.empty")}</p>
        {:else}
          <div class="liste" bind:clientHeight={hauteurListe}>
            <ol class="classement">
              {#each equipes.slice(0, visibles) as ligne, i (ligne.team_id)}
                {#if i === 0}
                  <li use:mesurer>
                    <span class="rang tnum">{ligne.rank}</span>
                    <span class="equipe">{typo(ligne.name)}</span>
                    <span class="points tnum">{formatPoints(ligne.score)}</span>
                  </li>
                {:else}
                  <li>
                    <span class="rang tnum">{ligne.rank}</span>
                    <span class="equipe">{typo(ligne.name)}</span>
                    <span class="points tnum">{formatPoints(ligne.score)}</span>
                  </li>
                {/if}
              {/each}
            </ol>
          </div>
        {/if}
      </section>
    </div>
  {/if}
</main>

<style>
  /* Les tailles suivent la hauteur de l'écran par paliers de l'échelle : 72/48/36/24 en
     1080 px et plus, 48/36/24/21 en dessous (projecteurs 1280 × 720 et 1366 × 768). */
  .ecran {
    --t-titre: 72px;
    --t-grand: 48px;
    --t-moyen: 36px;
    --t-base: 24px;
    height: 100vh;
    height: 100dvh;
    overflow: hidden;
    display: grid;
    grid-template-columns: minmax(0, 3fr) minmax(0, 2fr);
    grid-template-rows: minmax(0, 1fr);
    gap: var(--e7);
    padding: var(--e6) var(--e7);
    font-size: var(--t-base);
    line-height: 1.35;
  }
  @media (max-height: 1000px) {
    .ecran {
      --t-titre: 48px;
      --t-grand: 36px;
      --t-moyen: 24px;
      --t-base: 21px;
      gap: var(--e6);
      padding: var(--e5) var(--e6);
    }
  }
  .panne,
  .attente {
    grid-column: 1 / -1;
    align-self: center;
    max-width: 40ch;
  }
  .panne p {
    margin-top: var(--e4);
    color: var(--douce);
  }
  .ville {
    display: flex;
    flex-direction: column;
    min-height: 0;
  }
  /* Interligne assez haut pour que la ligne coupée ne dépasse pas sous les deux premières. */
  .titre {
    font-family: var(--display);
    font-weight: 400;
    font-size: var(--t-titre);
    line-height: 1.2;
    overflow-wrap: anywhere;
    display: -webkit-box;
    -webkit-box-orient: vertical;
    -webkit-line-clamp: 2;
    line-clamp: 2;
    overflow: hidden;
  }
  .cadre-carte {
    flex: 1;
    min-height: 0;
    container-type: size;
    display: grid;
    place-items: center;
    margin-top: var(--e4);
  }
  .carte {
    position: relative;
    width: min(100cqw, 100cqh * 600 / 650);
    aspect-ratio: 600 / 650;
  }
  /* La maquette en volume : en fond de tout l'écran, sous le texte ; un voile de la couleur de
     la table porte la colonne de droite. Sans elle, l'enveloppe s'efface devant le plan à plat. */
  .scene {
    display: contents;
  }
  .ecran.en-volume .scene {
    display: block;
    height: 76vw;
  }
  .ecran.en-volume :global(.maquette .nom) {
    font-size: var(--t-base);
  }
  @media (min-width: 901px) {
    :global(body.ecran-volume) {
      background: var(--table);
    }
    .ecran.en-volume .cadre-carte {
      display: block;
      container-type: normal;
    }
    .ecran.en-volume .scene {
      position: fixed;
      inset: 0;
      z-index: -1;
      height: auto;
    }
    .ecran.en-volume::after {
      content: "";
      position: fixed;
      top: 0;
      right: 0;
      bottom: 0;
      width: 46%;
      z-index: -1;
      pointer-events: none;
      background: linear-gradient(to right, transparent, color-mix(in srgb, var(--table) 92%, transparent) 38%);
    }
  }
  .fond {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
  }
  .quai {
    fill: none;
    stroke: var(--pierre);
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
    font-size: var(--t-moyen);
    line-height: 1;
    white-space: nowrap;
  }
  .progression {
    margin-top: var(--e5);
    font-size: var(--t-moyen);
    line-height: 1.25;
  }
  .chronique {
    margin-top: var(--e4);
    padding-top: var(--e3);
    border-top: 1px solid var(--pierre);
  }
  .chronique-titre {
    font-family: var(--display);
    font-size: var(--t-moyen);
    line-height: 1;
  }
  .chronique-texte {
    margin-top: var(--e2);
    overflow-wrap: anywhere;
    display: -webkit-box;
    -webkit-box-orient: vertical;
    -webkit-line-clamp: 2;
    line-clamp: 2;
    overflow: hidden;
  }
  .cote {
    display: flex;
    flex-direction: column;
    min-width: 0;
    min-height: 0;
  }
  .compte {
    font-size: var(--t-moyen);
    line-height: 1.2;
    color: var(--douce);
  }
  .valeur {
    color: var(--lumen);
  }
  .classement-zone {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
    margin-top: var(--e6);
  }
  .sous-titre {
    font-family: var(--display);
    font-size: var(--t-grand);
    line-height: 1;
  }
  .note {
    margin: var(--e2) 0 var(--e4);
    color: var(--douce);
  }
  .vide {
    padding-top: var(--e4);
    border-top: 1px solid var(--pierre);
  }
  .liste {
    flex: 1;
    min-height: 0;
    overflow: hidden;
  }
  .classement {
    border-top: 1px solid var(--pierre);
  }
  .classement li {
    display: grid;
    grid-template-columns: 2.5em minmax(0, 1fr) auto;
    gap: var(--e4);
    align-items: baseline;
    padding: var(--e3) 0;
    border-bottom: 1px solid var(--pierre);
  }
  .rang {
    font-weight: 700;
    color: var(--douce);
  }
  .classement li:nth-child(-n + 3) .rang {
    color: var(--claire);
  }
  .equipe {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .points {
    font-weight: 700;
  }

  /* Ouvert sur un petit écran (ce n'est pas son usage) : tout s'empile, rien ne déborde. */
  @media (max-width: 900px) {
    .ecran {
      --t-titre: 48px;
      --t-grand: 36px;
      --t-moyen: 21px;
      --t-base: var(--t-texte);
      height: auto;
      overflow: visible;
      grid-template-columns: minmax(0, 1fr);
      grid-template-rows: none;
      gap: var(--e6);
      padding: var(--e4);
    }
    .cadre-carte {
      flex: none;
      container-type: inline-size;
    }
    .carte {
      width: 100%;
    }
    .liste {
      overflow: visible;
    }
  }
</style>
