/**
 * Copie un texte dans le presse-papiers. `navigator.clipboard` n'existe qu'en contexte sécurisé
 * (HTTPS ou localhost) : sur une plateforme servie en HTTP, sur le réseau d'une école par
 * exemple, on passe par une zone de texte hors écran et `execCommand("copy")`, que les
 * navigateurs acceptent encore pendant un clic. Renvoie `false` si rien n'a pu être copié.
 */
export async function copierTexte(texte: string): Promise<boolean> {
  if (window.isSecureContext && navigator.clipboard) {
    try {
      await navigator.clipboard.writeText(texte);
      return true;
    } catch {
      // permission refusée : on tente le repli
    }
  }
  const actif = document.activeElement instanceof HTMLElement ? document.activeElement : null;
  const zone = document.createElement("textarea");
  zone.value = texte;
  zone.setAttribute("readonly", "");
  zone.setAttribute("aria-hidden", "true");
  Object.assign(zone.style, { position: "fixed", top: "0", left: "-9999px", opacity: "0" });
  document.body.append(zone);
  zone.select();
  let copie = false;
  try {
    copie = document.execCommand("copy");
  } catch {
    copie = false;
  }
  zone.remove();
  actif?.focus({ preventScroll: true });
  return copie;
}
