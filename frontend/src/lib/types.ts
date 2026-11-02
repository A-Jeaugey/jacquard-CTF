// Types des réponses de l'API. À garder synchronisés avec backend/src/jacquard/api.

export type Phase = "not_started" | "running" | "ended";

export interface Category {
  id: string;
  name: string;
  description: string | null;
  color: string | null;
}

export interface EventInfo {
  id: string;
  name: string;
  tagline: string | null;
  timezone: string;
  schedule: { start: string; end: string; freeze: string | null };
  phase: Phase;
  frozen: boolean;
  server_time: string;
  participation: {
    mode: "teams" | "solo";
    team_size: { min: number; max: number };
    registration: "open" | "invite_code" | "closed";
  };
  flag_format: string | null;
  difficulties: string[];
  categories: Category[];
  board: { layout: string };
}

export interface User {
  id: number;
  username: string;
  role: "player" | "admin";
}

export interface Me {
  user: User;
  team: { id: number; name: string } | null;
}

export interface TeamDetail {
  id: number;
  name: string;
  invite_code: string | null;
  max_size: number;
  members: { id: number; username: string }[];
  score: number;
  rank: number | null;
  solves: {
    challenge_id: string;
    challenge_name: string;
    solved_at: string;
    solved_by: string | null;
    points: number;
  }[];
}

export interface ChallengeSummary {
  id: string;
  name: string;
  category: string;
  difficulty: string | null;
  tags: string[];
  value: number;
  solves: number;
  solved: boolean;
}

export interface ChallengeDetail extends ChallengeSummary {
  authors: string[];
  description_html: string;
  connection: string | null;
  files: { id: string; name: string; size: number }[];
}

export interface ChallengeList {
  phase: Phase;
  challenges: ChallengeSummary[];
}

export type SubmitStatus = "correct" | "incorrect" | "already_solved";

export interface ScoreboardEntry {
  rank: number;
  team_id: number;
  name: string;
  score: number;
  solves: number;
  last_solve_at: string | null;
}

export interface Scoreboard {
  frozen: boolean;
  frozen_at: string | null;
  teams: ScoreboardEntry[];
}

export interface Announcement {
  id: number;
  title: string;
  body_html: string;
  created_at: string;
}

export interface AdminTeam {
  id: number;
  name: string;
  hidden: boolean;
  rank: number | null;
  score: number;
  solves: number;
  members: string[];
}

export interface AdminSubmission {
  id: number;
  team_id: number;
  team: string;
  user: string | null;
  challenge_id: string;
  challenge: string;
  provided: string;
  correct: boolean;
  ip: string;
  created_at: string;
}

/**
 * Données transmises à un layout de tableau. C'est le contrat que devront respecter
 * les layouts fournis par les packs (voir docs/conception-plateforme.md, §6.2).
 */
export interface BoardData {
  categories: Category[];
  challenges: ChallengeSummary[];
  difficulties: string[];
}
