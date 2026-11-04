<script lang="ts">
  import PageAcces from "../components/PageAcces.svelte";
  import { api, ApiError, errorMessage } from "../lib/api";
  import { navigate } from "../lib/router.svelte";
  import { session } from "../lib/session.svelte";
  import { t } from "../lib/strings";
  import type { Me } from "../lib/types";

  let pseudo = $state("");
  let motDePasse = $state("");
  let courriel = $state("");
  let code = $state("");
  let erreur = $state<{ titre: string; texte: string } | null>(null);
  let envoi = $state(false);
  let premierChamp = $state<HTMLInputElement>();

  const mode = $derived(session.event?.participation.registration);

  async function valider(event: SubmitEvent): Promise<void> {
    event.preventDefault();
    envoi = true;
    erreur = null;
    try {
      session.me = await api.post<Me>("/api/auth/register", {
        username: pseudo,
        password: motDePasse,
        email: courriel || null,
        registration_code: mode === "invite_code" ? code : null,
      });
      navigate(session.me.team ? "/challenges" : "/team");
    } catch (e) {
      const refus = e instanceof ApiError && e.status < 500;
      erreur = { titre: refus ? t("auth.register_refused") : t("error.title"), texte: errorMessage(e) };
      premierChamp?.focus();
    } finally {
      envoi = false;
    }
  }
</script>

<PageAcces>
  <h1 class="titre-page">{t("auth.register_title")}</h1>
  {#if mode === "closed"}
    <p class="ferme">{t("auth.registration_closed")}</p>
    <p><a class="btn-ligne" href="/login">{t("nav.login")}</a></p>
  {:else}
    <form class="formulaire" onsubmit={valider}>
      <div class="champ">
        <label for="pseudo">{t("auth.username")}</label>
        <input
          id="pseudo"
          class="saisie"
          bind:this={premierChamp}
          bind:value={pseudo}
          autocomplete="username"
          required
          minlength="3"
          maxlength="32"
          aria-describedby="aide-pseudo"
        />
        <p class="aide" id="aide-pseudo">{t("auth.username_hint")}</p>
      </div>
      <div class="champ">
        <label for="mot-de-passe">{t("auth.password")}</label>
        <input
          id="mot-de-passe"
          class="saisie"
          type="password"
          bind:value={motDePasse}
          autocomplete="new-password"
          required
          minlength="8"
          maxlength="128"
          aria-describedby="aide-mdp"
        />
        <p class="aide" id="aide-mdp">{t("auth.password_hint")}</p>
      </div>
      <div class="champ">
        <label for="courriel">{t("auth.email")}</label>
        <input id="courriel" class="saisie" type="email" bind:value={courriel} autocomplete="email" maxlength="254" />
      </div>
      {#if mode === "invite_code"}
        <div class="champ">
          <label for="code">{t("auth.registration_code")}</label>
          <input id="code" class="saisie" bind:value={code} required autocomplete="off" aria-describedby="aide-code" />
          <p class="aide" id="aide-code">{t("auth.registration_code_hint")}</p>
        </div>
      {/if}
      {#if erreur}
        <p class="refus" role="alert"><b>{erreur.titre}</b> {erreur.texte}</p>
      {/if}
      <p>
        <button type="submit" class="btn-principal" disabled={envoi}>{envoi ? t("auth.registering") : t("auth.register")}</button>
      </p>
    </form>
    <p class="bascule">{t("auth.has_account")} <a href="/login">{t("auth.login_link")}</a>.</p>
  {/if}
</PageAcces>

<style>
  .formulaire {
    display: grid;
    gap: var(--e5);
    margin-top: var(--e6);
  }
  .ferme {
    margin: var(--e4) 0;
  }
  .bascule {
    margin-top: var(--e6);
    padding-top: var(--e4);
    border-top: 1px solid var(--pierre);
    color: var(--douce);
  }
  .bascule a {
    color: var(--claire);
    display: inline-flex;
    align-items: center;
    min-height: 44px;
  }
</style>
