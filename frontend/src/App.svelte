<script lang="ts">
  import Nav from "./components/Nav.svelte";
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
  import Team from "./pages/Team.svelte";

  const pages = {
    "/": Home,
    "/login": Login,
    "/register": Register,
    "/team": Team,
    "/challenges": Board,
    "/scoreboard": Scoreboard,
    "/admin": Admin,
  } as const;

  const Page = $derived(pages[route.path as keyof typeof pages] ?? NotFound);

  void bootstrap();
</script>

<svelte:document onclick={interceptLinks} />

{#if !session.ready}
  <p class="center muted">{t("loading")}</p>
{:else if !session.configured}
  <main class="container">
    <div class="card">{t("error.not_configured")}</div>
  </main>
{:else}
  <Nav />
  <main class="container">
    <Page />
  </main>
{/if}
