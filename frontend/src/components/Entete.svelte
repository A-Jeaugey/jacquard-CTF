<script lang="ts">
  import { api } from "../lib/api";
  import { equipe } from "../lib/equipe.svelte";
  import { formatPoints } from "../lib/format";
  import { navigate, route } from "../lib/router.svelte";
  import { refreshMe, session } from "../lib/session.svelte";
  import { story, unreadCount } from "../lib/story.svelte";
  import { t, tn } from "../lib/strings";
  import Compte from "./Compte.svelte";

  const nonLus = $derived(story.data ? unreadCount() : 0);
  const avecJournal = $derived(Boolean(story.data && (story.data.entries.length > 0 || story.data.locked > 0)));
  const courant = (chemin: string): "page" | undefined => (route.path === chemin ? "page" : undefined);

  async function seDeconnecter(): Promise<void> {
    await api.post("/api/auth/logout");
    await refreshMe();
    navigate("/");
  }
</script>

<header class="barre">
  <a class="evitement" href="#contenu">{t("nav.skip")}</a>
  <a class="logo" href="/">{session.event?.name ?? ""}</a>
  <nav class="nav" aria-label={t("nav.label")}>
    <ul>
      <li><a href="/challenges" aria-current={courant("/challenges")}>{t("nav.board")}</a></li>
      <li><a href="/scoreboard" aria-current={courant("/scoreboard")}>{t("nav.scoreboard")}</a></li>
      {#if avecJournal}
        <li>
          <a href="/story" aria-current={courant("/story")}>
            {t("nav.story")}
            {#if nonLus > 0 && route.path !== "/story"}
              <span class="compteur tnum" aria-label={tn("nav.unread", nonLus)}>{nonLus}</span>
            {/if}
          </a>
        </li>
      {/if}
      {#if session.me?.user.role === "admin"}
        <li><a href="/admin" aria-current={courant("/admin")}>{t("nav.admin")}</a></li>
      {/if}
    </ul>
  </nav>
  <Compte />
  {#if session.me}
    {#if session.me.team}
      <a class="equipe" href="/team" aria-current={courant("/team")}>
        <span class="equipe-nom">{session.me.team.name}</span>
        {#if equipe.data && equipe.data.rank}
          <span class="equipe-score tnum">
            {equipe.data.rank}<span class="sup">e</span>
            {t("nav.rank_of", { total: equipe.nombreEquipes })},
            <b class="score">{formatPoints(equipe.data.score)}</b>
          </span>
        {/if}
      </a>
    {:else if session.me.user.role !== "admin"}
      <a class="equipe" href="/team" aria-current={courant("/team")}><span class="equipe-nom">{t("nav.team_join")}</span></a>
    {:else}
      <span class="equipe"><span class="equipe-nom">{session.me.user.username}</span></span>
    {/if}
    <button type="button" class="btn-texte sortie" onclick={seDeconnecter}>{t("nav.logout")}</button>
  {:else}
    <div class="acces">
      <a class="lien" href="/login" aria-current={courant("/login")}>{t("nav.login")}</a>
      <a class="btn-ligne" href="/register">{t("nav.register")}</a>
    </div>
  {/if}
</header>

<style>
  .barre {
    display: flex;
    align-items: center;
    gap: var(--e6);
    min-height: 64px;
    padding: 0 var(--gouttiere);
    border-bottom: 1px solid var(--pierre);
  }
  .logo {
    display: inline-flex;
    align-items: center;
    min-height: 44px;
    padding-top: var(--e1);
    font-family: var(--display);
    font-size: 36px;
    line-height: 1;
    text-decoration: none;
  }
  .nav ul {
    display: flex;
    gap: var(--e1);
  }
  .nav a {
    display: inline-flex;
    align-items: center;
    min-height: 44px;
    padding: 0 var(--e3);
    color: var(--douce);
    text-decoration: none;
  }
  .nav a:hover {
    color: var(--claire);
    text-decoration: underline;
    text-underline-offset: 8px;
  }
  .nav a[aria-current="page"] {
    color: var(--claire);
    font-weight: 700;
    text-decoration: underline;
    text-decoration-thickness: 2px;
    text-underline-offset: 8px;
  }
  .compteur {
    display: inline-grid;
    place-items: center;
    min-width: 24px;
    height: 24px;
    margin-left: var(--e2);
    padding: 0 var(--e2);
    background: var(--claire);
    color: var(--nuit);
    border-radius: 2px;
    font-size: var(--t-meta);
    font-weight: 700;
  }
  .equipe {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    justify-content: center;
    min-height: 44px;
    line-height: 1.25;
    text-decoration: none;
  }
  a.equipe:hover .equipe-nom,
  a.equipe[aria-current="page"] .equipe-nom {
    text-decoration: underline;
    text-underline-offset: 4px;
  }
  .equipe-score {
    font-size: var(--t-meta);
    color: var(--douce);
  }
  .score {
    color: var(--lumignon);
  }
  .sortie {
    color: var(--douce);
  }
  .sortie:hover {
    color: var(--claire);
  }
  .acces {
    display: flex;
    align-items: center;
    gap: var(--e4);
  }
  .lien {
    display: inline-flex;
    align-items: center;
    min-height: 44px;
    color: var(--douce);
  }

  @media (max-width: 1099px) {
    .barre {
      display: grid;
      align-items: stretch;
      gap: 0;
      grid-template-columns: 1fr auto;
      grid-template-areas: "logo compte" "nav nav" "equipe sortie";
      padding: var(--e2) var(--gouttiere);
    }
    .logo {
      grid-area: logo;
    }
    .nav {
      grid-area: nav;
      margin: var(--e1) calc(-1 * var(--e3)) 0;
    }
    .nav ul {
      flex-wrap: wrap;
    }
    .barre :global(.compte) {
      grid-area: compte;
    }
    .equipe,
    .acces {
      grid-area: equipe;
      align-items: flex-start;
      justify-content: center;
      border-top: 1px solid var(--pierre);
      padding-top: var(--e2);
      margin-top: var(--e1);
    }
    .acces {
      grid-column: 1 / -1;
      flex-direction: row;
      justify-content: flex-start;
    }
    .sortie {
      grid-area: sortie;
      border-top: 1px solid var(--pierre);
      padding-top: var(--e2);
      margin-top: var(--e1);
      min-height: 52px;
    }
  }
  @media (max-width: 359px) {
    .nav a {
      padding: 0 var(--e2);
    }
  }
</style>
