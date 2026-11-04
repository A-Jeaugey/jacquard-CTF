import { expect, test, type Browser, type Page } from "@playwright/test";

let counter = 0;

async function newPlayer(browser: Browser, team: { create?: string; join?: string }): Promise<Page> {
  const page = await (await browser.newContext()).newPage();
  const username = `joueur${Date.now() % 100000}${counter++}`;
  await page.goto("/register");
  await page.getByLabel("Pseudo").fill(username);
  await page.getByLabel("Mot de passe").fill("motdepasse-solide");
  await page.getByRole("button", { name: "Créer mon compte" }).click();
  await expect(page).toHaveURL(/\/team$/);
  if (team.create) {
    await page.getByLabel(/Nom de l.équipe/).fill(team.create);
    await page.getByRole("button", { name: "Créer", exact: true }).click();
  } else if (team.join) {
    await page.getByLabel(/Code d.invitation/).fill(team.join);
    await page.getByRole("button", { name: "Rejoindre" }).click();
  }
  await expect(page.locator(".code-valeur")).toBeVisible();
  return page;
}

async function solve(page: Page, challenge: string | RegExp, flag: string): Promise<void> {
  await page.getByRole("link", { name: challenge }).click();
  const dialog = page.getByRole("dialog");
  await dialog.locator("#flag").fill(flag);
  await dialog.getByRole("button", { name: "Valider" }).click();
  await expect(dialog.getByRole("heading", { name: "Défi résolu" })).toBeVisible();
}

const recompenses = (page: Page) => page.getByRole("dialog").locator(".reussite");

test("verrous, objets et défi final caché", async ({ browser }) => {
  const page = await newPlayer(browser, { create: `Explorateurs ${counter}` });
  await page.goto("/challenges");

  const verrouille = page.locator('.etage[data-etat="verrouille"]');
  await expect(verrouille).toContainText("Niveau supérieur");
  await expect(verrouille).toContainText("Résous deux défis de cryptographie");
  await expect(page.getByText("Le coffre")).toHaveCount(0);

  await solve(page, /Mille-feuille/, "DEMO{trois_couches_suffisent}");
  await expect(recompenses(page)).toContainText(/Objet obtenu\s*:\s*Clé de cryptographie/);
  await page.keyboard.press("Escape");

  await solve(page, /Quelle ville/, "DEMO{lyon}");
  await expect(recompenses(page)).toContainText(/Défi débloqué\s*:\s*Le coffre/);
  await page.keyboard.press("Escape");

  await solve(page, /Le coffre/, "DEMO{coffre_ouvert}");
  await expect(recompenses(page)).toContainText(/Le coffre s.ouvre/);
  await page.keyboard.press("Escape");

  await page.goto("/team");
  await expect(page.locator(".fils")).toContainText("Clé de cryptographie");
  await expect(page.locator(".fils")).toContainText(/Clé d.OSINT/);
});

test("indices et messages", async ({ browser }) => {
  const page = await newPlayer(browser, { create: `Lecteurs ${counter}` });
  await page.goto("/challenges");

  await page.getByRole("link", { name: /Ave César/ }).click();
  const dialog = page.getByRole("dialog");
  await expect(dialog.locator(".indices li").first()).toContainText("gratuit");
  await dialog.getByRole("button", { name: /Voir l.indice/ }).first().click();
  await expect(dialog.locator(".indices li").first()).toContainText("empereur romain");
  await page.keyboard.press("Escape");

  await solve(page, /Bienvenue/, "DEMO{bienvenue_a_bord}");
  await expect(recompenses(page)).toContainText(/Nouveau message\s*:\s*Premiers pas/);
  await page.keyboard.press("Escape");

  // Le thème du pack de démo renomme « Messages » en « Carnet ».
  const carnet = page.getByRole("link", { name: /Carnet/ });
  await expect(carnet.locator(".compteur")).toHaveText("2");
  await carnet.click();
  await expect(page.getByRole("heading", { name: "Premiers pas" })).toBeVisible();
  await expect(page.getByText(/1 message encore chiffré/)).toBeVisible();
  await expect(carnet.locator(".compteur")).toHaveCount(0);
});

test("temps réel : coéquipiers, déblocage et premier sang", async ({ browser }) => {
  const alice = await newPlayer(browser, { create: `Temps Réel ${counter}` });
  const invite = (await alice.locator(".code-valeur").textContent())!;
  const carol = await newPlayer(browser, { join: invite });
  const rival = await newPlayer(browser, { create: `Rivaux ${counter}` });
  for (const page of [carol, rival, alice]) await page.goto("/challenges");
  // Laisse les flux temps réel s'établir.
  await alice.waitForTimeout(500);

  const chronique = (page: Page, texte: RegExp) => page.locator(".chroniques .chronique", { hasText: texte });

  // La coéquipière est prévenue et son plan se met à jour sans recharger la page.
  await solve(alice, /Ave César/, "DEMO{jules_serait_fier}");
  await expect(chronique(carol, /a résolu.*Ave César/)).toBeVisible();
  await expect(carol.locator('.etage[data-etat="resolu"]')).toContainText("Ave César");
  await alice.keyboard.press("Escape");

  // Le déblocage gagné par Alice apparaît aussi chez Carol.
  await solve(alice, /Mille-feuille/, "DEMO{trois_couches_suffisent}");
  await expect(chronique(carol, /Nouveau défi\s*:\s*Niveau supérieur/)).toBeVisible();
  await expect(carol.getByRole("link", { name: /Niveau supérieur/ })).toBeVisible();
  await alice.keyboard.press("Escape");

  // Personne n'a encore résolu « Niveau supérieur » : l'équipe rivale voit le premier sang.
  await solve(alice, /Niveau supérieur/, "DEMO{niveau_superieur}");
  await expect(recompenses(alice)).toContainText("Premier sang");
  await expect(chronique(rival, /Premier sang.*Niveau supérieur/)).toBeVisible();
  // … mais rien de ce qui est propre à l'équipe d'Alice.
  await expect(chronique(rival, /a résolu/)).toHaveCount(0);
  await expect(rival.locator('.etage[data-etat="verrouille"]')).toContainText("Niveau supérieur");
});
