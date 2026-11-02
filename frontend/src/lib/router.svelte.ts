// Routeur minimal basé sur l'API History. Le serveur renvoie index.html pour toute
// route inconnue (voir deploy/Caddyfile).

export const route = $state({ path: window.location.pathname });

export function navigate(path: string, replace = false): void {
  if (path === route.path) return;
  if (replace) history.replaceState(null, "", path);
  else history.pushState(null, "", path);
  route.path = path;
  window.scrollTo(0, 0);
}

window.addEventListener("popstate", () => {
  route.path = window.location.pathname;
});

/** Intercepte les clics sur les liens internes pour éviter un rechargement complet. */
export function interceptLinks(event: MouseEvent): void {
  if (event.defaultPrevented || event.button !== 0) return;
  if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
  const anchor = (event.target as Element | null)?.closest("a");
  if (!anchor || anchor.target || anchor.hasAttribute("download")) return;
  const url = new URL(anchor.href, window.location.href);
  if (url.origin !== window.location.origin || url.pathname.startsWith("/api/")) return;
  event.preventDefault();
  navigate(url.pathname);
}
