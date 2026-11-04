<script lang="ts">
  import { tick } from "svelte";

  import PageAcces from "../components/PageAcces.svelte";
  import { api, ApiError, errorMessage } from "../lib/api";
  import { navigate } from "../lib/router.svelte";
  import { session } from "../lib/session.svelte";
  import { t } from "../lib/strings";
  import type { Me } from "../lib/types";

  let pseudo = $state("");
  let motDePasse = $state("");
  let erreur = $state<{ titre: string; texte: string; champs: boolean } | null>(null);
  let envoi = $state(false);
  let champPseudo = $state<HTMLInputElement>();
  let bouton = $state<HTMLButtonElement>();

  async function valider(event: SubmitEvent): Promise<void> {
    event.preventDefault();
    envoi = true;
    erreur = null;
    try {
      session.me = await api.post<Me>("/api/auth/login", { username: pseudo, password: motDePasse });
      navigate(session.me.team || session.me.user.role === "admin" ? "/challenges" : "/team");
    } catch (e) {
      const refus = e instanceof ApiError && (e.status === 401 || e.status === 429);
      // Seul un identifiant refusé met les champs en cause ; une panne n'est pas leur faute.
      erreur = { titre: refus ? t("auth.refused") : t("error.title"), texte: errorMessage(e), champs: e instanceof ApiError && e.status === 401 };
    } finally {
      envoi = false;
    }
    if (erreur) {
      await tick();
      (erreur.champs ? champPseudo : bouton)?.focus();
    }
  }
</script>

<PageAcces>
  <h1 class="titre-page">{t("auth.login_title")}</h1>
  <p class="intro">{t("auth.login_intro")}</p>
  <form class="formulaire" onsubmit={valider}>
    <div class="champ">
      <label for="pseudo">{t("auth.username")}</label>
      <input
        id="pseudo"
        class="saisie"
        bind:this={champPseudo}
        bind:value={pseudo}
        autocomplete="username"
        required
        maxlength="32"
        aria-invalid={erreur?.champs ? "true" : undefined}
        aria-describedby={erreur ? "erreur-connexion" : undefined}
        oninput={() => erreur?.champs && (erreur = null)}
      />
    </div>
    <div class="champ">
      <label for="mot-de-passe">{t("auth.password")}</label>
      <input
        id="mot-de-passe"
        class="saisie"
        type="password"
        bind:value={motDePasse}
        autocomplete="current-password"
        required
        maxlength="128"
        aria-invalid={erreur?.champs ? "true" : undefined}
        aria-describedby={erreur ? "erreur-connexion" : undefined}
        oninput={() => erreur?.champs && (erreur = null)}
      />
    </div>
    {#if erreur}
      <p class="refus" id="erreur-connexion" role="alert"><b>{erreur.titre}</b> {erreur.texte}</p>
    {/if}
    <p>
      <button type="submit" class="btn-principal" disabled={envoi} bind:this={bouton}>{envoi ? t("auth.logging_in") : t("auth.login")}</button>
    </p>
  </form>
  {#if session.event?.participation.registration !== "closed"}
    <p class="bascule">{t("auth.no_account")} <a href="/register">{t("auth.create_account")}</a>.</p>
  {/if}
</PageAcces>

<style>
  .intro {
    margin-top: var(--e3);
    font-size: var(--t-nom);
  }
  .formulaire {
    display: grid;
    gap: var(--e5);
    margin-top: var(--e6);
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
