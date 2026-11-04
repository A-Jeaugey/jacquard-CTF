import { api, ApiError, errorMessage } from "./api";
import { loadTheme } from "./theme.svelte";
import type { EventInfo, Me } from "./types";

interface SessionState {
  ready: boolean;
  me: Me | null;
  event: EventInfo | null;
  configured: boolean;
  /** Écart entre l'horloge du serveur et celle du navigateur, en millisecondes. */
  clockOffset: number;
  /** Raison de l'échec du chargement de l'événement, s'il a échoué. */
  erreurEvenement: string | null;
}

export const session: SessionState = $state({
  ready: false,
  me: null,
  event: null,
  configured: true,
  clockOffset: 0,
  erreurEvenement: null,
});

export async function refreshEvent(): Promise<void> {
  try {
    const event = await api.get<EventInfo>("/api/event");
    session.event = event;
    session.configured = true;
    session.clockOffset = new Date(event.server_time).getTime() - Date.now();
    session.erreurEvenement = null;
    document.title = event.name;
  } catch (error) {
    if (error instanceof ApiError && error.code === "event_not_configured") session.configured = false;
    else {
      session.erreurEvenement = errorMessage(error);
      throw error;
    }
  }
}

export async function refreshMe(): Promise<void> {
  session.me = await api.get<Me | null>("/api/auth/me");
}

export async function bootstrap(): Promise<void> {
  // Le thème est chargé avant le premier affichage : ses libellés remplacent ceux par défaut.
  await Promise.allSettled([refreshEvent(), refreshMe(), loadTheme()]);
  session.ready = true;
}

/** Peut-on encore s'inscrire ? Non si l'orga les a fermées ou si l'événement est fini. */
export function inscriptionsOuvertes(): boolean {
  return session.event?.participation.registration !== "closed" && session.event?.phase !== "ended";
}

export function serverNow(): number {
  return Date.now() + session.clockOffset;
}
