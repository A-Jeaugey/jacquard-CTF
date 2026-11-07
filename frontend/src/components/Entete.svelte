<script lang="ts">
  import { api } from "../lib/api";
  import { equipe } from "../lib/equipe.svelte";
  import { formatPoints } from "../lib/format";
  import { navigate, route } from "../lib/router.svelte";
  import { inscriptionsOuvertes, refreshMe, session } from "../lib/session.svelte";
  import { story, unreadCount } from "../lib/story.svelte";
  import { t, tn } from "../lib/strings";
  import Compte from "./Compte.svelte";

  const nonLus = $derived(story.data ? unreadCount() : 0);
  const avecJournal = $derived(
    Boolean(session.me && story.data && (story.data.entries.length > 0 || story.data.locked > 0)),
  );
  const courant = (chemin: string): "page" | undefined => (route.path === chemin ? "page" : undefined);

  async function seDeconnecter(): Promise<void> {
    await api.post("/api/auth/logout");
    await refreshMe();
    navigate("/");
  }
</script>

<header class="barre">
  <a class="evitement" href="#contenu">{t("nav.skip")}</a>
  {#if session.event}
    <a class="logo" href="/"><span class="logo-texte">{session.event.name}</span></a>
  {/if}
  {#if session.event}
  <nav class="nav" aria-label={t("nav.label")}>
    <ul>
      {#if session.me}
        <li><a href="/challenges" aria-current={courant("/challenges")}><span class="libelle">{t("nav.board")}</span></a></li>
      {/if}
      <li><a href="/scoreboard" aria-current={courant("/scoreboard")}><span class="libelle">{t("nav.scoreboard")}</span></a></li>
      {#if avecJournal}
        <li>
          <a href="/story" aria-current={courant("/story")}>
            <span class="libelle">{t("nav.story")}</span>
            {#if nonLus > 0 && route.path !== "/story"}
              <span class="compteur tnum" aria-label={tn("nav.unread", nonLus)}>{nonLus}</span>
            {/if}
          </a>
        </li>
      {/if}
      {#if session.me?.user.role === "admin"}
        <li><a href="/admin" aria-current={courant("/admin")}><span class="libelle">{t("nav.admin")}</span></a></li>
      {/if}
    </ul>
  </nav>
  {/if}
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
  {:else if session.event}
    <div class="acces">
      <a class="lien" href="/login" aria-current={courant("/login")}><span class="libelle">{t("nav.login")}</span></a>
      {#if inscriptionsOuvertes()}
        <a class="lien" href="/register" aria-current={courant("/register")}><span class="libelle">{t("nav.register")}</span></a>
      {/if}
    </div>
  {/if}
</header>

<style>
  .barre {
    display: flex;
    align-items: center;
    gap: var(--e6);
    min-height: 64px;
    padding: 0 var(--bord);
    border-bottom: 1px solid var(--pierre);
  }
  .logo {
    display: inline-flex;
    align-items: center;
    flex: 0 1 auto;
    min-width: 0;
    max-width: 16em;
    overflow-wrap: anywhere;
    min-height: 44px;
    padding-top: var(--e1);
    font-family: var(--display);
    font-size: 36px;
    line-height: 1;
    text-decoration: none;
  }
  /* Un nom d'événement très long tient sur deux lignes au plus. */
  .logo-texte {
    display: -webkit-box;
    -webkit-box-orient: vertical;
    -webkit-line-clamp: 2;
    line-clamp: 2;
    overflow: hidden;
    line-height: 1.1;
    /* Lumignons dépasse de ses lignes (accents des capitales en haut, hampes de la ligne
       masquée en bas) : place pour les accents au-dessus, coupe juste au-dessus des hampes de
       la troisième ligne en dessous. */
    padding-top: 0.12em;
    margin-top: -0.12em;
    max-height: 2.07em;
  }
  .nav ul {
    display: flex;
    gap: var(--e1);
  }
  /* Un seul traitement pour tous les liens de l'en-tête (navigation et accès) : souligné au
     survol, gras et souligné sur la page courante, sans que le gras déplace quoi que ce soit. */
  .nav a,
  .lien {
    display: inline-flex;
    align-items: center;
    min-height: 44px;
    padding: 0 var(--e3);
    color: var(--douce);
    text-decoration: none;
  }
  .libelle {
    text-underline-offset: 4px;
  }
  .nav a:hover,
  .lien:hover {
    color: var(--claire);
  }
  .nav a:hover .libelle,
  .lien:hover .libelle {
    text-decoration: underline;
  }
  /* Page courante : clair et souligné de 2 px, sans gras (rien ne change de largeur). */
  .nav a[aria-current="page"],
  .lien[aria-current="page"] {
    color: var(--claire);
  }
  .nav a[aria-current="page"] .libelle,
  .lien[aria-current="page"] .libelle {
    text-decoration: underline;
    text-decoration-thickness: 2px;
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
    min-width: 0;
    min-height: 44px;
    line-height: 1.25;
    text-decoration: none;
  }
  a.equipe .equipe-nom {
    color: var(--douce);
  }
  a.equipe:hover .equipe-nom,
  a.equipe[aria-current="page"] .equipe-nom {
    color: var(--claire);
    text-decoration: underline;
    text-underline-offset: 4px;
  }
  a.equipe[aria-current="page"] .equipe-nom {
    text-decoration-thickness: 2px;
  }
  .equipe-nom {
    max-width: min(24ch, 100%);
    /* Le soulignement de la page courante reste dans la boîte du nom, et à distance de la
       ligne du rang : il appartient au nom seul. */
    padding-bottom: 2px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  /* Le nom de l'administrateur n'est pas un lien : texte secondaire, comme les liens au repos. */
  span.equipe .equipe-nom {
    color: var(--douce);
  }
  .equipe-score {
    margin-top: 2px;
    font-size: var(--t-meta);
    color: var(--douce);
  }
  .score {
    color: var(--lumignon);
  }
  .sortie {
    color: var(--douce);
    text-decoration: none;
  }
  .sortie:hover {
    color: var(--claire);
    text-decoration: underline;
  }
  .acces {
    display: flex;
    align-items: center;
    gap: var(--e1);
    margin-right: calc(-1 * var(--e3));
  }


  @media (max-width: 1099px) {
    .barre {
      display: grid;
      align-items: stretch;
      gap: 0 var(--e4);
      grid-template-columns: minmax(0, 1fr) auto;
      grid-template-areas: "logo compte" "nav nav" "equipe sortie";
      padding: var(--e2) var(--bord);
    }
    .logo {
      grid-area: logo;
    }
    .nav {
      grid-area: nav;
      margin: var(--e1) 0 0;
    }
    .nav li:first-child a {
      padding-left: 0;
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
      margin-right: 0;
    }
    .acces .lien:first-child {
      padding-left: 0;
    }
    .sortie {
      grid-area: sortie;
      /* Le filet passe sous la gouttière : une seule ligne avec celui de l'équipe. */
      margin-left: calc(-1 * var(--e4));
      padding-left: var(--e4);
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
