<script lang="ts">
  import { api, errorMessage } from "../lib/api";
  import { navigate } from "../lib/router.svelte";
  import { session } from "../lib/session.svelte";
  import { t } from "../lib/strings";
  import type { Me } from "../lib/types";

  let username = $state("");
  let password = $state("");
  let error = $state<string | null>(null);
  let busy = $state(false);

  async function submit(event: SubmitEvent): Promise<void> {
    event.preventDefault();
    busy = true;
    error = null;
    try {
      session.me = await api.post<Me>("/api/auth/login", { username, password });
      navigate(session.me.team || session.me.user.role === "admin" ? "/challenges" : "/team");
    } catch (e) {
      error = errorMessage(e);
    } finally {
      busy = false;
    }
  }
</script>

<form class="card form narrow" onsubmit={submit}>
  <h1>{t("nav.login")}</h1>
  <label>
    {t("auth.username")}
    <input autocomplete="username" required bind:value={username} />
  </label>
  <label>
    {t("auth.password")}
    <input type="password" autocomplete="current-password" required bind:value={password} />
  </label>
  {#if error}<p class="error" role="alert">{error}</p>{/if}
  <button type="submit" disabled={busy}>{t("auth.login")}</button>
  {#if session.event?.participation.registration !== "closed"}
    <p class="muted small">{t("auth.no_account")} <a href="/register">{t("nav.register")}</a></p>
  {/if}
</form>
