<script lang="ts">
  // Grand écran public (vidéoprojecteur) : Lyon s'illumine avec la progression de toutes les
  // équipes, le classement, le fil en direct et le compte à rebours. Rien sur le contenu des
  // défis. Lisible à cinq mètres : rien sous 24 px.
  import { untrack } from "svelte";

  import Immeuble from "../components/ville/Immeuble.svelte";
  import { api, errorMessage } from "../lib/api";
  import { formatDuration, formatHeure, formatPoints, poll } from "../lib/format";
  import { live } from "../lib/live.svelte";
  import { serverNow, session } from "../lib/session.svelte";
  import { t, tn } from "../lib/strings";
  import { typo } from "../lib/typo";
  import type { FeedItem, Scoreboard, ScreenData } from "../lib/types";
  import { NOMS_RIVIERES, PLAN, PONTS, RIVIERES, villeEteinte, type Quartier } from "../lib/ville";

  let { id }: { id: string } = $props();

  let ecran = $state<ScreenData | null>(null);
  let classement = $state<Scoreboard | null>(null);
  let flux = $state<FeedItem[]>([]);
  let erreur = $state<string | null>(null);
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
      erreur = errorMessage(e);
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

  // La ville : chaque quartier allume une part de ses fenêtres égale à sa progression globale.
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
</script>

<main class="ecran">
  {#if erreur}
    <p class="message">{t("screen.not_found")} {erreur}</p>
  {:else if !ecran}
    <p class="message">{t("loading")}</p>
  {:else}
    <div class="ville" aria-hidden="true">
      {#if quartiers}
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
              <Immeuble quartier={q} />
              <span class="nom">{q.categorie.name}</span>
            </div>
          {/each}
        </div>
      {/if}
    </div>

    <div class="cote">
      <h1 class="titre">{typo(ecran.title)}</h1>
      {#if reste !== null}
        <p class="compte">
          <span class="valeur tnum">{formatDuration(reste)}</span>
          <span class="libelle">{t(`phase.${session.event?.phase ?? "running"}`)}</span>
        </p>
      {:else}
        <p class="compte"><span class="libelle">{t("phase.ended")}</span></p>
      {/if}

      <section aria-labelledby="h-classement">
        <h2 class="sous-titre" id="h-classement">{t("screen.top")}</h2>
        {#if ecran.frozen}<p class="gel">{t("screen.frozen")}</p>{/if}
        <ol class="classement">
          {#each (classement?.teams ?? []).slice(0, 10) as ligne (ligne.team_id)}
            <li>
              <span class="rang tnum">{ligne.rank}</span>
              <span class="equipe">{typo(ligne.name)}</span>
              <span class="points tnum">{formatPoints(ligne.score)}</span>
            </li>
          {/each}
        </ol>
      </section>

      <section aria-labelledby="h-direct">
        <h2 class="sous-titre" id="h-direct">{t("screen.feed")}</h2>
        <ul class="direct">
          {#each flux.slice(0, 4) as evenement (`${evenement.kind}-${evenement.at}`)}
            <li>
              <span class="heure tnum">{heure(evenement.at)}</span>
              <span>
                {#if evenement.kind === "first_blood"}
                  {t("screen.first_blood", { team: evenement.team, challenge: evenement.challenge })}
                {:else}
                  {t("screen.announcement", { title: evenement.title })}
                {/if}
              </span>
            </li>
          {/each}
        </ul>
      </section>

      <p class="equipes">{tn("screen.active_teams", ecran.active_teams)}</p>
    </div>
  {/if}
</main>

<style>
  .ecran {
    min-height: 100vh;
    display: grid;
    grid-template-columns: minmax(0, 3fr) minmax(0, 2fr);
    gap: var(--e7);
    padding: var(--e6) var(--e7);
    font-size: 24px;
    line-height: 1.35;
  }
  .message {
    grid-column: 1 / -1;
  }
  .ville {
    container-type: size;
    display: grid;
    place-items: center;
    min-height: 0;
  }
  .carte {
    position: relative;
    width: min(100cqw, 100cqh * 600 / 650);
    aspect-ratio: 600 / 650;
  }
  .fond {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
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
    font-size: 36px;
    line-height: 1;
    white-space: nowrap;
  }
  .cote {
    display: flex;
    flex-direction: column;
    gap: var(--e6);
    min-width: 0;
  }
  .titre {
    font-family: var(--display);
    font-weight: 400;
    font-size: 72px;
    line-height: 1;
  }
  .compte {
    display: flex;
    align-items: baseline;
    flex-wrap: wrap;
    gap: var(--e3);
    margin-top: calc(-1 * var(--e4));
  }
  .valeur {
    font-size: 72px;
    font-weight: 700;
    line-height: 1;
    color: var(--lumen);
  }
  .libelle {
    color: var(--douce);
  }
  .sous-titre {
    font-family: var(--display);
    font-size: 48px;
    line-height: 1;
    margin-bottom: var(--e3);
  }
  .gel {
    color: var(--lumen);
    margin-bottom: var(--e2);
  }
  .classement {
    border-top: 1px solid var(--pierre);
  }
  .classement li {
    display: grid;
    grid-template-columns: 3rem minmax(0, 1fr) auto;
    gap: var(--e4);
    align-items: baseline;
    padding: var(--e2) 0;
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
  .direct li {
    display: grid;
    grid-template-columns: 5rem minmax(0, 1fr);
    gap: var(--e4);
    padding: var(--e2) 0;
    border-bottom: 1px solid var(--pierre);
  }
  .heure {
    color: var(--douce);
  }
  .equipes {
    margin-top: auto;
    color: var(--douce);
  }
</style>
