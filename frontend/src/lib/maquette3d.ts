// La ville en volume (frontend/DESIGN.md) : la maquette du plan de Lyon rendue en temps réel.
// Le fichier public/ville/lyon.glb porte les volumes (planche, fleuves, ponts, immeubles) ;
// les fenêtres des défis et les fils de soie sont posés ici, d'après les défis de l'équipe.
// Ce module est chargé à la demande (three.js pèse lourd) : rien d'autre ne doit l'importer
// que Ville3D.svelte, par un import dynamique.
//
// Deux dispositions de la même maquette : « plan » (le plan de Lyon, les immeubles à leur place
// entre les fleuves) et « quai » (les huit immeubles alignés face à la Saône, comme au début de
// la bande-annonce ; décor de l'accueil et des pages d'accès).
//
// Repère : x vers l'est, y vers le haut, z vers le sud (vers la caméra). Une unité = un mètre de
// maquette ; une unité du dessin d'un immeuble (lib/ville.ts) = 10 cm.

import {
  BoxGeometry,
  BufferGeometry,
  CatmullRomCurve3,
  Color,
  DepthTexture,
  DirectionalLight,
  DoubleSide,
  Float32BufferAttribute,
  Fog,
  Group,
  HalfFloatType,
  HemisphereLight,
  InstancedMesh,
  Material,
  Matrix4,
  Mesh,
  MeshBasicMaterial,
  MeshStandardMaterial,
  Object3D,
  PCFShadowMap,
  PerspectiveCamera,
  PlaneGeometry,
  PointLight,
  Scene,
  Shape,
  ShapeGeometry,
  TubeGeometry,
  UnsignedIntType,
  Vector2,
  Vector3,
  WebGLRenderer,
  WebGLRenderTarget,
} from "three";
import { Line2 } from "three/addons/lines/Line2.js";
import { LineGeometry } from "three/addons/lines/LineGeometry.js";
import { LineMaterial } from "three/addons/lines/LineMaterial.js";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { Reflector } from "three/addons/objects/Reflector.js";
import { EffectComposer } from "three/addons/postprocessing/EffectComposer.js";
import { OutputPass } from "three/addons/postprocessing/OutputPass.js";
import { RenderPass } from "three/addons/postprocessing/RenderPass.js";
import { UnrealBloomPass } from "three/addons/postprocessing/UnrealBloomPass.js";

import type { Etat, Fen } from "./ville";

// ---------------------------------------------------------------- ce que la page fournit

export interface FenetreScene {
  /** Identifiant du défi. */
  id: string;
  etat: Etat;
  fen: Fen;
  /** Fenêtre ni gagnée ni tenue par LUMEN : sombre, sans cerne (grand écran). */
  eteinte?: boolean;
}

export interface FilScene {
  /** Défi atteint par ce tronçon : il en prend l'état. */
  vers: string;
  etat: Etat;
  /** Le tracé, en unités du dessin de l'immeuble. */
  points: [number, number][];
}

export interface QuartierScene {
  /** L'immeuble de la maquette (son emplacement sur le plan : « croix-rousse », « gerland »…). */
  immeuble: string;
  /** La catégorie affichée à cet emplacement. */
  categorie: string;
  fenetres: FenetreScene[];
  fils: FilScene[];
  /** Vrai si les fenêtres sont celles du dessin : leurs niches existent dans la maquette. */
  nominal: boolean;
  /** Zone des fenêtres sur la façade, à recouvrir quand elles ne sont pas celles du dessin. */
  zone: { x: number; y: number; w: number; h: number };
}

/** Ce que la caméra regarde : toute la ville, un quartier, ou la fenêtre d'un défi. */
export interface Vue {
  quartier: string | null;
  defi: string | null;
}

/** La part de la toile recouverte par l'interface, de chaque côté, en pixels CSS. */
export interface Marges {
  haut: number;
  droite: number;
  bas: number;
  gauche: number;
}

export interface Rectangle {
  x: number;
  y: number;
  w: number;
  h: number;
}

/** Où sont les immeubles et les fenêtres à l'écran (pixels CSS de la toile) : la page y pose
 * ses boutons et ses liens. */
export interface Reperes {
  quartiers: Record<string, Rectangle & { profondeur: number; pied: { x: number; y: number } }>;
  fenetres: Record<string, Rectangle>;
}

export interface Options {
  /** Mouvement réduit : la caméra change de vue d'un coup, les lumières aussi. */
  calme: boolean;
  surReperes?: (reperes: Reperes) => void;
  /** « plan » (par défaut) ou « quai ». */
  disposition?: "plan" | "quai";
  /** La maquette tourne lentement d'elle-même (grand écran). */
  ronde?: boolean;
  /** Vue du quai : la hauteur du quai dans l'image (0 en haut, 1 en bas). */
  sol?: number;
}

// ---------------------------------------------------------------- couleurs et matières

const U = 0.1;
const COULEURS = {
  table: "#16151c",
  nuit: "#2e2936",
  eau: "#131419",
  claire: "#ede7df",
  douce: "#bcb3c2",
  lumignon: "#f5a23d",
  lumen: "#ddebf7",
  vitre: "#0d0e14",
  menuiserie: "#17151c",
};
/** Les matières de la maquette, par nom (celles de video/3d/construire.py du pack Traboules). */
const MATIERES: Record<string, { couleur: string; rugosite: number; metal?: number }> = {
  corniche: { couleur: "#a69eb0", rugosite: 0.7 },
  socle: { couleur: "#6d6577", rugosite: 0.82 },
  toiture: { couleur: "#4c4759", rugosite: 0.6, metal: 0.1 },
  // Mates : une vitre brillante renverrait la lueur du quartier en un point blanc.
  porte: { couleur: "#0b0b0e", rugosite: 0.7 },
  vitre: { couleur: COULEURS.vitre, rugosite: 0.65 },
  menuiserie: { couleur: COULEURS.menuiserie, rugosite: 0.5 },
  "métal": { couleur: "#8a93a0", rugosite: 0.4, metal: 0.3 },
  "métal sombre": { couleur: "#444b59", rugosite: 0.35, metal: 0.3 },
  fonte: { couleur: "#4d4958", rugosite: 0.45, metal: 0.25 },
  planche: { couleur: "#3d3847", rugosite: 0.85 },
};
const PIERRES: Record<string, string[]> = {
  fourviere: ["#9792a3"],
  "vieux-lyon": ["#99878f", "#9b8d88", "#908598"],
  traboules: ["#8d8496"],
  "croix-rousse": ["#978a8c"],
  "part-dieu": ["#7c7587"],
  terrain: ["#8b8896"],
  gerland: ["#917c80"],
  confluence: ["#8a93a0"],
};

/** Une lumière qui se voit telle quelle (fenêtre, fil, rive) : sa couleur, plus ou moins forte.
 * Au-dessus du seuil de l'éclat, elle rayonne. */
function lueur(couleur: string, force: number): Color {
  return new Color(couleur).multiplyScalar(force);
}
const LUMIERES: Record<Etat, Color> = {
  resolu: lueur(COULEURS.lumignon, 1.2),
  verrouille: lueur(COULEURS.lumen, 0.82),
  disponible: new Color(COULEURS.vitre),
};
/** Les petites fenêtres des toits lointains (vue du quai). */
const FENETRE_LOINTAINE = { eteinte: new Color("#3a3444").multiplyScalar(0.55), allumee: lueur(COULEURS.lumignon, 0.85) };

/** Pierre de taille : de longues assises horizontales, comme les hachures des immeubles du
 * site. Le trait s'efface de loin, là où il serait plus fin qu'un pixel. */
function pierre(couleur: string, rugosite: number, rang: number): MeshStandardMaterial {
  const matiere = new MeshStandardMaterial({ color: couleur, roughness: rugosite });
  matiere.onBeforeCompile = (shader) => {
    shader.vertexShader = shader.vertexShader
      .replace("#include <common>", "#include <common>\nvarying vec3 vAssise;")
      .replace(
        "#include <project_vertex>",
        "#include <project_vertex>\nvAssise = vec3((modelMatrix * vec4(transformed, 1.0)).y, normalize(mat3(modelMatrix) * objectNormal).y, 0.0);",
      );
    shader.fragmentShader = shader.fragmentShader
      .replace("#include <common>", "#include <common>\nvarying vec3 vAssise;")
      .replace(
        "#include <color_fragment>",
        `#include <color_fragment>
        float assise = vAssise.x / ${rang.toFixed(3)};
        float finesse = fwidth(assise);
        float joint = (1.0 - smoothstep(0.0, max(0.06, finesse * 1.5), fract(assise))) * clamp(1.0 - finesse * 2.5, 0.0, 1.0);
        diffuseColor.rgb *= 1.0 - 0.38 * joint * (1.0 - smoothstep(0.3, 0.6, abs(vAssise.y)));`,
      );
  };
  return matiere;
}

// ---------------------------------------------------------------- mouvements

const adoucir = (k: number): number => (k < 0.5 ? 4 * k * k * k : 1 - (-2 * k + 2) ** 3 / 2);
const borner = (v: number, min: number, max: number): number => Math.min(max, Math.max(min, v));
const entre = (a: number, b: number, k: number): number => a + (b - a) * k;

interface Pose {
  cible: Vector3;
  distance: number;
  /** Angle au-dessus de l'horizon, et angle autour de la verticale (0 = plein nord). */
  pente: number;
  lacet: number;
  /** Décalage de l'image, en part de la toile, pour centrer le sujet dans la place libre. */
  decalage: Vector2;
}

interface Transition {
  depuis: Pose;
  vers: Pose;
  debut: number;
  duree: number;
}

interface Fenetre {
  id: string;
  etat: Etat;
  eteinte: boolean;
  vitre: Mesh<BufferGeometry, MeshBasicMaterial>;
  contour: Line2;
  /** Coins de la baie sur la façade, dans le repère de l'immeuble. */
  coins: Vector3[];
  couleur: Color;
  depuis: Color;
  change: number;
}

interface Fil {
  cle: string;
  etat: Etat;
  objet: Mesh<TubeGeometry, Material>;
  indices: number;
  /** Instant où le fil a commencé à se tendre (0 : déjà tendu). */
  tendu: number;
}

interface Meta {
  vitres: number[];
  auvents: number[][];
  boite: [number[], number[]];
  centre: number[];
  w: number;
  h: number;
}

interface Immeuble {
  id: string;
  meta: Meta;
  /** Le nœud de l'immeuble dans la maquette : son origine est celle de son dessin (le coin
   * gauche de la façade, au sol). Les fenêtres, les fils et la lueur y sont attachés : déplacer
   * la racine déplace tout. */
  racine: Object3D;
  /** Sa boîte et le point visé, par rapport à la racine. */
  mini: Vector3;
  maxi: Vector3;
  centre: Vector3;
  groupe: Group;
  pierre: Material | null;
  lampe: PointLight;
  fenetres: Fenetre[];
  fils: Fil[];
  /** La signature de ce qui est posé, pour ne reconstruire que ce qui change. */
  trace: string;
  cache: Mesh | null;
}

const RAYON_FIL = 0.055;
const ECART_FIL = 1.8;
const DEGRE = Math.PI / 180;
const PENTE_VILLE = 46 * DEGRE;
/** Sur une toile en hauteur (téléphone), la ville se regarde de plus haut : elle remplit l'image. */
const PENTE_VILLE_HAUTE = 62 * DEGRE;
const PENTE_QUARTIER = 28 * DEGRE;
/** D'où l'on regarde chaque immeuble, en degrés à l'est du plein sud : de trois quarts, du côté
 * où aucun voisin ne passe devant la caméra (un fleuve, le bord de la planche). */
const LACETS: Record<string, number> = {
  "croix-rousse": 24,
  fourviere: 24,
  traboules: 24,
  "part-dieu": -24,
  "vieux-lyon": 14,
  terrain: 24,
  confluence: 14,
  gerland: -14,
};
const CHAMP = 35.6;

/** L'ordre des immeubles sur le quai et l'espace avant chacun, en unités du dessin (les mêmes
 * que dans Panorama.svelte). */
const RANGEE: [string, number][] = [
  ["fourviere", 0],
  ["vieux-lyon", 16],
  ["traboules", 12],
  ["croix-rousse", 20],
  ["confluence", 24],
  ["part-dieu", 18],
  ["terrain", 22],
  ["gerland", 16],
];
/** Le quai : son bord est à 2,6 m devant les façades, l'eau à 1,6 m sous lui. */
const BORD_QUAI = 2.6;
const NIVEAU_EAU = -1.6;
const HAUTEUR_OEIL = 3.2;

export class Maquette {
  private rendu: WebGLRenderer;
  private scene = new Scene();
  private camera = new PerspectiveCamera(CHAMP, 1, 1, 900);
  private composition: EffectComposer;
  private eclat: UnrealBloomPass;
  private immeubles = new Map<string, Immeuble>();
  private quartiers: QuartierScene[] = [];
  private vue: Vue = { quartier: null, defi: null };
  private marges: Marges = { haut: 0, droite: 0, bas: 0, gauche: 0 };
  private pose: Pose | null = null;
  private transition: Transition | null = null;
  private orbite = new Vector2();
  private orbiteVoulue = new Vector2();
  private survole: string | null = null;
  private largeur = 1;
  private hauteur = 1;
  private image = 0;
  private dernierInstant = 0;
  private bouge = true;
  private detruite = false;
  private lignes: LineMaterial[] = [];
  private observateur: ResizeObserver;
  private lune = new DirectionalLight(new Color(0.72, 0.75, 1.0), 1.15);
  private quai: boolean;
  /** Vue du quai : largeur de la rangée, filet ambre et fenêtres lointaines (ils suivent la
   * part des défis résolus). */
  private rangee = 0;
  private filetAmbre: Mesh | null = null;
  private lointaines: InstancedMesh | null = null;
  private part = 0;
  private partVoulue = 0;
  private dernierRendu = 0;

  /** Charge la maquette et prépare la scène. Échoue si WebGL 2 n'est pas disponible. */
  static async creer(toile: HTMLCanvasElement, options: Options): Promise<Maquette> {
    const base = import.meta.env.BASE_URL;
    const [gltf, meta] = await Promise.all([
      new GLTFLoader().loadAsync(`${base}ville/lyon.glb`),
      fetch(`${base}ville/lyon.json`).then((reponse) => {
        if (!reponse.ok) throw new Error("lyon.json introuvable");
        return reponse.json() as Promise<{ quartiers: Record<string, Meta> }>;
      }),
    ]);
    return new Maquette(toile, options, gltf.scene, meta.quartiers);
  }

  private constructor(
    private toile: HTMLCanvasElement,
    private options: Options,
    modele: Group,
    meta: Record<string, Meta>,
  ) {
    this.quai = options.disposition === "quai";
    this.rendu = new WebGLRenderer({ canvas: toile, antialias: false, powerPreference: "high-performance" });
    if (!this.rendu.capabilities.isWebGL2) throw new Error("WebGL 2 indisponible");
    this.rendu.shadowMap.enabled = true;
    this.rendu.shadowMap.type = PCFShadowMap;
    this.rendu.shadowMap.autoUpdate = false;

    const nuit = new Color(this.quai ? COULEURS.nuit : COULEURS.table);
    this.scene.background = nuit;
    if (!this.quai) this.scene.fog = new Fog(nuit, 190, 520);
    this.construireDecor(modele, meta);
    if (this.quai) this.alignerSurLeQuai(modele);
    this.rendu.shadowMap.needsUpdate = true;

    // L'éclat des lumières : ce qui dépasse le seuil rayonne, comme dans la bande-annonce.
    // Une profondeur précise : l'eau est posée à trois centimètres de ses rives.
    const tampon = new WebGLRenderTarget(1, 1, { type: HalfFloatType, samples: 4, depthTexture: new DepthTexture(1, 1, UnsignedIntType) });
    this.composition = new EffectComposer(this.rendu, tampon);
    this.composition.addPass(new RenderPass(this.scene, this.camera));
    this.eclat = new UnrealBloomPass(new Vector2(1, 1), 0.4, 0.4, 0.5);
    this.composition.addPass(this.eclat);
    this.composition.addPass(new OutputPass());

    this.observateur = new ResizeObserver(() => this.redimensionner());
    this.observateur.observe(toile);
    this.redimensionner();
  }

  // -------------------------------------------------------------- décor

  private construireDecor(modele: Group, meta: Record<string, Meta>): void {
    const matieres = new Map<string, Material>();
    const matiere = (nom: string): Material => {
      let m = matieres.get(nom);
      if (!m) {
        const simple = MATIERES[nom];
        const taille = /^pierre (.+) (\d)$/.exec(nom);
        if (nom === "rive" || nom === "couronne") m = new MeshBasicMaterial({ color: lueur(COULEURS.lumen, nom === "rive" ? 0.92 : 1.05) });
        // L'eau passe toujours devant sa rive, même vue de très loin.
        else if (nom === "eau") m = new MeshStandardMaterial({ color: "#0c0d12", roughness: 0.3, polygonOffset: true, polygonOffsetFactor: -2, polygonOffsetUnits: -2 });
        else if (taille) m = pierre(PIERRES[taille[1] ?? ""]?.[Number(taille[2]) - 1] ?? "#8d8496", 0.82, 0.3);
        else if (nom === "socle") m = pierre("#6d6577", 0.82, 0.42);
        else if (simple) m = new MeshStandardMaterial({ color: simple.couleur, roughness: simple.rugosite, metalness: simple.metal ?? 0 });
        else m = new MeshStandardMaterial({ color: "#6d6577", roughness: 0.8 });
        m.name = nom;
        // Les surfaces sans épaisseur (eau, vitres, portes, rives) se voient des deux côtés.
        if (["eau", "rive", "vitre", "porte"].includes(nom)) m.side = DoubleSide;
        matieres.set(nom, m);
      }
      return m;
    };
    const donnee = (objet: Object3D, cle: string): string | null => {
      for (let o: Object3D | null = objet; o; o = o.parent) {
        const valeur = o.userData[cle] as unknown;
        if (typeof valeur === "string") return valeur;
      }
      return null;
    };

    const pierres = new Map<string, Material>();
    modele.traverse((objet) => {
      if (!(objet instanceof Mesh)) return;
      const nom = (objet.material as Material).name;
      objet.material = matiere(nom);
      const lumineux = nom === "rive" || nom === "couronne";
      objet.castShadow = !lumineux && nom !== "eau" && nom !== "planche";
      objet.receiveShadow = !lumineux;
      const quartier = donnee(objet, "quartier");
      if (quartier && nom.startsWith("pierre") && !pierres.has(quartier)) pierres.set(quartier, objet.material as Material);
    });
    this.scene.add(modele);

    if (!this.quai) {
      const table = new Mesh(new PlaneGeometry(4000, 4000), new MeshStandardMaterial({ color: "#1d1a23", roughness: 0.9 }));
      table.rotation.x = -Math.PI / 2;
      table.position.set(30, -0.8, 32);
      table.receiveShadow = true;
      this.scene.add(table);
    }

    // La lune (d'où viennent les ombres) et le ciel de nuit.
    this.lune.position.set(30 - 0.55 * 90, 0.7 * 90, 32 + 0.45 * 90);
    this.lune.target.position.set(30, 0, 32);
    this.lune.castShadow = true;
    this.lune.shadow.mapSize.set(4096, 4096);
    this.lune.shadow.bias = -0.0006;
    this.lune.shadow.normalBias = 0.03;
    const ombre = this.lune.shadow.camera;
    ombre.left = -52;
    ombre.right = 52;
    ombre.top = 52;
    ombre.bottom = -52;
    ombre.near = 10;
    ombre.far = 220;
    this.scene.add(this.lune, this.lune.target, new HemisphereLight("#7f86c4", "#241f2c", 0.42));

    const racines = new Map<string, Object3D>();
    modele.traverse((objet) => {
      const quartier = objet.userData.quartier as unknown;
      if (typeof quartier === "string" && objet.userData.role === undefined) racines.set(quartier, objet);
    });
    for (const [id, m] of Object.entries(meta)) {
      const racine = racines.get(id);
      if (!racine) continue;
      const origine = racine.position.clone();
      const groupe = new Group();
      groupe.name = `poses.${id}`;
      racine.add(groupe);
      const centre = new Vector3(...(m.centre as [number, number, number])).sub(origine);
      // La lueur chaude devant un quartier gagné : elle grandit avec les défis résolus.
      const lampe = new PointLight(new Color(1.0, 0.62, 0.28), 0, 26, 2);
      lampe.position.set(centre.x, 3.2, centre.z + 5.5);
      racine.add(lampe);
      this.immeubles.set(id, {
        id,
        meta: m,
        racine,
        mini: new Vector3(...(m.boite[0] as [number, number, number])).sub(origine),
        maxi: new Vector3(...(m.boite[1] as [number, number, number])).sub(origine),
        centre,
        groupe,
        pierre: pierres.get(id) ?? null,
        lampe,
        fenetres: [],
        fils: [],
        trace: "",
        cache: null,
      });
    }
  }

  /** La vue du quai : les immeubles en rangée face à la Saône, le quai et son filet de lumière,
   * les réverbères, les toits lointains, le ciel, et l'eau où tout se reflète. */
  private alignerSurLeQuai(modele: Group): void {
    modele.traverse((objet) => {
      if (typeof objet.userData.role === "string" && objet.userData.quartier === undefined) objet.visible = false;
    });
    let x = 0;
    for (const [id, ecart] of RANGEE) {
      const immeuble = this.immeubles.get(id);
      if (!immeuble) continue;
      x += ecart;
      immeuble.racine.position.set(x * U, 0, 0);
      x += immeuble.meta.w;
    }
    this.rangee = x * U;
    const milieu = this.rangee / 2;
    const decor = new Group();
    decor.name = "quai";
    this.scene.add(decor);
    const boite = (matiere: Material, x0: number, x1: number, y0: number, y1: number, z0: number, z1: number, ombre = true): Mesh => {
      const objet = new Mesh(new BoxGeometry(x1 - x0, y1 - y0, z1 - z0), matiere);
      objet.position.set((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2);
      objet.receiveShadow = ombre;
      decor.add(objet);
      return objet;
    };
    const gauche = -260;
    const droite = this.rangee + 260;
    boite(pierre("#7b7386", 0.82, 0.5), gauche, droite, NIVEAU_EAU - 1.4, 0, -140, BORD_QUAI);
    boite(new MeshStandardMaterial({ color: "#5d5668", roughness: 0.75 }), gauche, droite, 0, 0.005, -140, BORD_QUAI - 0.5);
    boite(new MeshStandardMaterial({ color: "#a69eb0", roughness: 0.7 }), gauche, droite, -0.16, 0.03, BORD_QUAI - 0.5, BORD_QUAI + 0.1);
    // Le filet de lumière du quai : froid sous LUMEN ; l'ambre le recouvre depuis la gauche à
    // mesure que la ville est rendue.
    boite(new MeshBasicMaterial({ color: lueur(COULEURS.lumen, 0.95) }), -70, this.rangee + 70, -0.34, -0.18, BORD_QUAI + 0.1, BORD_QUAI + 0.14, false);
    const ambre = new Mesh(new BoxGeometry(this.rangee + 140, 0.18, 0.03).translate((this.rangee + 140) / 2, 0, 0), new MeshBasicMaterial({ color: lueur(COULEURS.lumignon, 1.25) }));
    ambre.position.set(-70, -0.26, BORD_QUAI + 0.155);
    ambre.scale.x = 0.0001;
    decor.add(ambre);
    this.filetAmbre = ambre;

    // Les réverbères du quai : un fût de fonte, une lanterne chaude.
    const places: number[] = [];
    for (let px = -49.3; px < this.rangee + 51; px += 5.8) places.push(px);
    const fonte = new MeshStandardMaterial({ color: "#4d4958", roughness: 0.45, metalness: 0.25 });
    const futs = new InstancedMesh(new BoxGeometry(0.08, 2.65, 0.08).translate(0, 1.325, 0), fonte, places.length);
    const lanternes = new InstancedMesh(new BoxGeometry(0.2, 0.31, 0.2).translate(0, 2.8, 0), new MeshBasicMaterial({ color: new Color(1.0, 0.72, 0.42).multiplyScalar(0.8) }), places.length);
    places.forEach((px, i) => {
      const place = new Matrix4().makeTranslation(px, 0, 1.7);
      futs.setMatrixAt(i, place);
      lanternes.setMatrixAt(i, place);
    });
    futs.castShadow = true;
    decor.add(futs, lanternes);

    // Les toits lointains, sur trois plans : des silhouettes, que le déplacement de la caméra
    // fait glisser derrière le quai. Rangée déterministe (la même graine que le panorama à plat).
    let graine = 7;
    const hasard = (): number => {
      graine = (graine * 16807) % 2147483647;
      return graine / 2147483647;
    };
    const teintes = ["#2b2734", "#2a2735", "#292736"].map((c) => new MeshBasicMaterial({ color: c }));
    const carreaux: Matrix4[] = [];
    for (let plan = 0; plan < 3; plan++) {
      const recul = [17, 30, 45][plan] ?? 17;
      const grandeur = 0.9 + plan * 0.22;
      for (let px = milieu - 190 - plan * 30; px < milieu + 190 + plan * 30; ) {
        const largeur = (3.4 + hasard() * 5.6) * grandeur;
        const hauteur = (5 + hasard() * 12) * grandeur * 1.15;
        const profondeur = 5 + hasard() * 4;
        const z = -recul - hasard() * 2.8;
        boite(teintes[plan] as Material, px, px + largeur, 0, hauteur, z - profondeur, z, false);
        for (let fy = hauteur - 1.6 * grandeur; fy > 1.5; fy -= 1.4 * grandeur) {
          for (let fx = px + 0.8 * grandeur; fx < px + largeur - 0.8 * grandeur; fx += 1.2 * grandeur) {
            if (hasard() < 0.2) carreaux.push(new Matrix4().makeTranslation(fx, fy, z + 0.03).scale(new Vector3(grandeur, grandeur, 1)));
          }
        }
        px += largeur + hasard() * 0.6;
      }
    }
    boite(teintes[2] as Material, gauche - 200, droite + 200, 0, 2.6, -70, -64, false);
    // Leurs fenêtres : éteintes, elles s'allument une à une avec la progression de la ville.
    const lointaines = new InstancedMesh(new PlaneGeometry(0.4, 0.6), new MeshBasicMaterial(), carreaux.length);
    carreaux
      .map((place) => ({ place, rang: hasard() }))
      .sort((a, b) => a.rang - b.rang)
      .forEach(({ place }, i) => {
        lointaines.setMatrixAt(i, place);
        lointaines.setColorAt(i, FENETRE_LOINTAINE.eteinte);
      });
    decor.add(lointaines);
    this.lointaines = lointaines;

    // Le ciel : une nuit violette, plus claire à l'horizon ; en haut, la couleur de la page.
    const ciel = new PlaneGeometry(5000, 900, 1, 6);
    const hauteurs = ciel.getAttribute("position");
    const couleurs: number[] = [];
    const bas = new Color("#54496c");
    const mi = new Color("#3a3348");
    const haut = new Color(COULEURS.nuit);
    for (let i = 0; i < hauteurs.count; i++) {
      const y = hauteurs.getY(i) + 440;
      const c = y < 40 ? bas.clone().lerp(mi, borner(y / 40, 0, 1)) : mi.clone().lerp(haut, borner((y - 40) / 110, 0, 1));
      couleurs.push(c.r, c.g, c.b);
    }
    ciel.setAttribute("color", new Float32BufferAttribute(couleurs, 3));
    const voute = new Mesh(ciel, new MeshBasicMaterial({ vertexColors: true }));
    voute.position.set(milieu, 440 - 10, -420);
    decor.add(voute);

    // La Saône : un miroir sombre, où les reflets s'étirent de haut en bas.
    const eau = new Reflector(new PlaneGeometry(1600, 500), {
      textureWidth: 1024,
      textureHeight: 512,
      clipBias: 0.002,
      color: 0x8f8f9c,
      shader: {
        name: "Saone",
        uniforms: { color: { value: null }, tDiffuse: { value: null }, textureMatrix: { value: null } },
        vertexShader: `
          uniform mat4 textureMatrix;
          varying vec4 vReflet;
          void main() {
            vReflet = textureMatrix * vec4(position, 1.0);
            gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
          }`,
        fragmentShader: `
          uniform vec3 color;
          uniform sampler2D tDiffuse;
          varying vec4 vReflet;
          void main() {
            vec2 uv = vReflet.xy / vReflet.w;
            vec3 somme = vec3(0.0);
            float poids = 0.0;
            for (int i = -5; i <= 5; i++) {
              float k = float(i);
              float p = exp(-k * k / 12.0);
              somme += texture2D(tDiffuse, uv + vec2(sin(uv.y * 150.0 + k * 1.7) * 0.0016, k * 0.011)).rgb * p;
              poids += p;
            }
            gl_FragColor = vec4(somme / poids * color * 0.6 + vec3(0.006, 0.006, 0.009), 1.0);
          }`,
      },
    });
    eau.rotation.x = -Math.PI / 2;
    eau.position.set(milieu, NIVEAU_EAU, BORD_QUAI + 250);
    decor.add(eau);

    // La lune vient de la gauche et de l'avant : elle donne leur relief aux façades.
    this.lune.color.setRGB(0.7, 0.72, 1.0);
    this.lune.intensity = 2.3;
    this.lune.target.position.set(milieu, 0, 0);
    this.lune.position.set(milieu - 0.72 * 130, 0.55 * 130, 0.42 * 130);
    const ombre = this.lune.shadow.camera;
    ombre.left = -78;
    ombre.right = 78;
    ombre.top = 42;
    ombre.bottom = -42;
    ombre.far = 320;
    ombre.updateProjectionMatrix();
  }

  // -------------------------------------------------------------- fenêtres et fils

  /** Pose (ou met à jour) les fenêtres et les fils de chaque quartier. */
  ville(quartiers: QuartierScene[]): void {
    this.quartiers = quartiers;
    const instant = performance.now();
    for (const q of quartiers) {
      const immeuble = this.immeubles.get(q.immeuble);
      if (!immeuble) continue;
      const trace = JSON.stringify([q.fenetres.map((f) => [f.id, f.fen, f.eteinte ?? false]), q.fils.map((f) => [f.vers, f.points]), q.nominal]);
      if (trace !== immeuble.trace) this.poser(immeuble, q, trace);
      for (const fenetre of immeuble.fenetres) {
        const etat = q.fenetres.find((f) => f.id === fenetre.id)?.etat ?? "verrouille";
        if (etat === fenetre.etat) continue;
        fenetre.etat = etat;
        fenetre.depuis.copy(fenetre.couleur);
        fenetre.change = this.options.calme ? 0 : instant;
      }
      for (const fil of immeuble.fils) {
        const etat = q.fils.find((f) => `${f.vers}` === fil.cle)?.etat ?? "verrouille";
        if (etat === fil.etat) continue;
        // Un défi vient d'être résolu : son fil se tend d'un bout à l'autre.
        if (etat === "resolu" && !this.options.calme) fil.tendu = instant;
        fil.etat = etat;
        this.habillerFil(fil);
      }
      const resolus = q.fenetres.filter((f) => f.etat === "resolu").length;
      immeuble.lampe.userData.voulue = (42 * resolus) / Math.max(1, q.fenetres.length);
    }
    // Un emplacement sans quartier (moins de huit catégories) reste un immeuble éteint.
    for (const immeuble of this.immeubles.values()) {
      if (!quartiers.some((q) => q.immeuble === immeuble.id)) immeuble.lampe.userData.voulue = 0;
    }
    const toutes = quartiers.flatMap((q) => q.fenetres);
    this.partVoulue = toutes.length ? toutes.filter((f) => f.etat === "resolu").length / toutes.length : 0;
    this.appliquerSurvol();
    this.bouge = true;
    this.demander();
  }

  private poser(immeuble: Immeuble, q: QuartierScene, trace: string): void {
    for (const objet of [...immeuble.groupe.children]) {
      immeuble.groupe.remove(objet);
      if (objet instanceof Mesh || objet instanceof Line2) objet.geometry.dispose();
    }
    this.lignes = this.lignes.filter((l) => !immeuble.fenetres.some((f) => f.contour.material === l));
    immeuble.trace = trace;
    const h = immeuble.meta.h;
    // Dans le repère de l'immeuble : x le long de la façade, y vers le haut, z devant elle.
    const point = (x: number, y: number, devant: number): Vector3 => new Vector3(x * U, (h - y) * U, devant * U);

    immeuble.cache = null;
    if (!q.nominal && q.fenetres.length > 0) {
      // Les fenêtres ne sont pas celles du dessin : un pan de pierre recouvre les niches.
      const pan = new Mesh(new PlaneGeometry(q.zone.w * U, q.zone.h * U), immeuble.pierre ?? new MeshStandardMaterial({ color: "#8d8496" }));
      pan.position.copy(point(q.zone.x + q.zone.w / 2, q.zone.y + q.zone.h / 2, 0.25));
      pan.receiveShadow = true;
      immeuble.groupe.add(pan);
      immeuble.cache = pan;
    }

    immeuble.fenetres = q.fenetres.map((f, i) => {
      const { x, y, w, h: haut, arc } = f.fen;
      const forme = new Shape();
      const rayon = w / 2;
      forme.moveTo(x * U, (h - (y + haut)) * U);
      forme.lineTo((x + w) * U, (h - (y + haut)) * U);
      if (arc) {
        forme.lineTo((x + w) * U, (h - (y + rayon)) * U);
        forme.absarc((x + rayon) * U, (h - (y + rayon)) * U, rayon * U, 0, Math.PI, false);
      } else {
        forme.lineTo((x + w) * U, (h - y) * U);
        forme.lineTo(x * U, (h - y) * U);
      }
      forme.closePath();
      // Dans sa niche si la fenêtre est celle du dessin ; sinon en applique, devant son cadre.
      const retrait = q.nominal ? (immeuble.meta.vitres[i] ?? immeuble.meta.vitres[0] ?? 1.45) : -0.75;
      const eteinte = f.eteinte ?? false;
      const couleur = (eteinte ? LUMIERES.disponible : LUMIERES[f.etat]).clone();
      const vitre = new Mesh(new ShapeGeometry(forme, 12), new MeshBasicMaterial({ color: couleur }));
      vitre.position.set(0, 0, -retrait * U);
      immeuble.groupe.add(vitre);
      if (!q.nominal) {
        // Sans niche, un cadre de menuiserie donne son épaisseur à la fenêtre.
        const cadre = new Mesh(new BoxGeometry((w + 1.6) * U, (haut + 1.6) * U, 0.06), new MeshStandardMaterial({ color: COULEURS.menuiserie, roughness: 0.5 }));
        cadre.position.copy(point(x + w / 2, y + haut / 2, 0.3));
        immeuble.groupe.add(cadre);
      }

      // Le contour : la fenêtre disponible, survolée ou ouverte est cernée de pierre claire.
      // Dans la niche, devant la menuiserie (qui avance de sept centimètres sur la vitre).
      const trait = forme.getPoints(12).flatMap((p) => [p.x, p.y, -(retrait - 0.85) * U]);
      trait.push(trait[0] ?? 0, trait[1] ?? 0, trait[2] ?? 0);
      const ligne = new LineMaterial({ color: COULEURS.claire, linewidth: 2, worldUnits: false });
      ligne.resolution.set(this.largeur, this.hauteur);
      this.lignes.push(ligne);
      const contour = new Line2(new LineGeometry().setPositions(trait), ligne);
      immeuble.groupe.add(contour);
      const coins = [point(x, y, 0), point(x + w, y, 0), point(x + w, y + haut, 0), point(x, y + haut, 0)];
      return { id: f.id, etat: f.etat, eteinte, vitre, contour, coins, couleur, depuis: couleur.clone(), change: 0 };
    });

    immeuble.fils = q.fils.flatMap((f) => {
      if (f.points.length < 2) return [];
      const xs = f.points.map((p) => p[0]);
      const zs = f.points.map((p) => h - p[1]);
      const emprise = { x0: Math.min(...xs), x1: Math.max(...xs), z0: Math.min(...zs), z1: Math.max(...zs) };
      // Le fil s'écarte de la façade pour passer devant un auvent qu'il croise.
      const ecart = (x: number): number => {
        let e = ECART_FIL;
        for (const [ax0 = 0, ax1 = 0, az0 = 0, az1 = 0, avancee = 0] of immeuble.meta.auvents) {
          if (emprise.x0 > ax1 || emprise.x1 < ax0 || emprise.z0 > az1 + 1 || emprise.z1 < az0 - 1) continue;
          const pres = borner(1 - Math.max(ax0 - x, x - ax1) / 10, 0, 1);
          e = Math.max(e, ECART_FIL + (avancee + 0.8 - ECART_FIL) * pres * pres * (3 - 2 * pres));
        }
        return e;
      };
      const courbe = new CatmullRomCurve3(f.points.map(([x, y]) => point(x, y, ecart(x))), false, "centripetal");
      const geometrie = new TubeGeometry(courbe, Math.max(12, f.points.length * 3), RAYON_FIL, 6, false);
      const fil: Fil = { cle: f.vers, etat: f.etat, objet: new Mesh(geometrie, new MeshBasicMaterial()), indices: geometrie.index?.count ?? 0, tendu: 0 };
      this.habillerFil(fil);
      immeuble.groupe.add(fil.objet);
      return [fil];
    });
  }

  /** Le fil prend l'état du défi qu'il atteint : chaud s'il est résolu, pierre douce jusqu'à
   * la fenêtre ouverte, froid au-delà. */
  private habillerFil(fil: Fil): void {
    const couleur = fil.etat === "resolu" ? lueur(COULEURS.lumignon, 1.25) : fil.etat === "disponible" ? new Color(COULEURS.douce).multiplyScalar(0.3) : lueur(COULEURS.lumen, 0.3);
    (fil.objet.material as MeshBasicMaterial).color.copy(couleur);
  }

  // -------------------------------------------------------------- caméra

  /** Change ce que la caméra regarde. `immediat` : sans mouvement (premier affichage). */
  viser(vue: Vue, immediat = false): void {
    const change = vue.quartier !== this.vue.quartier || vue.defi !== this.vue.defi;
    this.vue = { ...vue };
    this.appliquerSurvol();
    if (change) this.orbiteVoulue.set(0, 0);
    this.recadrer(immediat || !change ? (this.pose ? null : 0) : 1100, immediat);
  }

  /** La place prise par l'interface autour de la scène : le sujet se centre dans le reste. */
  degager(marges: Marges): void {
    const m = this.marges;
    if (m.haut === marges.haut && m.droite === marges.droite && m.bas === marges.bas && m.gauche === marges.gauche) return;
    this.marges = { ...marges };
    this.recadrer(this.pose ? 500 : 0, false);
  }

  /** Défi survolé dans la liste ou sur la scène : sa fenêtre se cerne. */
  survoler(defi: string | null): void {
    if (defi === this.survole) return;
    this.survole = defi;
    this.appliquerSurvol();
    this.demander();
  }

  /** Glisser sur la scène fait tourner la maquette, dans des limites ; elle revient d'elle-même
   * au changement de vue. Angles en radians. */
  tourner(lacet: number, pente: number): void {
    this.orbiteVoulue.set(borner(this.orbiteVoulue.x + lacet, -0.75, 0.75), borner(this.orbiteVoulue.y + pente, -0.2, 0.32));
    this.demander();
  }

  /** Vue du quai : la caméra se décale un peu avec le pointeur (de −1 à 1) ; les toits lointains
   * glissent derrière les immeubles. */
  pencher(cote: number): void {
    if (this.options.calme) return;
    this.orbiteVoulue.set(borner(cote, -1, 1) * 0.045, 0);
    this.demander();
  }

  /** Vue du quai : change la hauteur du quai dans l'image. */
  asseoir(sol: number): void {
    if (sol === this.options.sol) return;
    this.options.sol = sol;
    this.recadrer(this.pose ? null : 0, true);
  }

  private appliquerSurvol(): void {
    for (const immeuble of this.immeubles.values()) {
      const quartier = this.quartiers.find((q) => q.immeuble === immeuble.id);
      const enAvant = quartier !== undefined && quartier.categorie === this.vue.quartier;
      for (const fenetre of immeuble.fenetres) {
        const ouverte = fenetre.id === this.vue.defi;
        const survolee = fenetre.id === this.survole;
        fenetre.contour.visible = (fenetre.etat === "disponible" && !fenetre.eteinte) || ouverte || survolee;
        fenetre.contour.material.linewidth = ouverte ? 4 : survolee ? 3 : 2;
      }
      // Hors du quartier choisi, seul le fil déjà gagné se voit.
      for (const fil of immeuble.fils) fil.objet.visible = fil.etat === "resolu" || enAvant;
    }
  }

  /** Calcule la pose qui montre la vue courante dans la place libre, et y va. */
  private recadrer(duree: number | null, immediat: boolean): void {
    const vers = this.poseVoulue();
    if (!this.pose || immediat || this.options.calme || duree === 0) {
      this.pose = vers;
      this.transition = null;
    } else if (duree !== null) {
      this.transition = { depuis: this.copie(this.pose), vers, debut: performance.now(), duree };
    } else if (this.transition) {
      this.transition.vers = vers;
    } else {
      this.pose = vers;
    }
    this.bouge = true;
    this.demander();
  }

  private copie(p: Pose): Pose {
    return { cible: p.cible.clone(), distance: p.distance, pente: p.pente, lacet: p.lacet, decalage: p.decalage.clone() };
  }

  /** Face à la ville, l'axe horizontal (les verticales restent droites). La rangée tient dans la
   * largeur ; sur un écran étroit, elle garde une taille lisible et ses bords sont rognés. Le
   * décalage de l'image pose le quai à la hauteur voulue. */
  private poseDuQuai(): Pose {
    const sol = this.options.sol ?? 0.7;
    const parMetre = Math.min(Math.max((this.largeur * 0.96) / (this.rangee + 4), (this.hauteur * 0.3) / 21), (this.hauteur * (sol - 0.06)) / 22);
    const distance = this.hauteur / (2 * parMetre * Math.tan((CHAMP * DEGRE) / 2));
    const decalage = new Vector2(0, sol - 0.5 - (HAUTEUR_OEIL * parMetre) / this.hauteur);
    return { cible: new Vector3(this.rangee / 2, HAUTEUR_OEIL, 0), distance, pente: 0, lacet: 0, decalage };
  }

  private poseVoulue(): Pose {
    if (this.quai) return this.poseDuQuai();
    const quartier = this.vue.quartier ? this.quartiers.find((q) => q.categorie === this.vue.quartier) : undefined;
    const immeuble = quartier ? this.immeubles.get(quartier.immeuble) : undefined;
    let mini: Vector3;
    let maxi: Vector3;
    let pente = this.largeur < this.hauteur ? PENTE_VILLE_HAUTE : PENTE_VILLE;
    let lacet = 0;
    if (immeuble) {
      mini = immeuble.mini.clone().add(immeuble.racine.position);
      maxi = immeuble.maxi.clone().add(immeuble.racine.position);
      pente = PENTE_QUARTIER;
      lacet = (LACETS[immeuble.id] ?? 0) * DEGRE;
    } else {
      // Toute la ville : la planche et ses immeubles (la tour compte pour sa hauteur).
      mini = new Vector3(1, 0, 1);
      maxi = new Vector3(59, 0, 64);
      for (const autre of this.immeubles.values()) {
        mini.min(autre.mini.clone().add(autre.racine.position));
        maxi.max(autre.maxi.clone().add(autre.racine.position));
      }
    }
    const coins: Vector3[] = [];
    for (const x of [mini.x, maxi.x]) for (const y of [mini.y, maxi.y]) for (const z of [mini.z, maxi.z]) coins.push(new Vector3(x, y, z));
    const cible = mini.clone().add(maxi).multiplyScalar(0.5);

    // La place libre, en part de la toile.
    const m = this.marges;
    const libre = {
      x0: borner(m.gauche / this.largeur, 0, 0.8),
      x1: borner(1 - m.droite / this.largeur, 0.2, 1),
      y0: borner(m.haut / this.hauteur, 0, 0.8),
      y1: borner(1 - m.bas / this.hauteur, 0.2, 1),
    };
    const marge = immeuble ? 0.82 : 0.94;
    const lw = Math.max(0.15, libre.x1 - libre.x0) * marge;
    const lh = Math.max(0.15, libre.y1 - libre.y0) * marge;

    // La distance d'où la boîte tient dans la place libre (recherche par moitiés).
    const essai = new PerspectiveCamera(CHAMP, this.largeur / this.hauteur, 1, 900);
    const emprise = (distance: number): { x0: number; x1: number; y0: number; y1: number } => {
      essai.position.copy(cible).add(new Vector3(Math.sin(lacet) * Math.cos(pente), Math.sin(pente), Math.cos(lacet) * Math.cos(pente)).multiplyScalar(distance));
      essai.lookAt(cible);
      essai.updateMatrixWorld();
      const e = { x0: Infinity, x1: -Infinity, y0: Infinity, y1: -Infinity };
      for (const coin of coins) {
        const p = coin.clone().project(essai);
        e.x0 = Math.min(e.x0, p.x);
        e.x1 = Math.max(e.x1, p.x);
        e.y0 = Math.min(e.y0, p.y);
        e.y1 = Math.max(e.y1, p.y);
      }
      return e;
    };
    const tient = (): number => {
      let pres = 4;
      let loin = 700;
      for (let i = 0; i < 28; i++) {
        const milieu = (pres + loin) / 2;
        const e = emprise(milieu);
        if ((e.x1 - e.x0) / 2 <= lw && (e.y1 - e.y0) / 2 <= lh) loin = milieu;
        else pres = milieu;
      }
      return loin;
    };
    let distance = tient();
    if (this.options.ronde && !immeuble) {
      // La maquette tourne : elle doit tenir dans la place libre sous tous les angles.
      const face = lacet;
      for (const angle of [Math.PI / 4, Math.PI / 2, (3 * Math.PI) / 4]) {
        lacet = angle;
        distance = Math.max(distance, tient());
      }
      lacet = face;
    }
    const e = emprise(distance);
    // Le centre de la boîte, tel qu'on le voit, va au centre de la place libre.
    const decalage = new Vector2((libre.x0 + libre.x1) / 2 - 0.5 - (e.x0 + e.x1) / 4, (libre.y0 + libre.y1) / 2 - 0.5 + (e.y0 + e.y1) / 4);
    return { cible, distance, pente, lacet, decalage };
  }

  // -------------------------------------------------------------- rendu

  private redimensionner(): void {
    const largeur = Math.max(1, this.toile.clientWidth);
    const hauteur = Math.max(1, this.toile.clientHeight);
    if (largeur === this.largeur && hauteur === this.hauteur && this.pose) return;
    this.largeur = largeur;
    this.hauteur = hauteur;
    // Au plus deux pixels par point, et jamais plus de quatre millions de pixels à calculer.
    const densite = Math.min(window.devicePixelRatio || 1, 2, Math.sqrt(4_000_000 / (largeur * hauteur)));
    this.rendu.setPixelRatio(densite);
    this.rendu.setSize(largeur, hauteur, false);
    this.composition.setPixelRatio(densite);
    this.composition.setSize(largeur, hauteur);
    for (const ligne of this.lignes) ligne.resolution.set(largeur, hauteur);
    this.camera.aspect = largeur / hauteur;
    this.recadrer(this.pose ? null : 0, !this.pose);
  }

  private demander(): void {
    if (this.image || this.detruite) return;
    this.image = requestAnimationFrame((instant) => {
      this.image = 0;
      this.dessiner(instant);
    });
  }

  private dessiner(instant: number): void {
    if (this.detruite || !this.pose) return;
    // La ronde du grand écran tourne des heures : trente images par seconde lui suffisent.
    if (this.options.ronde && instant - this.dernierRendu < 30) {
      this.demander();
      return;
    }
    this.dernierRendu = instant;
    const ecoule = Math.min(0.1, (instant - (this.dernierInstant || instant)) / 1000);
    this.dernierInstant = instant;
    let encore = false;

    if (this.transition) {
      const { depuis, vers, debut, duree } = this.transition;
      const k = adoucir(borner((performance.now() - debut) / duree, 0, 1));
      this.pose.cible.lerpVectors(depuis.cible, vers.cible, k);
      this.pose.distance = Math.exp(entre(Math.log(depuis.distance), Math.log(vers.distance), k));
      this.pose.pente = entre(depuis.pente, vers.pente, k);
      this.pose.lacet = entre(depuis.lacet, vers.lacet, k);
      this.pose.decalage.lerpVectors(depuis.decalage, vers.decalage, k);
      if (k >= 1) this.transition = null;
      else encore = true;
      this.bouge = true;
    }
    if (this.options.ronde && !this.options.calme) {
      // Un tour en deux minutes environ.
      this.orbiteVoulue.x += ecoule * 0.05;
      encore = true;
    }
    // La rotation à la main rejoint doucement ce que le geste a demandé.
    if (this.orbite.distanceTo(this.orbiteVoulue) > 0.0005) {
      if (this.options.calme) this.orbite.copy(this.orbiteVoulue);
      else this.orbite.lerp(this.orbiteVoulue, 1 - Math.exp(-ecoule * 9));
      encore = true;
      this.bouge = true;
    }

    const pente = borner(this.pose.pente + this.orbite.y, this.quai ? 0 : 0.12, 1.35);
    const lacet = this.pose.lacet + this.orbite.x;
    this.camera.position
      .set(Math.sin(lacet) * Math.cos(pente), Math.sin(pente), Math.cos(lacet) * Math.cos(pente))
      .multiplyScalar(this.pose.distance)
      .add(this.pose.cible);
    this.camera.lookAt(this.pose.cible);
    // Les plans de coupe suivent la distance : de la précision de loin, rien de tronqué de près.
    this.camera.near = borner(this.pose.distance * 0.06, 0.4, 8);
    this.camera.far = this.pose.distance * 3 + 400;
    this.camera.setViewOffset(this.largeur, this.hauteur, -this.pose.decalage.x * this.largeur, -this.pose.decalage.y * this.hauteur, this.largeur, this.hauteur);

    // Les lumières changent en douceur : une fenêtre s'allume, un fil se tend, une lueur monte.
    const maintenant = performance.now();
    for (const immeuble of this.immeubles.values()) {
      for (const fenetre of immeuble.fenetres) {
        const voulue = fenetre.eteinte && fenetre.etat !== "resolu" ? LUMIERES.disponible : LUMIERES[fenetre.etat];
        const k = fenetre.change ? borner((maintenant - fenetre.change) / 450, 0, 1) : 1;
        fenetre.couleur.lerpColors(fenetre.depuis, voulue, k);
        fenetre.vitre.material.color.copy(fenetre.couleur);
        if (k < 1) encore = true;
        else fenetre.change = 0;
      }
      for (const fil of immeuble.fils) {
        const k = fil.tendu ? borner((maintenant - fil.tendu) / 700, 0, 1) : 1;
        fil.objet.geometry.setDrawRange(0, Math.ceil((fil.indices * k) / 36) * 36);
        if (k < 1) encore = true;
        else fil.tendu = 0;
      }
      const voulue = (immeuble.lampe.userData.voulue as number | undefined) ?? 0;
      if (Math.abs(immeuble.lampe.intensity - voulue) > 0.05) {
        immeuble.lampe.intensity = this.options.calme ? voulue : entre(immeuble.lampe.intensity, voulue, 1 - Math.exp(-ecoule * 4));
        encore = true;
      } else {
        immeuble.lampe.intensity = voulue;
      }
    }

    // Vue du quai : le filet ambre s'étire et les fenêtres lointaines s'allument avec la part
    // des défis résolus.
    if (this.quai && this.part !== this.partVoulue) {
      const suite = this.options.calme ? this.partVoulue : entre(this.part, this.partVoulue, 1 - Math.exp(-ecoule * 1.5));
      this.part = Math.abs(suite - this.partVoulue) < 0.001 ? this.partVoulue : suite;
      if (this.filetAmbre) this.filetAmbre.scale.x = Math.max(0.0001, this.part);
      if (this.lointaines) {
        const allumees = Math.round(this.part * this.lointaines.count);
        for (let i = 0; i < this.lointaines.count; i++) this.lointaines.setColorAt(i, i < allumees ? FENETRE_LOINTAINE.allumee : FENETRE_LOINTAINE.eteinte);
        if (this.lointaines.instanceColor) this.lointaines.instanceColor.needsUpdate = true;
      }
      if (this.part !== this.partVoulue) encore = true;
    }

    this.composition.render();
    if (this.bouge) {
      this.bouge = false;
      this.options.surReperes?.(this.reperer());
    }
    if (encore) this.demander();
  }

  /** La place à l'écran de chaque immeuble, et des fenêtres du quartier choisi. */
  private reperer(): Reperes {
    const ecran = (p: Vector3): { x: number; y: number } => {
      const n = p.clone().project(this.camera);
      return { x: ((n.x + 1) / 2) * this.largeur, y: ((1 - n.y) / 2) * this.hauteur };
    };
    const boite = (points: Vector3[]): Rectangle => {
      const e = points.map(ecran);
      const x0 = Math.min(...e.map((p) => p.x));
      const y0 = Math.min(...e.map((p) => p.y));
      return { x: x0, y: y0, w: Math.max(...e.map((p) => p.x)) - x0, h: Math.max(...e.map((p) => p.y)) - y0 };
    };
    const reperes: Reperes = { quartiers: {}, fenetres: {} };
    for (const q of this.quartiers) {
      const immeuble = this.immeubles.get(q.immeuble);
      if (!immeuble) continue;
      const a = immeuble.mini.clone().add(immeuble.racine.position);
      const b = immeuble.maxi.clone().add(immeuble.racine.position);
      const coins: Vector3[] = [];
      for (const x of [a.x, b.x]) for (const y of [a.y, b.y]) for (const z of [a.z, b.z]) coins.push(new Vector3(x, y, z));
      const centre = immeuble.centre.clone().add(immeuble.racine.position);
      reperes.quartiers[q.categorie] = {
        ...boite(coins),
        profondeur: centre.distanceTo(this.camera.position),
        // Le sol devant l'immeuble, au milieu de sa façade : la place de son nom.
        pied: ecran(new Vector3(centre.x, 0, b.z + 1.3)),
      };
      if (q.categorie === this.vue.quartier) {
        for (const fenetre of immeuble.fenetres) reperes.fenetres[fenetre.id] = boite(fenetre.coins.map((c) => immeuble.racine.localToWorld(c.clone())));
      }
    }
    return reperes;
  }

  detruire(): void {
    this.detruite = true;
    cancelAnimationFrame(this.image);
    this.observateur.disconnect();
    this.scene.traverse((objet) => {
      if (objet instanceof Mesh || objet instanceof Line2) {
        objet.geometry.dispose();
        for (const m of Array.isArray(objet.material) ? objet.material : [objet.material]) (m as Material).dispose();
      }
    });
    this.lune.shadow.map?.dispose();
    this.composition.dispose();
    this.rendu.dispose();
  }
}
