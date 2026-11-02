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
