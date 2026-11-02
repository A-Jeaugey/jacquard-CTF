<script lang="ts">
  import Nav from "./components/Nav.svelte";
  import Toasts from "./components/Toasts.svelte";
  import { connectLive } from "./lib/live.svelte";
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

  // Le flux temps réel et le journal dépendent de l'utilisateur et de son équipe.
  const identity = $derived(`${session.me?.user.id ?? "-"}:${session.me?.team?.id ?? "-"}`);
  $effect(() => {
    if (!session.ready || !session.configured) return;
    void identity;
    connectLive();
    void refreshStory();
  });
</script>

<svelte:document onclick={interceptLinks} />

{#if !session.ready}
  <p class="center muted">{t("loading")}</p>
{:else if !session.configured}
  <main class="container">
    <div class="card">{t("error.not_configured")}</div>
  </main>
{:else if screenId}
  <Screen id={screenId} />
{:else}
  <Nav />
  <main class="container">
    <Page />
  </main>
  <Toasts />
{/if}
