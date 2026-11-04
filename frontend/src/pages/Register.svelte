<script lang="ts">
  import { tick } from "svelte";

  import PageAcces from "../components/PageAcces.svelte";
  import { api, ApiError, errorMessage } from "../lib/api";
  import { navigate } from "../lib/router.svelte";
  import { inscriptionsOuvertes, session } from "../lib/session.svelte";
  import { t } from "../lib/strings";
  import type { Me } from "../lib/types";

  let pseudo = $state("");
  let motDePasse = $state("");
  let courriel = $state("");
  let code = $state("");
  type Champ = "pseudo" | "mot-de-passe" | "courriel" | "code";
  let erreur = $state<{ titre: string; texte: string; champ: Champ | null } | null>(null);
  let envoi = $state(false);
  let bouton = $state<HTMLButtonElement>();

  // Le champ mis en cause par une erreur du serveur, d'après son code ou la validation.
  const PAR_CODE: Record<string, Champ> = {
    username_taken: "pseudo",
    invalid_username: "pseudo",
    invalid_email: "courriel",
    bad_registration_code: "code",
  };
  const PAR_NOM: Record<string, Champ> = {
    username: "pseudo",
    password: "mot-de-passe",
    email: "courriel",
    registration_code: "code",
  };
  function champDe(e: unknown): Champ | null {
    if (!(e instanceof ApiError)) return null;
    const direct = PAR_CODE[e.code];
    if (direct) return direct;
    const champs = Array.isArray(e.extra.fields) ? (e.extra.fields as string[]) : [];
    return champs.map((f) => PAR_NOM[f]).find((c) => c !== undefined) ?? null;
  }
  const enCause = (champ: Champ): "true" | undefined => (erreur?.champ === champ ? "true" : undefined);
  const decrit = (champ: Champ, aide?: string): string | undefined =>
    [aide, erreur?.champ === champ ? "erreur-inscription" : undefined].filter(Boolean).join(" ") || undefined;
  const effacer = (champ: Champ) => (): void => {
    if (erreur?.champ === champ) erreur = null;
  };

  const mode = $derived(session.event?.participation.registration);
  const terminee = $derived(session.event?.phase === "ended");
  const ouvertes = $derived(inscriptionsOuvertes());

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
      const refus = e instanceof ApiError && e.status >= 400 && e.status < 500;
      erreur = { titre: refus ? t("auth.register_refused") : t("error.title"), texte: errorMessage(e), champ: champDe(e) };
    } finally {
      envoi = false;
    }
    if (erreur) {
      await tick();
      if (erreur.champ) document.getElementById(erreur.champ)?.focus();
      else bouton?.focus();
    }
  }
</script>

<PageAcces>
  <h1 class="titre-page">{t("auth.register_title")}</h1>
  <p class="intro">
    {#if ouvertes}{t("auth.register_intro")}{:else if terminee}{t("auth.registration_ended")}{:else}{t("auth.registration_closed")}{/if}
  </p>
  {#if !ouvertes}
    <p class="ferme"><a class="btn-principal" href="/login">{t("nav.login")}</a></p>
  {:else}
    <form class="formulaire" onsubmit={valider}>
      <div class="champ">
        <label for="pseudo">{t("auth.username")}</label>
        <input
          id="pseudo"
          class="saisie"
          bind:value={pseudo}
          autocomplete="username"
          required
          minlength="3"
          maxlength="32"
          aria-invalid={enCause("pseudo")}
          aria-describedby={decrit("pseudo", "aide-pseudo")}
          oninput={effacer("pseudo")}
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
          aria-invalid={enCause("mot-de-passe")}
          aria-describedby={decrit("mot-de-passe", "aide-mdp")}
          oninput={effacer("mot-de-passe")}
        />
        <p class="aide" id="aide-mdp">{t("auth.password_hint")}</p>
      </div>
      <div class="champ">
        <label for="courriel">{t("auth.email")}</label>
        <input
          id="courriel"
          class="saisie"
          type="email"
          bind:value={courriel}
          autocomplete="email"
          maxlength="254"
          aria-invalid={enCause("courriel")}
          aria-describedby={decrit("courriel")}
          oninput={effacer("courriel")}
        />
      </div>
      {#if mode === "invite_code"}
        <div class="champ">
          <label for="code">{t("auth.registration_code")}</label>
          <input
            id="code"
            class="saisie"
            bind:value={code}
            required
            autocomplete="off"
            aria-invalid={enCause("code")}
            aria-describedby={decrit("code", "aide-code")}
            oninput={effacer("code")}
          />
          <p class="aide" id="aide-code">{t("auth.registration_code_hint")}</p>
        </div>
      {/if}
      {#if erreur}
        <p class="refus" id="erreur-inscription" role="alert"><b>{erreur.titre}</b> {erreur.texte}</p>
      {/if}
      <p>
        <button type="submit" class="btn-principal" disabled={envoi} bind:this={bouton}>{envoi ? t("auth.registering") : t("auth.register")}</button>
      </p>
    </form>
    <p class="bascule">{t("auth.has_account")} <a href="/login">{t("auth.login_link")}</a>.</p>
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
