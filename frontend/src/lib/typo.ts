// Typographie française : espace fine insécable avant « : ; ? ! » et à l'intérieur des
// guillemets, apostrophe typographique. Appliquée aux libellés (t) et aux données affichées.

const FINE = " ";

export function typo(text: string): string {
  return text
    .replace(/«[\s  ]?/g, `«${FINE}`)
    .replace(/[\s  ]?»/g, `${FINE}»`)
    .replace(/(\S)[\s  ]?([:;!?])(?=\s|$|»)/g, (match, before: string, sign: string) =>
      // Pas d'espace dans une adresse (« http: »), une heure (« 12:21 ») ou un flag.
      /[/\d{]/.test(before) ? match : `${before}${FINE}${sign}`,
    )
    .replace(/([A-Za-zÀ-ÿ])'([A-Za-zÀ-ÿ])/g, "$1’$2");
}

/** Action Svelte : applique `typo` aux nœuds texte d'un contenu HTML (Markdown du serveur),
 * sans toucher au code ni aux champs. */
export function typographie(node: HTMLElement): { update: () => void } {
  const apply = (): void => {
    const walker = document.createTreeWalker(node, NodeFilter.SHOW_TEXT, {
      acceptNode: (text) =>
        text.parentElement?.closest("code, pre, script, style, textarea, input")
          ? NodeFilter.FILTER_REJECT
          : NodeFilter.FILTER_ACCEPT,
    });
    for (let text = walker.nextNode(); text; text = walker.nextNode()) {
      const value = typo(text.nodeValue ?? "");
      if (value !== text.nodeValue) text.nodeValue = value;
    }
  };
  apply();
  return { update: apply };
}
