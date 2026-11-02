<script lang="ts">
  import { api, errorMessage } from "../lib/api";
  import { navigate } from "../lib/router.svelte";
  import { session } from "../lib/session.svelte";
  import { t } from "../lib/strings";
  import type { Me } from "../lib/types";

  let username = $state("");
  let password = $state("");
  let email = $state("");
  let registrationCode = $state("");
  let error = $state<string | null>(null);
  let busy = $state(false);

  const mode = $derived(session.event?.participation.registration);

  async function submit(event: SubmitEvent): Promise<void> {
    event.preventDefault();
    busy = true;
    error = null;
    try {
      session.me = await api.post<Me>("/api/auth/register", {
        username,
        password,
        email: email || null,
        registration_code: mode === "invite_code" ? registrationCode : null,
      });
      navigate(session.me.team ? "/challenges" : "/team");
    } catch (e) {
      error = errorMessage(e);
    } finally {
      busy = false;
    }
  }
</script>

{#if mode === "closed"}
  <div class="card narrow">{t("auth.registration_closed")}</div>
{:else}
  <form class="card form narrow" onsubmit={submit}>
    <h1>{t("nav.register")}</h1>
    <label>
      {t("auth.username")}
      <input autocomplete="username" required minlength="3" maxlength="32" bind:value={username} />
    </label>
    <label>
      {t("auth.password")}
      <input type="password" autocomplete="new-password" required minlength="8" maxlength="128" bind:value={password} />
      <span class="muted small">{t("auth.password_hint")}</span>
    </label>
    <label>
      {t("auth.email")}
      <input type="email" autocomplete="email" maxlength="254" bind:value={email} />
    </label>
    {#if mode === "invite_code"}
      <label>
        {t("auth.registration_code")}
        <input required autocomplete="off" bind:value={registrationCode} />
      </label>
    {/if}
    {#if error}<p class="error" role="alert">{error}</p>{/if}
    <button type="submit" disabled={busy}>{t("auth.register")}</button>
    <p class="muted small">{t("auth.has_account")} <a href="/login">{t("nav.login")}</a></p>
  </form>
{/if}
