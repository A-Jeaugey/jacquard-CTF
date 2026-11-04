export function formatDateTime(iso: string, timeZone?: string): string {
  return new Intl.DateTimeFormat("fr-FR", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone,
  }).format(new Date(iso));
}

export function formatTime(iso: string, timeZone?: string): string {
  return new Intl.DateTimeFormat("fr-FR", { timeStyle: "medium", timeZone }).format(new Date(iso));
}

export function formatDuration(milliseconds: number): string {
  const total = Math.max(0, Math.floor(milliseconds / 1000));
  const days = Math.floor(total / 86400);
  const hours = Math.floor((total % 86400) / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  const seconds = total % 60;
  const clock = [hours, minutes, seconds].map((n) => String(n).padStart(2, "0")).join(":");
  return days > 0 ? `${days} j ${clock}` : clock;
}

export function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} o`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} Ko`;
  return `${(bytes / 1024 / 1024).toFixed(1)} Mo`;
}

/** Exécute `task` immédiatement puis toutes les `ms` millisecondes, tant que l'onglet est visible. */
export function poll(task: () => unknown, ms: number): () => void {
  void task();
  const timer = setInterval(() => {
    if (document.visibilityState === "visible") void task();
  }, ms);
  return () => clearInterval(timer);
}

const nombres = new Intl.NumberFormat("fr-FR");

/** « 4 996 pts », avec une espace insécable avant l'unité. */
export function formatPoints(points: number): string {
  return `${nombres.format(points)} pts`;
}

/** Heure courte (« 15:07 ») dans le fuseau de l'événement. */
export function formatHeure(iso: string, timeZone?: string): string {
  return new Intl.DateTimeFormat("fr-FR", { hour: "2-digit", minute: "2-digit", timeZone }).format(new Date(iso));
}

/** Plage horaire en phrase : « Le 13 mars 2027, de 14:00 à 20:00 » ou, sur plusieurs jours,
 * « Du 3 nov. 2026 à 12:07 au 4 nov. 2026 à 18:07 ». */
export function formatPlage(debut: string, fin: string, timeZone?: string): string {
  const jour = new Intl.DateTimeFormat("fr-FR", { day: "numeric", month: "long", year: "numeric", timeZone });
  const heure = (iso: string): string => formatHeure(iso, timeZone);
  const j1 = jour.format(new Date(debut));
  const j2 = jour.format(new Date(fin));
  if (j1 === j2) return `Le ${j1}, de ${heure(debut)} à ${heure(fin)}`;
  return `Du ${j1} à ${heure(debut)} au ${j2} à ${heure(fin)}`;
}
