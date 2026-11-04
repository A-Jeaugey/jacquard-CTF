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

export type NomGabarit = "canuts" | "basilique" | "traboule" | "tour" | "renaissance" | "ecole" | "musee" | "usine";

export const GABARITS: Record<NomGabarit, Gabarit> = {
  // Immeuble de canuts : hautes fenêtres des ateliers.
  canuts: {
    w: 120,
    h: 92,
    dessin: [r("toit", 22, 2, 8, 14), r("toit", 90, 0, 8, 16), r("facade", 6, 14, 108, 78), r("toit", 2, 12, 116, 4)],
    fixe: [
      { x: 14, y: 30, w: 16, h: 36 },
      { x: 39, y: 30, w: 16, h: 36 },
      { x: 65, y: 30, w: 16, h: 36 },
      { x: 90, y: 30, w: 16, h: 36 },
    ],
    zone: { x: 14, y: 24, w: 92, h: 60 },
    fenetre: { w: 16, h: 36 },
    sens: "ligne",
    socle: { x: 0, w: 120 },
  },
  // Basilique : flèche de la tour métallique, façade et tours crénelées, fenêtres en arc.
  basilique: {
    w: 130,
    h: 96,
    dessin: [
      p("toit", "5,96 13,4 21,96"),
      r("toit", 9, 40, 8, 2),
      r("toit", 7, 66, 12, 2),
      r("facade", 36, 44, 80, 52),
      p("facade", "52,45 76,26 100,45"),
      r("facade", 28, 28, 16, 68),
      r("facade", 108, 28, 16, 68),
      r("toit", 28, 22, 4, 6),
      r("toit", 34, 22, 4, 6),
      r("toit", 40, 22, 4, 6),
      r("toit", 108, 22, 4, 6),
      r("toit", 114, 22, 4, 6),
      r("toit", 120, 22, 4, 6),
    ],
    fixe: [
      { x: 46, y: 56, w: 14, h: 26, arc: true },
      { x: 69, y: 56, w: 14, h: 26, arc: true },
      { x: 92, y: 56, w: 14, h: 26, arc: true },
    ],
    zone: { x: 44, y: 50, w: 64, h: 40 },
    fenetre: { w: 14, h: 26, arc: true },
    sens: "ligne",
    socle: { x: 24, w: 106 },
  },
  // Immeuble traversé par une traboule (passage voûté au rez-de-chaussée).
  traboule: {
    w: 110,
    h: 88,
    dessin: [p("toit", "4,22 55,6 106,22"), r("facade", 8, 20, 94, 68), { el: "path", c: "passage", d: "M41 88v-12a14 14 0 0 1 28 0v12z" }],
    fixe: [
      { x: 20, y: 32, w: 14, h: 22 },
      { x: 48, y: 32, w: 14, h: 22 },
      { x: 76, y: 32, w: 14, h: 22 },
    ],
    zone: { x: 16, y: 28, w: 78, h: 42 },
    fenetre: { w: 14, h: 22 },
    sens: "ligne",
    socle: { x: 0, w: 110 },
  },
  // Tour : on la gravit, premier défi en bas, dernier en haut. Sa couronne reste à LUMEN.
  tour: {
    w: 70,
    h: 206,
    dessin: [r("toit", 0, 184, 70, 22), r("facade", 20, 40, 30, 166), p("couronne", "20,40 35,2 50,40")],
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
  // Maisons Renaissance à pignons, fenêtres en arc.
  renaissance: {
    w: 120,
    h: 96,
    dessin: [
      p("facade", "4,96 4,36 22,22 40,36 40,96"),
      p("facade", "41,96 41,24 60,6 79,24 79,96"),
      p("facade", "80,96 80,40 97,28 114,40 114,96"),
      r("toit", 40, 24, 1, 72),
      r("toit", 79, 28, 1, 68),
    ],
    fixe: [
      { x: 15, y: 52, w: 14, h: 26, arc: true },
      { x: 53, y: 38, w: 14, h: 26, arc: true },
      { x: 90, y: 56, w: 14, h: 26, arc: true },
    ],
    zone: { x: 10, y: 44, w: 100, h: 44 },
    fenetre: { w: 14, h: 26, arc: true },
    sens: "ligne",
    socle: { x: 0, w: 120 },
  },
  // Bâtiment bas et large (l'école).
  ecole: {
    w: 120,
    h: 70,
    dessin: [r("facade", 6, 20, 108, 50), r("toit", 2, 16, 116, 4)],
    fixe: [
      { x: 18, y: 34, w: 20, h: 18 },
      { x: 50, y: 34, w: 20, h: 18 },
      { x: 82, y: 34, w: 20, h: 18 },
    ],
    zone: { x: 14, y: 28, w: 92, h: 36 },
    fenetre: { w: 20, h: 18 },
    sens: "ligne",
    socle: { x: 0, w: 120 },
  },
  // Musée aux volumes obliques (Confluence).
  musee: {
    w: 96,
    h: 76,
    dessin: [p("facade", "6,76 14,32 46,12 90,34 84,76")],
    fixe: [
      { x: 22, y: 42, w: 14, h: 20 },
      { x: 41, y: 42, w: 14, h: 20 },
      { x: 60, y: 42, w: 14, h: 20 },
    ],
    zone: { x: 18, y: 38, w: 62, h: 32 },
    fenetre: { w: 14, h: 20 },
    sens: "ligne",
    socle: { x: 0, w: 96 },
  },
  // Usine à toit en sheds et cheminée (Gerland).
  usine: {
    w: 140,
    h: 80,
    dessin: [r("toit", 122, 0, 8, 36), r("facade", 6, 30, 128, 50), p("toit", "6,31 6,14 38,31 38,14 70,31 70,14 102,31 102,14 134,31")],
    fixe: [
      { x: 24, y: 46, w: 16, h: 22 },
      { x: 62, y: 46, w: 16, h: 22 },
      { x: 100, y: 46, w: 16, h: 22 },
    ],
    zone: { x: 14, y: 38, w: 112, h: 36 },
    fenetre: { w: 16, h: 22 },
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
export const RIVIERES = [
  { points: "190,-10 190,88 160,148 160,330 180,400 214,520 254,600", largeur: 22 },
  { points: "566,-10 470,130 420,260 386,400 344,520 254,600", largeur: 34 },
  { points: "254,600 254,660", largeur: 44 },
];
export const PONTS = [
  [156, 58, 54],
  [128, 236, 58],
  [138, 352, 58],
  [406, 186, 70],
  [374, 326, 64],
  [218, 628, 72],
] as const;
export const NOMS_RIVIERES = [
  { nom: "Saône", x: 216, y: 48, angle: -90 },
  { nom: "Rhône", x: 474, y: 232, angle: -69 },
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
  { categorie: "fourviere", gabarit: "basilique", x: 8, y: 108, w: 130, de: "de Fourvière" },
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
