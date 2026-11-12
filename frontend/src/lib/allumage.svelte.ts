// L'allumage, seul moment orchestré de la ville (frontend/DESIGN.md) : au premier affichage de
// la session, tout est froid, puis les fenêtres résolues s'allument une à une dans l'ordre des
// résolutions. Il se décide une seule fois, à l'arrivée de la progression de l'équipe : les
// rechargements suivants (une résolution, un coéquipier) ne le relancent pas et ne
// l'interrompent pas, et une équipe qui n'a encore rien résolu ne le verra pas à sa première
// résolution. Partagé par le plan à plat (Ville.svelte) et la maquette (Ville3D.svelte).

export interface ReglagesAllumage {
  /** Clé de session : un allumage par décor (le plan, le panorama). */
  cle?: string;
  /** Attente avant la première fenêtre, puis entre deux fenêtres (selon leur nombre), en ms. */
  depart?: number;
  pas?: number | ((nombre: number) => number);
}

export interface Allumage {
  /** Les défis résolus dont la fenêtre est encore froide ; `null` hors de l'allumage. */
  readonly froides: Set<string> | null;
  /** À appeler quand l'ordre des résolutions est connu (`null` : pas encore). */
  lancer(ordre: string[] | null): void;
  arreter(): void;
}

export function creerAllumage(reglages: ReglagesAllumage = {}): Allumage {
  const cle = reglages.cle ?? "jq_allumage";
  const depart = reglages.depart ?? 700;
  let froides = $state<Set<string> | null>(null);
  let lance = false;
  const minuteurs: ReturnType<typeof setTimeout>[] = [];
  return {
    get froides() {
      return froides;
    },
    lancer(ordre) {
      if (lance || ordre === null) return;
      lance = true;
      let dejaVu = false;
      try {
        dejaVu = sessionStorage.getItem(cle) === "1";
        sessionStorage.setItem(cle, "1");
      } catch {
        // stockage indisponible : l'allumage se rejoue, sans gravité
      }
      if (dejaVu || ordre.length === 0 || matchMedia("(prefers-reduced-motion: reduce)").matches) return;
      const pas = typeof reglages.pas === "function" ? reglages.pas(ordre.length) : (reglages.pas ?? 110);
      froides = new Set(ordre);
      ordre.forEach((id, i) =>
        minuteurs.push(
          setTimeout(() => {
            if (!froides) return;
            const suite = new Set(froides);
            suite.delete(id);
            froides = suite;
          }, depart + i * pas),
        ),
      );
      minuteurs.push(setTimeout(() => (froides = null), depart + ordre.length * pas + 260));
    },
    arreter() {
      minuteurs.forEach(clearTimeout);
    },
  };
}
