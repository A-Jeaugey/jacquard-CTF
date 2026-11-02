// Libellés de l'interface. Toutes les chaînes affichées passent par `t()`, ce qui
// permettra aux thèmes des packs de les surcharger (docs/conception-plateforme.md, §6.1).

const defaults = {
  "nav.home": "Accueil",
  "nav.board": "Défis",
  "nav.scoreboard": "Classement",
  "nav.story": "Journal",
  "nav.team": "Équipe",
  "nav.admin": "Admin",
  "nav.login": "Connexion",
  "nav.register": "Inscription",
  "nav.logout": "Déconnexion",

  "phase.not_started": "Début dans",
  "phase.running": "Fin dans",
  "phase.ended": "Événement terminé",
  "phase.frozen": "Classement gelé",

  "home.cta.board": "Voir les défis",
  "home.cta.register": "S'inscrire",
  "home.cta.team": "Créer ou rejoindre une équipe",
  "home.announcements": "Annonces",
  "home.no_announcements": "Aucune annonce pour l'instant.",

  "auth.username": "Pseudo",
  "auth.password": "Mot de passe",
  "auth.email": "E-mail (facultatif)",
  "auth.registration_code": "Code d'inscription",
  "auth.login": "Se connecter",
  "auth.register": "Créer mon compte",
  "auth.no_account": "Pas encore de compte ?",
  "auth.has_account": "Déjà inscrit·e ?",
  "auth.registration_closed": "Les inscriptions sont fermées.",
  "auth.password_hint": "8 caractères minimum.",

  "team.title": "Mon équipe",
  "team.create": "Créer une équipe",
  "team.create.name": "Nom de l'équipe",
  "team.create.submit": "Créer",
  "team.join": "Rejoindre une équipe",
  "team.join.code": "Code d'invitation",
  "team.join.submit": "Rejoindre",
  "team.invite": "Code d'invitation à partager",
  "team.members": "Membres",
  "team.score": "Score",
  "team.rank": "Rang",
  "team.solves": "Défis résolus",
  "team.no_solves": "Aucun défi résolu pour l'instant.",
  "team.leave": "Quitter l'équipe",
  "team.leave.confirm": "Quitter cette équipe ?",
  "team.solo": "Cet événement se joue en solo : ton équipe porte ton pseudo.",
  "team.items": "Inventaire",
  "team.no_items": "Aucun objet pour l'instant.",
  "team.penalty": "Indices achetés : −{n} pts",

  "board.title": "Défis",
  "board.need_team": "Rejoins ou crée une équipe pour accéder aux défis.",
  "board.not_started": "Les défis seront visibles au début de l'événement.",
  "board.empty": "Aucun défi pour l'instant.",
  "board.solves": "{n} résolution(s)",
  "board.points": "{n} pts",
  "board.solved": "Résolu",
  "board.filter.unsolved": "Masquer les défis résolus",
  "board.locked": "Verrouillé",

  "challenge.files": "Fichiers",
  "challenge.connection": "Connexion",
  "challenge.authors": "Par {names}",
  "challenge.flag": "Flag",
  "challenge.submit": "Valider",
  "challenge.correct": "Bravo, flag correct !",
  "challenge.incorrect": "Ce n'est pas le bon flag.",
  "challenge.already_solved": "Ton équipe a déjà résolu ce défi.",
  "challenge.solved_banner": "Défi résolu par ton équipe.",
  "challenge.format_hint": "Le flag attendu ressemble à {format}.",
  "challenge.ended": "L'événement est terminé : les soumissions sont fermées.",
  "challenge.close": "Fermer",
  "challenge.hints": "Indices",
  "challenge.hint": "Indice {n}",
  "challenge.hint.free": "Gratuit",
  "challenge.hint.cost": "{n} pts",
  "challenge.hint.reveal": "Révéler",
  "challenge.hint.unavailable": "Pas encore disponible",
  "challenge.hint.confirm": "Révéler cet indice coûtera {n} points à ton équipe. Continuer ?",
  "challenge.first_blood": "Premier sang ! Ton équipe est la première à résoudre ce défi.",
  "challenge.first_blood_rank": "Ton équipe est la {n}e à résoudre ce défi : bonus obtenu.",
  "challenge.item_obtained": "Objet obtenu : {name}",
  "challenge.unlocked_challenge": "Nouveau défi débloqué : {name}",
  "challenge.unlocked_story": "Nouveau chapitre dans le journal : {title}",

  "story.title": "Journal",
  "story.empty": "Rien à lire pour l'instant.",
  "story.locked": "{n} chapitre(s) encore à découvrir.",
  "story.new": "Nouveau",

  "live.first_blood": "🩸 {team} : premier sang sur « {challenge} » !",
  "live.teammate_solve": "✅ {user} a résolu « {challenge} »",
  "live.teammate_hint": "💡 {user} a révélé un indice sur « {challenge} »",
  "live.unlocked_challenge": "🔓 Nouveau défi : {name}",
  "live.unlocked_story": "📜 Nouveau chapitre : {title}",
  "live.announcement": "📢 {title}",

  "scoreboard.title": "Classement",
  "scoreboard.rank": "#",
  "scoreboard.team": "Équipe",
  "scoreboard.score": "Score",
  "scoreboard.solves": "Résolus",
  "scoreboard.frozen": "Le classement est gelé depuis {time}. Les résultats finaux seront révélés à la fin.",
  "scoreboard.empty": "Aucune équipe pour l'instant.",

  "admin.title": "Administration",
  "admin.tab.submissions": "Soumissions",
  "admin.tab.teams": "Équipes",
  "admin.tab.announcements": "Annonces",
  "admin.filter.all": "Toutes",
  "admin.filter.correct": "Correctes",
  "admin.filter.incorrect": "Incorrectes",
  "admin.load_more": "Charger plus",
  "admin.hidden": "Masquée",
  "admin.hide": "Masquer",
  "admin.show": "Afficher",
  "admin.announcement.title": "Titre",
  "admin.announcement.body": "Message (Markdown)",
  "admin.announcement.publish": "Publier",
  "admin.announcement.delete": "Supprimer",

  "error.generic": "Une erreur est survenue.",
  "error.network": "Impossible de joindre le serveur.",
  "error.validation": "Certains champs sont invalides.",
  "error.not_configured": "La plateforme est prête, mais aucun événement n'a encore été importé.",
  "error.not_found": "Page introuvable.",
  "loading": "Chargement…",
} as const;

export type StringKey = keyof typeof defaults;

let overrides: Partial<Record<StringKey, string>> = {};

export function setStringOverrides(values: Partial<Record<StringKey, string>>): void {
  overrides = values;
}

export function t(key: StringKey, params: Record<string, string | number> = {}): string {
  const template = overrides[key] ?? defaults[key];
  return template.replace(/\{(\w+)\}/g, (_, name: string) => String(params[name] ?? `{${name}}`));
}
