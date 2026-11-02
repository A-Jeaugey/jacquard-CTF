<script lang="ts">
  import { api } from "../lib/api";
  import { navigate, route } from "../lib/router.svelte";
  import { refreshMe, session } from "../lib/session.svelte";
  import { t } from "../lib/strings";
  import Countdown from "./Countdown.svelte";

  let open = $state(false);

  async function logout(): Promise<void> {
    await api.post("/api/auth/logout");
    await refreshMe();
    navigate("/");
  }

  $effect(() => {
    void route.path;
    open = false;
  });
</script>

<header class="nav">
  <div class="nav-inner container">
    <a class="brand" href="/">{session.event?.name}</a>
    <button class="nav-toggle" aria-expanded={open} aria-label="Menu" onclick={() => (open = !open)}>☰</button>
    <nav class:open>
      <a href="/challenges" class:active={route.path === "/challenges"}>{t("nav.board")}</a>
      <a href="/scoreboard" class:active={route.path === "/scoreboard"}>{t("nav.scoreboard")}</a>
      {#if session.me}
        <a href="/team" class:active={route.path === "/team"}>{session.me.team?.name ?? t("nav.team")}</a>
        {#if session.me.user.role === "admin"}
          <a href="/admin" class:active={route.path === "/admin"}>{t("nav.admin")}</a>
        {/if}
        <button class="link" onclick={logout}>{t("nav.logout")}</button>
      {:else}
        <a href="/login" class:active={route.path === "/login"}>{t("nav.login")}</a>
        <a class="button small" href="/register">{t("nav.register")}</a>
      {/if}
    </nav>
    <Countdown />
  </div>
</header>
