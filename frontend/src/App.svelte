<script lang="ts">
  import Entete from "./components/Entete.svelte";
  import Toasts from "./components/Toasts.svelte";
  import { refreshEquipe } from "./lib/equipe.svelte";
  import { connectLive, live } from "./lib/live.svelte";
  import { refreshStory } from "./lib/story.svelte";
  import { interceptLinks, route } from "./lib/router.svelte";
  import { bootstrap, session } from "./lib/session.svelte";
  import { t } from "./lib/strings";
  import Admin from "./pages/Admin.svelte";
  import Board from "./pages/Board.svelte";
  import Home from "./pages/Home.svelte";
  import Login from "./pages/Login.svelte";
  import NotFound from "./pages/NotFound.svelte";
  import Register from "./pages/Register.svelte";
  import Scoreboard from "./pages/Scoreboard.svelte";
  import Screen from "./pages/Screen.svelte";
  import Story from "./pages/Story.svelte";
  import Team from "./pages/Team.svelte";

  const pages = {
    "/": Home,
    "/login": Login,
    "/register": Register,
    "/team": Team,
    "/challenges": Board,
    "/scoreboard": Scoreboard,
    "/story": Story,
    "/admin": Admin,
  } as const;

  const Page = $derived(pages[route.path as keyof typeof pages] ?? NotFound);
  // Grand écran : /ecran/<id>, plein écran sans barre de navigation.
  const screenId = $derived(route.path.match(/^\/ecran\/([a-z0-9-]+)$/)?.[1] ?? null);

  void bootstrap();

  // Le flux temps réel, le journal et l'équipe dépendent de l'utilisateur et de son équipe.
  const identity = $derived(`${session.me?.user.id ?? "-"}:${session.me?.team?.id ?? "-"}`);
  $effect(() => {
    if (!session.ready || !session.configured) return;
    void identity;
    connectLive();
    void refreshStory();
  });
  $effect(() => {
    if (!session.ready) return;
    void identity;
    void live.ticks.solve;
    void live.ticks.team;
    void refreshEquipe();
  });
</script>

<svelte:document onclick={interceptLinks} />

{#if !session.ready}
  <p class="attente secondaire">{t("loading")}</p>
{:else if !session.configured}
  <main id="contenu" class="page page-etroite">
    <p>{t("error.not_configured")}</p>
  </main>
{:else if screenId}
  <Screen id={screenId} />
{:else}
  <Entete />
  <main id="contenu" tabindex="-1">
    <Page />
  </main>
  <footer class="pied">
    <p>{t("credits.fonts")}</p>
  </footer>
  <Toasts />
{/if}

<style>
  .attente {
    padding: var(--e7) var(--gouttiere);
  }
  .pied {
    padding: var(--e5) var(--gouttiere) var(--e7);
    border-top: 1px solid var(--pierre);
    font-size: var(--t-meta);
    color: var(--douce);
  }
  .pied p {
    max-width: 64ch;
  }
</style>
