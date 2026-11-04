// Connexion temps réel (Server-Sent Events). Les pages réagissent aux compteurs de
// `live.ticks` pour se recharger ; les événements importants deviennent des toasts.

import { session } from "./session.svelte";
import { refreshStory } from "./story.svelte";
import { t } from "./strings";

export interface Toast {
  id: number;
  text: string;
  kind: "info" | "success" | "highlight";
}

export const live = $state({
  connected: false,
  ticks: { solve: 0, team: 0, unlock: 0, announcement: 0 },
});

export const toasts: Toast[] = $state([]);

let source: EventSource | null = null;
let nextToastId = 1;

export function pushToast(text: string, kind: Toast["kind"] = "info", duration = 6000): void {
  const toast = { id: nextToastId++, text, kind };
  toasts.push(toast);
  if (toasts.length > 4) toasts.shift();
  setTimeout(() => dismissToast(toast.id), duration);
}

export function dismissToast(id: number): void {
  const index = toasts.findIndex((toast) => toast.id === id);
  if (index >= 0) toasts.splice(index, 1);
}

type Handler = (data: Record<string, unknown>) => void;

const handlers: Record<string, Handler> = {
  solve(data) {
    live.ticks.solve++;
    if (data.first_blood === 1 && data.team_id !== session.me?.team?.id) {
      pushToast(t("live.first_blood", { team: String(data.team), challenge: String(data.challenge) }), "highlight");
    }
  },
  team_update(data) {
    live.ticks.team++;
    // L'auteur de l'action a déjà son retour dans l'interface.
    if (data.user === session.me?.user.username) return;
    const params = { user: String(data.user), challenge: String(data.challenge) };
    pushToast(t(data.reason === "hint" ? "live.teammate_hint" : "live.teammate_solve", params), "success");
  },
  unlock(data) {
    live.ticks.unlock++;
    void refreshStory();
    const names = ((data.challenges as { name: string }[]) ?? []).map((c) => c.name);
    // Au-delà de deux déblocages simultanés, un seul toast plutôt qu'une avalanche.
    if (names.length > 2) {
      pushToast(t("live.unlocked_challenges", { n: names.length, names: names.join(", ") }), "highlight");
    } else {
      for (const name of names) pushToast(t("live.unlocked_challenge", { name }), "highlight");
    }
    for (const chapter of (data.story as { title: string }[]) ?? []) {
      pushToast(t("live.unlocked_story", { title: chapter.title }), "highlight");
    }
  },
  announcement(data) {
    live.ticks.announcement++;
    pushToast(t("live.announcement", { title: String(data.title) }), "info", 10000);
  },
};

/** Mode audit (`?audit` dans l'adresse) : pas de flux temps réel. Une connexion SSE ouverte
 * empêche les outils d'analyse de considérer la page comme chargée. */
export const auditMode = new URLSearchParams(location.search).has("audit");

/** Ouvre (ou rouvre) le flux. À rappeler quand l'utilisateur ou son équipe change. */
export function connectLive(): void {
  source?.close();
  if (auditMode) return;
  source = new EventSource("/api/live");
  source.onopen = () => (live.connected = true);
  source.onerror = () => (live.connected = false);
  for (const [type, handle] of Object.entries(handlers)) {
    source.addEventListener(type, (event) => {
      try {
        handle(JSON.parse((event as MessageEvent<string>).data) as Record<string, unknown>);
      } catch {
        // Un événement mal formé ne doit pas casser la connexion.
      }
    });
  }
}
