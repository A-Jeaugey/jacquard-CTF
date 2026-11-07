// La ville de nuit (frontend/DESIGN.md) : un immeuble par catégorie, une fenêtre par défi,
// rangées dans l'ordre où les défis s'ouvrent. Le plan est dessiné pour Lyon et les huit
// quartiers de Traboules ; une autre catégorie prend le premier emplacement libre.

import type { Category, ChallengeSummary } from "./types";

export type Etat = "resolu" | "disponible" | "verrouille";

export function etatDe(c: ChallengeSummary): Etat {
  return c.solved ? "resolu" : c.locked ? "verrouille" : "disponible";
}

// ---------------------------------------------------------------- géométrie des immeubles

export interface Fen {
  x: number;
  y: number;
  w: number;
  h: number;
  arc?: boolean;
}

export type Forme =
  | { el: "rect"; c: string; x: number; y: number; w: number; h: number }
  | { el: "polygon"; c: string; points: string }
  | { el: "path"; c: string; d: string };

export interface Gabarit {
  /** Largeur et hauteur du dessin (sans le socle, posé en y = h, haut de 4). */
  w: number;
  h: number;
  dessin: Forme[];
  /** Fenêtres dessinées à la main, utilisées quand le nombre de défis correspond. */
  fixe: Fen[];
  /** Zone où répartir les fenêtres sinon, taille nominale d'une fenêtre, sens de lecture. */
  zone: { x: number; y: number; w: number; h: number };
  fenetre: { w: number; h: number; arc?: boolean };
  sens: "ligne" | "colonne";
  socle: { x: number; w: number };
}

const r = (c: string, x: number, y: number, w: number, h: number): Forme => ({ el: "rect", c, x, y, w, h });
const p = (c: string, points: string): Forme => ({ el: "polygon", c, points });
const d = (c: string, chemin: string): Forme => ({ el: "path", c, d: chemin });
/** Volet clos : deux battants, sans lumière. Le décor de la façade ; seules les fenêtres des
 * défis s'éclairent. */
const volet = (x: number, y: number, w: number, h: number): Forme[] => [r("toit", x, y, w, h), r("ombre", x + w / 2 - 0.5, y, 1, h)];
/** Arc plein cintre (porte, passage, boutique). */
const arche = (c: string, x: number, bas: number, w: number, piedroit: number): Forme =>
  d(c, `M${x} ${bas}v${-piedroit}a${w / 2} ${w / 2} 0 0 1 ${w} 0v${piedroit}z`);
/** Petit cercle (oculus, rose). */
const rond = (c: string, cx: number, cy: number, rayon: number): Forme =>
  d(c, `M${cx - rayon} ${cy}a${rayon} ${rayon} 0 1 0 ${2 * rayon} 0a${rayon} ${rayon} 0 1 0 ${-2 * rayon} 0z`);

export type NomGabarit = "canuts" | "basilique" | "traboule" | "tour" | "renaissance" | "ecole" | "musee" | "usine";

// Chaque quartier a son architecture : proportions, étages, volets clos, corniches, portes. Seules
// les fenêtres des défis (« fixe », ou réparties dans « zone ») portent une lumière.
// Classes : facade (pierre), ombre (pierre sombre), toit (toits, volets, cordons), passage
// (portes, arches), couronne (la pointe de LUMEN), trait (treillis, arêtes).
export const GABARITS: Record<NomGabarit, Gabarit> = {
  // Immeuble de canuts des pentes : haut étage des ateliers (les défis), volets clos aux autres
  // étages, corniche, souches de cheminées, portes de traboules au rez-de-chaussée.
  canuts: {
    w: 120,
    h: 92,
    dessin: [
      r("facade", 14, 5, 16, 9),
      r("facade", 15, 1, 4, 4),
      r("facade", 21, 1, 4, 4),
      r("facade", 88, 4, 20, 10),
      r("facade", 89, 0, 4, 4),
      r("facade", 95, 0, 4, 4),
      r("facade", 101, 0, 4, 4),
      r("facade", 2, 12, 116, 3),
      r("facade", 6, 15, 108, 77),
      r("toit", 6, 15, 108, 1.5),
      r("toit", 6, 29, 108, 1),
      r("toit", 6, 57, 108, 1),
      r("toit", 6, 73, 108, 1),
      ...[16, 42, 68, 94].flatMap((x) => [...volet(x, 18, 10, 9), ...volet(x, 60, 10, 10), r("ombre", x - 2, 54, 14, 1.5)]),
      r("toit", 46, 78, 28, 14),
      r("ombre", 46, 78, 28, 2),
      arche("passage", 17, 92, 14, 9),
      arche("passage", 89, 92, 14, 9),
    ],
    fixe: [
      { x: 15, y: 32, w: 12, h: 22 },
      { x: 41, y: 32, w: 12, h: 22 },
      { x: 67, y: 32, w: 12, h: 22 },
      { x: 93, y: 32, w: 12, h: 22 },
    ],
    zone: { x: 12, y: 31, w: 96, h: 24 },
    fenetre: { w: 12, h: 22 },
    sens: "ligne",
    socle: { x: 0, w: 120 },
  },
  // Fourvière : la tour métallique en treillis, deux tours crénelées, le fronton et sa rose,
  // le portail entre deux colonnes ; les défis sont les baies de la nef.
  basilique: {
    w: 125,
    h: 96,
    dessin: [
      p("facade", "8,0 0,96 16,96"),
      r("toit", 4.5, 30, 7, 2),
      r("toit", 2.8, 56, 10.4, 2),
      r("toit", 1, 80, 14, 2),
      d("trait", "M6.6 32.5L12.4 55.5M9.4 32.5L3.6 55.5M4.2 58.5L13.4 79.5M11.8 58.5L2.6 79.5M2.2 82.5L14.6 95.5M13.8 82.5L1.4 95.5"),
      ...[23, 103].flatMap((x) => [
        r("facade", x, 30, 16, 66),
        ...[0, 4.33, 8.67, 13].map((dx) => r("facade", x + dx, 25, 3, 5)),
        r("toit", x, 30, 16, 1.5),
        arche("passage", x + 6, 52, 4, 5),
        arche("passage", x + 6, 74, 4, 5),
        r("ombre", x + 2, 84, 12, 1),
      ]),
      r("facade", 39, 50, 64, 46),
      p("facade", "37,51 71,30 105,51"),
      p("ombre", "45,49 71,34 97,49"),
      rond("toit", 71, 43, 3.5),
      r("toit", 39, 52, 64, 1.5),
      arche("passage", 61, 96, 20, 7),
      r("ombre", 52, 79, 2, 17),
      r("ombre", 88, 79, 2, 17),
    ],
    fixe: [
      { x: 46, y: 57, w: 12, h: 19, arc: true },
      { x: 65, y: 57, w: 12, h: 19, arc: true },
      { x: 84, y: 57, w: 12, h: 19, arc: true },
    ],
    zone: { x: 43, y: 55, w: 56, h: 22 },
    fenetre: { w: 12, h: 19, arc: true },
    sens: "ligne",
    socle: { x: 19, w: 106 },
  },
  // Immeuble traversé par une traboule : toit à deux pans, passage voûté au rez-de-chaussée,
  // fenêtres grillées de part et d'autre ; les défis sont au premier étage.
  traboule: {
    w: 110,
    h: 88,
    dessin: [
      p("toit", "2,20 55,6 108,20"),
      r("facade", 78, 7, 8, 9),
      r("facade", 4, 19, 102, 3),
      r("facade", 8, 22, 94, 66),
      r("toit", 8, 22, 94, 1.5),
      r("toit", 8, 46, 94, 1),
      r("toit", 8, 62, 94, 1),
      ...[20, 49, 78].flatMap((x) => [r("ombre", x - 1, 43.5, 14, 1.5), ...volet(x + 1, 49, 10, 10)]),
      r("toit", 16, 70, 12, 10),
      r("ombre", 21.5, 70, 1, 10),
      r("toit", 82, 70, 12, 10),
      r("ombre", 87.5, 70, 1, 10),
      arche("passage", 42, 88, 26, 10),
    ],
    fixe: [
      { x: 20, y: 26, w: 12, h: 17 },
      { x: 49, y: 26, w: 12, h: 17 },
      { x: 78, y: 26, w: 12, h: 17 },
    ],
    zone: { x: 14, y: 25, w: 82, h: 19 },
    fenetre: { w: 12, h: 17 },
    sens: "ligne",
    socle: { x: 0, w: 110 },
  },
  // Le « crayon » de la Part-Dieu : fût cerclé d'étages, ombré d'un côté, posé sur ses tours
  // basses ; on le gravit, premier défi en bas, dernier en haut. Sa pointe reste à LUMEN.
  tour: {
    w: 70,
    h: 206,
    dessin: [
      r("facade", 0, 182, 70, 24),
      ...[6, 52].map((x) => r("toit", x, 189, 12, 8)),
      r("facade", 20, 40, 30, 166),
      r("ombre", 43, 40, 7, 166),
      ...Array.from({ length: 20 }, (_, i) => r("toit", 20, 47 + i * 7, 30, 1)),
      r("toit", 19, 39, 32, 2),
      p("couronne", "20,40 35,2 50,40"),
    ],
    fixe: [
      { x: 28, y: 142, w: 14, h: 22 },
      { x: 28, y: 102, w: 14, h: 22 },
      { x: 28, y: 62, w: 14, h: 22 },
    ],
    zone: { x: 28, y: 50, w: 14, h: 130 },
    fenetre: { w: 14, h: 22 },
    sens: "colonne",
    socle: { x: 0, w: 70 },
  },
  // Maisons Renaissance du Vieux Lyon : trois pignons étroits, cordons d'étage, oculus,
  // croisée, arcades de boutiques ; une baie cintrée par maison pour les défis.
  renaissance: {
    w: 120,
    h: 96,
    dessin: [
      p("facade", "4,96 4,36 22,22 40,36 40,96"),
      p("facade", "41,96 41,24 60,6 79,24 79,96"),
      p("facade", "80,96 80,40 97,28 114,40 114,96"),
      r("toit", 40, 24, 1, 72),
      r("toit", 79, 28, 1, 68),
      rond("toit", 22, 33, 2.5),
      rond("toit", 60, 17, 3),
      rond("toit", 97, 37, 2.5),
      r("toit", 4, 46, 36, 1),
      r("toit", 4, 72, 36, 1),
      r("toit", 41, 30, 38, 1),
      r("toit", 41, 58, 38, 1),
      r("toit", 41, 78, 38, 1),
      r("toit", 80, 48, 34, 1),
      r("toit", 80, 74, 34, 1),
      r("toit", 54, 61, 12, 13),
      r("ombre", 59.5, 61, 1, 13),
      r("ombre", 54, 66.5, 12, 1),
      arche("passage", 13, 96, 18, 10),
      arche("passage", 52, 96, 16, 8),
      arche("passage", 88, 96, 18, 10),
    ],
    fixe: [
      { x: 16, y: 49, w: 12, h: 20, arc: true },
      { x: 54, y: 33, w: 12, h: 20, arc: true },
      { x: 91, y: 51, w: 12, h: 19, arc: true },
    ],
    zone: { x: 10, y: 44, w: 100, h: 28 },
    fenetre: { w: 12, h: 20, arc: true },
    sens: "ligne",
    socle: { x: 0, w: 120 },
  },
  // L'école (Terrain) : bâtiment bas, dalle de toit, bande vitrée à meneaux, entrée sous auvent.
  ecole: {
    w: 120,
    h: 70,
    dessin: [
      r("facade", 16, 10, 14, 6),
      r("facade", 88, 12, 10, 4),
      r("toit", 2, 16, 116, 4),
      r("facade", 6, 20, 108, 50),
      r("ombre", 10, 30, 100, 20),
      ...Array.from({ length: 9 }, (_, i) => r("toit", 20 + i * 10, 30, 1, 20)),
      r("toit", 44, 52, 32, 2),
      r("passage", 52, 54, 16, 16),
      r("ombre", 59.5, 54, 1, 16),
    ],
    fixe: [
      { x: 16, y: 32, w: 20, h: 16 },
      { x: 50, y: 32, w: 20, h: 16 },
      { x: 84, y: 32, w: 20, h: 16 },
    ],
    zone: { x: 12, y: 31, w: 96, h: 18 },
    fenetre: { w: 20, h: 16 },
    sens: "ligne",
    socle: { x: 0, w: 120 },
  },
  // Musée des Confluences : volumes obliques, facette sombre, arêtes du cristal, socle vitré.
  musee: {
    w: 96,
    h: 76,
    dessin: [
      p("facade", "6,76 14,32 46,12 90,34 84,76"),
      p("ombre", "46,12 90,34 84,76 64,76 60,38"),
      d("trait", "M14 32L36 42L46 12M36 42L60 38M36 42L30 68"),
      r("passage", 14, 68, 64, 8),
    ],
    fixe: [
      { x: 22, y: 46, w: 12, h: 16 },
      { x: 39, y: 46, w: 12, h: 16 },
      { x: 56, y: 46, w: 12, h: 16 },
    ],
    zone: { x: 18, y: 42, w: 56, h: 22 },
    fenetre: { w: 12, h: 16 },
    sens: "ligne",
    socle: { x: 0, w: 96 },
  },
  // Gerland : la halle industrielle, toit en sheds, cheminée cerclée, pilastres, baies cintrées.
  usine: {
    w: 140,
    h: 80,
    dessin: [
      r("facade", 122, 0, 8, 36),
      r("toit", 121, 6, 10, 2),
      r("toit", 121, 18, 10, 2),
      p("toit", "6,31 6,14 38,31 38,14 70,31 70,14 102,31 102,14 134,31"),
      r("facade", 6, 30, 128, 50),
      r("toit", 6, 30, 128, 1.5),
      r("ombre", 6, 36, 128, 1),
      r("ombre", 44, 37, 4, 43),
      r("ombre", 82, 37, 4, 43),
      r("toit", 6, 72, 128, 1),
    ],
    fixe: [
      { x: 24, y: 44, w: 16, h: 22, arc: true },
      { x: 62, y: 44, w: 16, h: 22, arc: true },
      { x: 100, y: 44, w: 16, h: 22, arc: true },
    ],
    zone: { x: 14, y: 40, w: 112, h: 28 },
    fenetre: { w: 16, h: 22, arc: true },
    sens: "ligne",
    socle: { x: 0, w: 140 },
  },
};

const ECART = 6;

/** Répartit `n` fenêtres sur la façade : à la main si le dessin prévoit ce nombre, sinon en
 * rangées centrées (ou en colonne, de bas en haut, pour une tour). */
export function disposer(g: Gabarit, n: number): Fen[] {
  if (n === g.fixe.length) return g.fixe;
  if (n === 0) return [];
  const { zone } = g;
  const arc = g.fenetre.arc;
  if (g.sens === "colonne") {
    const fh = Math.max(8, Math.min(g.fenetre.h, (zone.h - (n - 1) * ECART) / n));
    const fw = g.fenetre.w;
    const x = zone.x + (zone.w - fw) / 2;
    return Array.from({ length: n }, (_, i) => ({ x, y: zone.y + zone.h - (i + 1) * fh - i * ECART, w: fw, h: fh, arc }));
  }
  let fw = g.fenetre.w;
  const parRangee = Math.max(1, Math.floor((zone.w + ECART) / (fw + ECART)));
  const rangees = Math.ceil(n / parRangee);
  let fh = Math.min(g.fenetre.h, (zone.h - (rangees - 1) * ECART) / rangees);
  if (arc && fh < fw) fw = fh; // un arc garde au moins sa largeur en hauteur
  fh = Math.max(8, fh);
  const fenetres: Fen[] = [];
  for (let rangee = 0; rangee < rangees; rangee++) {
    const nombre = Math.min(parRangee, n - rangee * parRangee);
    const largeur = nombre * fw + (nombre - 1) * ECART;
    const x0 = zone.x + (zone.w - largeur) / 2;
    for (let i = 0; i < nombre; i++) {
      fenetres.push({ x: x0 + i * (fw + ECART), y: zone.y + rangee * (fh + ECART), w: fw, h: fh, arc });
    }
  }
  return fenetres;
}

export function cheminFenetre(f: Fen): string {
  const rayon = f.w / 2;
  return `M${f.x} ${f.y + rayon}a${rayon} ${rayon} 0 0 1 ${f.w} 0v${f.h - rayon}h${-f.w}z`;
}

// ---------------------------------------------------------------- le plan de la ville

export const PLAN = { w: 600, h: 650 };
// À la confluence, la Saône se jette dans le Rhône, qui continue seul vers le sud : les deux
// tracés se prolongent dans le même lit (coudes et bouts arrondis), sans tronçon à part dont
// les quais couperaient l'eau.
export const RIVIERES = [
  { points: "190,-10 190,88 160,148 160,330 180,400 214,520 254,600 254,660", largeur: 22 },
  { points: "566,-10 470,130 420,260 386,400 344,520 254,600 254,660", largeur: 34 },
];
export const PONTS = [
  [156, 58, 54],
  [128, 236, 58],
  [138, 352, 58],
  [406, 186, 70],
  [374, 326, 64],
  [221, 628, 66],
] as const;
export const NOMS_RIVIERES = [
  { nom: "Saône", x: 196, y: 165, angle: -90 },
  { nom: "Rhône", x: 486, y: 226, angle: -69 },
];

interface Emplacement {
  /** Catégorie prévue à cet endroit (plan de Traboules). */
  categorie: string;
  gabarit: NomGabarit;
  x: number;
  y: number;
  w: number;
  /** Complément de nom pour les phrases (« des trois défis de Fourvière »). */
  de: string | null;
}

// Du nord au sud : la liste se lit dans le même ordre que la carte.
const EMPLACEMENTS: Emplacement[] = [
  { categorie: "croix-rousse", gabarit: "canuts", x: 268, y: 22, w: 120, de: "de la Croix-Rousse" },
  { categorie: "fourviere", gabarit: "basilique", x: 13, y: 108, w: 125, de: "de Fourvière" },
  { categorie: "traboules", gabarit: "traboule", x: 226, y: 186, w: 110, de: "des Traboules" },
  { categorie: "part-dieu", gabarit: "tour", x: 512, y: 92, w: 70, de: "de la Part-Dieu" },
  { categorie: "vieux-lyon", gabarit: "renaissance", x: 12, y: 286, w: 120, de: "du Vieux Lyon" },
  { categorie: "terrain", gabarit: "ecole", x: 448, y: 376, w: 120, de: "du Terrain" },
  { categorie: "confluence", gabarit: "musee", x: 232, y: 372, w: 96, de: "de Confluence" },
  { categorie: "gerland", gabarit: "usine", x: 360, y: 512, w: 140, de: "de Gerland" },
];

export interface Quartier {
  categorie: Category;
  gabarit: Gabarit;
  x: number;
  y: number;
  w: number;
  de: string;
  /** Défis dans l'ordre où le fil les relie. */
  defis: ChallengeSummary[];
  fenetres: Fen[];
  resolus: number;
}

/** Le gabarit de chaque catégorie, dans l'ordre donné : celui de son emplacement sur le plan
 * (le premier libre pour une catégorie inconnue, comme dans `construireVille`), `null` pour
 * toutes au-delà de huit catégories. */
export function gabaritsDe(categories: string[]): (NomGabarit | null)[] {
  if (categories.length > EMPLACEMENTS.length) return categories.map(() => null);
  const libres = [...EMPLACEMENTS];
  const places = new Map<string, Emplacement>();
  for (const id of categories) {
    const index = libres.findIndex((e) => e.categorie === id);
    const [place] = index >= 0 ? libres.splice(index, 1) : [];
    if (place) places.set(id, place);
  }
  for (const id of categories) {
    const place = places.has(id) ? undefined : libres.shift();
    if (place) places.set(id, place);
  }
  return categories.map((id) => places.get(id)?.gabarit ?? null);
}

/** Les quartiers à dessiner, ou `null` si les catégories ne tiennent pas sur le plan. */
export function construireVille(
  categories: Category[],
  challenges: ChallengeSummary[],
  difficultes: string[],
): Quartier[] | null {
  if (categories.length === 0 || categories.length > EMPLACEMENTS.length) return null;
  const libres = [...EMPLACEMENTS];
  const places = new Map<string, Emplacement>();
  for (const cat of categories) {
    const index = libres.findIndex((e) => e.categorie === cat.id);
    const [place] = index >= 0 ? libres.splice(index, 1) : [];
    if (place) places.set(cat.id, place);
  }
  for (const cat of categories) {
    if (!places.has(cat.id)) places.set(cat.id, libres.shift() as Emplacement);
  }
  const ordre = ordonner(challenges, difficultes);
  return EMPLACEMENTS.flatMap((emplacement) => {
    const cat = categories.find((c) => places.get(c.id) === emplacement);
    if (!cat) return [];
    const gabarit = GABARITS[emplacement.gabarit];
    const defis = ordre.filter((c) => c.category === cat.id);
    return [
      {
        categorie: cat,
        gabarit,
        x: emplacement.x,
        y: emplacement.y,
        w: emplacement.w,
        de: emplacement.categorie === cat.id && emplacement.de ? emplacement.de : `de « ${cat.name} »`,
        defis,
        fenetres: disposer(gabarit, defis.length),
        resolus: defis.filter((d) => d.solved).length,
      },
    ];
  });
}

// ---------------------------------------------------------------- ordre de déblocage

/** Le défi qui ouvre celui-ci, de préférence dans la même catégorie. */
export function avant(c: ChallengeSummary, parId: Map<string, ChallengeSummary>): ChallengeSummary | null {
  const ids = c.after ?? [];
  const meme = ids.map((id) => parId.get(id)).find((x) => x?.category === c.category);
  return meme ?? parId.get(ids[0] ?? "") ?? null;
}

/** Les défis rangés quartier par quartier dans l'ordre où ils s'ouvrent : chaînes parcourues
 * depuis leurs racines, les plus faciles d'abord. */
export function ordonner(challenges: ChallengeSummary[], difficultes: string[]): ChallengeSummary[] {
  const parId = new Map(challenges.map((c) => [c.id, c]));
  const rang = (c: ChallengeSummary): number => {
    const i = difficultes.indexOf(c.difficulty ?? "");
    return i < 0 ? difficultes.length : i;
  };
  const trier = (a: ChallengeSummary, b: ChallengeSummary): number => rang(a) - rang(b) || a.value - b.value;
  const suivants = new Map<string, ChallengeSummary[]>();
  for (const c of challenges) {
    const a = avant(c, parId);
    if (a && a.category === c.category) suivants.set(a.id, [...(suivants.get(a.id) ?? []), c]);
  }
  const vus = new Set<string>();
  const resultat: ChallengeSummary[] = [];
  const suivre = (liste: ChallengeSummary[]): void => {
    for (const c of [...liste].sort(trier)) {
      if (vus.has(c.id)) continue;
      vus.add(c.id);
      resultat.push(c);
      suivre(suivants.get(c.id) ?? []);
    }
  };
  const categories = [...new Set(challenges.map((c) => c.category))];
  for (const cat of categories) {
    const dans = challenges.filter((c) => c.category === cat);
    suivre(dans.filter((c) => avant(c, parId)?.category !== cat));
    suivre(dans); // défis restants (cycle improbable) : en fin de quartier
  }
  return resultat;
}

// ---------------------------------------------------------------- le fil de soie

export interface Troncon {
  vers: string;
  etat: Etat;
  d: string;
}

/** Le fil d'un immeuble : il court d'un appui de fenêtre au suivant, avec du mou ; chaque
 * tronçon prend l'état de la fenêtre qu'il atteint. Un fil qui commence est noué à l'appui. */
export function fil(q: Quartier): Troncon[] {
  const parId = new Map(q.defis.map((d) => [d.id, d]));
  const sol = q.gabarit.h;
  return q.defis.flatMap((d, i) => {
    const f = q.fenetres[i];
    if (!f) return [];
    const precedent = (d.after ?? []).map((id) => parId.get(id)).find(Boolean);
    const etat = etatDe(d);
    if (!precedent) {
      const bx = f.x + f.w / 2;
      const by = f.y + f.h + 3;
      const chute = Math.max(2, Math.min(10, sol - by - 1));
      return [{ vers: d.id, etat, d: `M${bx} ${by}q-5 ${chute / 2} -3 ${chute}` }];
    }
    const pf = q.fenetres[q.defis.indexOf(precedent)];
    if (!pf) return [];
    if (f.y + f.h < pf.y) {
      // Fenêtre au-dessus (tour, rangée supérieure) : le fil longe le flanc.
      const x = Math.max(pf.x + pf.w, f.x + f.w) + 3;
      const y0 = pf.y + pf.h / 2;
      const y1 = f.y + f.h / 2;
      return [{ vers: d.id, etat, d: `M${x} ${y0}Q${x + 8} ${(y0 + y1) / 2} ${x} ${y1}` }];
    }
    const a0 = { x: pf.x + pf.w / 2, y: pf.y + pf.h + 3 };
    const a1 = { x: f.x + f.w / 2, y: f.y + f.h + 3 };
    const creux = Math.max(4, Math.min(24, 2 * (sol - Math.max(a0.y, a1.y) - 2)));
    return [{ vers: d.id, etat, d: `M${a0.x} ${a0.y}Q${(a0.x + a1.x) / 2} ${Math.max(a0.y, a1.y) + creux} ${a1.x} ${a1.y}` }];
  });
}

// ---------------------------------------------------------------- phrases du panneau

const RANGS = ["Premier", "Deuxième", "Troisième", "Quatrième", "Cinquième", "Sixième", "Septième", "Huitième", "Neuvième", "Dixième"];
const NOMBRES = ["zéro", "un", "deux", "trois", "quatre", "cinq", "six", "sept", "huit", "neuf", "dix"];
const nombre = (n: number): string => NOMBRES[n] ?? String(n);
const guillemets = (s: string): string => `« ${s} »`;

/** Ce que disent les règles de déblocage d'un défi, en phrases simples. */
export function ordreEnPhrases(
  d: ChallengeSummary,
  q: Quartier,
  tous: ChallengeSummary[],
  heure: (iso: string) => string,
): string {
  const parId = new Map(tous.map((c) => [c.id, c]));
  const i = q.defis.findIndex((x) => x.id === d.id);
  const phrases: string[] = [];
  const total = q.defis.length;
  phrases.push(
    total === 1
      ? `Seul défi ${q.de}.`
      : `${RANGS[i] ?? `${i + 1}e`} des ${nombre(total)} défis ${q.de}.`,
  );
  const precedent = avant(d, parId);
  if (d.opens_at) {
    phrases.push(`Ouvert à ${heure(d.opens_at)}${precedent ? `, après ${guillemets(precedent.name)}` : ""}.`);
  } else if (precedent) {
    phrases.push(`Après ${guillemets(precedent.name)}.`);
  }
  const ensuite = tous.filter((c) => (c.after ?? []).includes(d.id));
  const ici = ensuite.filter((c) => c.category === d.category);
  const ailleurs = [...new Set(ensuite.filter((c) => c.category !== d.category).map((c) => c.category))];
  const noms = ici.map((c) => guillemets(c.name)).join(" et ");
  if (ici.length && ailleurs.length) {
    phrases.push(`Ouvre ensuite ${noms} et les premiers défis des ${nombre(ailleurs.length)} autres quartiers.`);
  } else if (ici.length) {
    phrases.push(`Ouvre ensuite ${noms}.`);
  } else if (ailleurs.length) {
    phrases.push(`Ouvre ensuite les premiers défis des ${nombre(ailleurs.length)} autres quartiers.`);
  } else if (i === total - 1 && total > 1) {
    phrases.push(`C'est le dernier défi ${q.de}.`);
  }
  return phrases.join(" ");
}

// ---------------------------------------------------------------- la ville éteinte (décor)

/** La ville avant le jeu : mêmes immeubles, toutes les fenêtres tenues par LUMEN. Sert de
 * décor (accueil, connexion) ; aucune donnée de défi n'y figure. */
export function villeEteinte(categories: Category[]): Quartier[] | null {
  const factices = categories.flatMap((cat) => {
    const emplacement = EMPLACEMENTS.find((e) => e.categorie === cat.id) ?? null;
    const n = emplacement ? GABARITS[emplacement.gabarit].fixe.length : 3;
    return Array.from({ length: n }, (_, i): ChallengeSummary => ({
      id: `${cat.id}-${i}`,
      name: "",
      category: cat.id,
      difficulty: null,
      tags: [],
      value: 0,
      solves: 0,
      solved: false,
      locked: true,
      locked_message: null,
      after: [],
    }));
  });
  return construireVille(categories, factices, []);
}
