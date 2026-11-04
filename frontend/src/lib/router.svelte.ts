// Routeur minimal basé sur l'API History. Le serveur renvoie index.html pour toute
// route inconnue (voir deploy/Caddyfile). La recherche (?defi=…) sert à ouvrir un panneau :
// le retour arrière du navigateur le referme.

export const route = $state({ path: window.location.pathname, search: window.location.search });

export function navigate(target: string, replace = false): void {
  const url = new URL(target, window.location.href);
  if (url.pathname === route.path && url.search === route.search) return;
  if (replace) history.replaceState(null, "", url.pathname + url.search);
  else history.pushState(null, "", url.pathname + url.search);
  const memePage = url.pathname === route.path;
  route.path = url.pathname;
  route.search = url.search;
  if (!memePage) window.scrollTo(0, 0);
}

/** Valeur d'un paramètre de la recherche courante. */
export function param(name: string): string | null {
  return new URLSearchParams(route.search).get(name);
}

window.addEventListener("popstate", () => {
  route.path = window.location.pathname;
  route.search = window.location.search;
});

/** Intercepte les clics sur les liens internes pour éviter un rechargement complet. */
export function interceptLinks(event: MouseEvent): void {
  if (event.defaultPrevented || event.button !== 0) return;
  if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
  const anchor = (event.target as Element | null)?.closest("a");
  if (!anchor || anchor.target || anchor.hasAttribute("download")) return;
  const url = new URL(anchor.href, window.location.href);
  if (url.origin !== window.location.origin || url.pathname.startsWith("/api/")) return;
  if (url.hash && url.pathname === route.path && url.search === route.search) return; // ancre locale
  event.preventDefault();
  navigate(url.pathname + url.search);
}
