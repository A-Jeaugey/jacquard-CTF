// Thème du pack : jetons de couleur, libellés, logo, CSS et layouts.

import { api } from "./api";
import { setStringOverrides, type StringKey } from "./strings";
import type { Theme } from "./types";

export const theme = $state<{ data: Theme | null }>({ data: null });

export async function loadTheme(): Promise<void> {
  let data: Theme;
  try {
    data = await api.get<Theme>("/api/theme");
  } catch {
    return; // pas de thème : l'apparence par défaut s'applique
  }
  theme.data = data;
  // La direction artistique est désormais fixe (frontend/DESIGN.md) : seuls les libellés du
  // pack sont repris ; ses jetons et sa feuille de style ne sont plus appliqués.
  setStringOverrides(data.strings as Partial<Record<StringKey, string>>);
}

/**
 * Nettoie un SVG avant de l'insérer dans la page. Le serveur refuse déjà les SVG dangereux
 * à l'import du pack ; ceci est une seconde barrière.
 */
export function sanitizeSvg(source: string): string {
  const doc = new DOMParser().parseFromString(source, "image/svg+xml");
  const svg = doc.documentElement;
  if (svg.nodeName.toLowerCase() !== "svg" || doc.querySelector("parsererror")) return "";
  for (const node of Array.from(doc.querySelectorAll("script, foreignObject, iframe, embed, object"))) {
    node.remove();
  }
  for (const element of Array.from(doc.querySelectorAll("*"))) {
    for (const attribute of Array.from(element.attributes)) {
      const name = attribute.name.toLowerCase();
      const value = attribute.value.trim().toLowerCase();
      if (name.startsWith("on")) element.removeAttribute(attribute.name);
      else if ((name === "href" || name === "xlink:href") && !value.startsWith("#")) {
        element.removeAttribute(attribute.name);
      }
    }
  }
  svg.removeAttribute("width");
  svg.removeAttribute("height");
  return new XMLSerializer().serializeToString(svg);
}
