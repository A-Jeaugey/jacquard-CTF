// Chapitres du journal et suivi des chapitres déjà lus (stocké dans le navigateur).

import { api, errorMessage } from "./api";
import type { Story } from "./types";

const SEEN_KEY = "jq_story_seen";

function readSeen(): string[] {
  try {
    const value: unknown = JSON.parse(localStorage.getItem(SEEN_KEY) ?? "[]");
    return Array.isArray(value) ? value.filter((v): v is string => typeof v === "string") : [];
  } catch {
    return [];
  }
}

export const story = $state({
  data: null as Story | null,
  seen: readSeen(),
  /** Dernière erreur de chargement, tant qu'aucune donnée n'a pu être lue. */
  erreur: null as string | null,
});

export function unreadCount(): number {
  return story.data?.entries.filter((entry) => !story.seen.includes(entry.id)).length ?? 0;
}

export async function refreshStory(): Promise<void> {
  try {
    story.data = await api.get<Story>("/api/story");
    story.erreur = null;
  } catch (e) {
    // Le journal est secondaire : une erreur ici ne bloque rien ailleurs, mais la page
    // des messages doit pouvoir la montrer.
    story.erreur = errorMessage(e);
  }
}

export function markAllSeen(): void {
  const ids = story.data?.entries.map((entry) => entry.id) ?? [];
  story.seen = Array.from(new Set([...story.seen, ...ids]));
  try {
    localStorage.setItem(SEEN_KEY, JSON.stringify(story.seen));
  } catch {
    // Stockage indisponible (navigation privée...) : le badge réapparaîtra, sans gravité.
  }
}
