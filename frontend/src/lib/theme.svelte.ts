// Thème du pack. La direction artistique est fixe (frontend/DESIGN.md) : seuls les libellés
// du pack sont repris ; ses jetons, sa feuille de style, son logo et ses layouts sont validés
// à l'import mais ne changent pas le rendu.

import { api } from "./api";
import { setStringOverrides, type StringKey } from "./strings";
import type { Theme } from "./types";

export async function loadTheme(): Promise<void> {
  let data: Theme;
  try {
    data = await api.get<Theme>("/api/theme");
  } catch {
    return; // pas de thème : les libellés par défaut s'appliquent
  }
  setStringOverrides(data.strings as Partial<Record<StringKey, string>>);
}
