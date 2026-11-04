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

export interface Item {
  id: string;
  name: string;
  description: string | null;
}

export interface TeamDetail {
  id: number;
  name: string;
  invite_code: string | null;
  max_size: number;
  penalty: number;
  items: Item[];
  members: { id: number; username: string }[];
  score: number;
  rank: number | null;
  solves: {
    challenge_id: string;
    challenge_name: string;
    /** Catégorie (quartier) du défi. */
    category: string;
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
  locked: boolean;
  locked_message: string | null;
  /** Défis (visibles) à résoudre avant celui-ci, d'après sa règle de déblocage. */
  after?: string[];
  /** Heure d'ouverture d'une règle de temps. */
  opens_at?: string | null;
}

export interface HintView {
  id: string;
  cost: number;
  available: boolean;
  unlocked: boolean;
  text_html: string | null;
}

export interface ChallengeDetail extends ChallengeSummary {
  authors: string[];
  description_html: string;
  connection: string | null;
  files: { id: string; name: string; size: number }[];
  hints: HintView[];
}

export interface UnlockSummary {
  challenges: { id: string; name: string }[];
  story: { id: string; title: string }[];
}

export type SubmitResult =
  | { status: "incorrect" | "already_solved" }
  | {
      status: "correct";
      first_blood: number | null;
      notifications: string[];
      items: Item[];
      unlocked: UnlockSummary;
    };

export interface StoryEntry {
  id: string;
  title: string;
  body_html: string;
  public: boolean;
}

export interface Story {
  entries: StoryEntry[];
  locked: number;
}

export interface ChallengeList {
  phase: Phase;
  challenges: ChallengeSummary[];
}


export interface ScoreboardEntry {
  rank: number;
  team_id: number;
  name: string;
  score: number;
  solves: number;
  last_solve_at: string | null;
  /** Fenêtres allumées de la ville commune (indices dans `districts`). */
  lit?: number[];
}

export interface Scoreboard {
  /** Défis dont l'existence est publique (ouverts d'emblée ou montrés verrouillés). */
  challenges?: number;
  /** La ville commune : quartiers dans l'ordre de l'événement, nombre de défis publics. */
  districts?: { category: string; count: number }[];
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

export interface ZoneConfig {
  element: string;
  target: { category: string | null; challenge: string | null };
  label: string | null;
}

export interface ThemeLayout {
  type: "image-map";
  background_url: string | null;
  zones: ZoneConfig[];
}

export interface Theme {
  tokens: Record<string, string>;
  strings: Record<string, string>;
  logo_url: string | null;
  css_url: string | null;
  layouts: Record<string, ThemeLayout>;
}

export interface ScreenData {
  id: string;
  title: string;
  layout: string | null;
  frozen: boolean;
  active_teams: number;
  categories: { id: string; name: string; color: string | null; progress: number }[];
}

export type FeedItem =
  | { kind: "first_blood"; at: string; team: string; challenge: string }
  | { kind: "announcement"; at: string; title: string };

export type ZoneState = "locked" | "available" | "in-progress" | "completed";

export interface ChallengeStats {
  id: string;
  name: string;
  category: string;
  solves: number;
  attempts: number;
  wrong: number;
  hints: number;
  first_solve_minutes: number | null;
  median_solve_minutes: number | null;
  top_wrong: { value: string; count: number }[];
}

export type Signal =
  | { kind: "shared_ip"; ip: string; teams: string[] }
  | { kind: "burst"; team: string; at_minutes: number }
  | { kind: "same_wrong_answer"; challenge: string; value: string; teams: string[] };

export interface AdminStats {
  challenges: ChallengeStats[];
  signals: Signal[];
}
