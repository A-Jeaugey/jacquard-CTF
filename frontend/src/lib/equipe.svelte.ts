// L'équipe du joueur (score, rang, objets, résolutions) et le nombre d'équipes classées.
// Partagé par l'en-tête et les pages ; rafraîchi au temps réel.

import { api } from "./api";
import { session } from "./session.svelte";
import type { Scoreboard, TeamDetail } from "./types";

export const equipe = $state({
  data: null as TeamDetail | null,
  nombreEquipes: 0,
});

export async function refreshEquipe(): Promise<void> {
  if (!session.me?.team) {
    equipe.data = null;
    return;
  }
  try {
    const [detail, classement] = await Promise.all([
      api.get<TeamDetail>("/api/teams/me"),
      api.get<Scoreboard>("/api/scoreboard"),
    ]);
    equipe.data = detail;
    equipe.nombreEquipes = classement.teams.length;
  } catch {
    // L'en-tête reste utilisable sans score ; la page de l'équipe affiche l'erreur.
  }
}
