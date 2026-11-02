import { api, ApiError } from "./api";
import { loadTheme } from "./theme.svelte";
import type { EventInfo, Me } from "./types";

interface SessionState {
  ready: boolean;
  me: Me | null;
  event: EventInfo | null;
  configured: boolean;
  /** Écart entre l'horloge du serveur et celle du navigateur, en millisecondes. */
  clockOffset: number;
}

export const session: SessionState = $state({
  ready: false,
  me: null,
  event: null,
  configured: true,
  clockOffset: 0,
});

export async function refreshEvent(): Promise<void> {
  try {
    const event = await api.get<EventInfo>("/api/event");
    session.event = event;
    session.configured = true;
    session.clockOffset = new Date(event.server_time).getTime() - Date.now();
    document.title = event.name;
  } catch (error) {
    if (error instanceof ApiError && error.code === "event_not_configured") session.configured = false;
    else throw error;
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

export function serverNow(): number {
  return Date.now() + session.clockOffset;
}
