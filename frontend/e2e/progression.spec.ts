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
    await page.getByLabel("Nom de l'équipe").fill(team.create);
    await page.getByRole("button", { name: "Créer", exact: true }).click();
  } else if (team.join) {
    await page.getByLabel("Code d'invitation").fill(team.join);
    await page.getByRole("button", { name: "Rejoindre" }).click();
  }
  await expect(page.locator("h1")).toContainText(team.create ?? "");
  return page;
}

async function solve(page: Page, challenge: string | RegExp, flag: string): Promise<void> {
  await page.getByRole("button", { name: challenge }).click();
  const dialog = page.getByRole("dialog");
  await dialog.locator("#flag").fill(flag);
  await dialog.getByRole("button", { name: "Valider" }).click();
  await expect(dialog.getByRole("status")).toHaveText("Bravo, flag correct !");
}

test("verrous, objets et défi final caché", async ({ browser }) => {
  const page = await newPlayer(browser, { create: `Explorateurs ${counter}` });
  await page.goto("/challenges");

  const teaser = page.locator(".challenge-card.locked");
  await expect(teaser).toContainText("Niveau supérieur");
  await expect(teaser).toContainText("Résous deux défis de cryptographie");
  await expect(page.getByText("Le coffre")).toHaveCount(0);

  await solve(page, /Mille-feuille/, "DEMO{trois_couches_suffisent}");
  await expect(page.locator(".rewards")).toContainText("Objet obtenu : Clé de cryptographie");
  await page.keyboard.press("Escape");

  await solve(page, /Quelle ville/, "DEMO{lyon}");
  await expect(page.locator(".rewards")).toContainText("Nouveau défi débloqué : Le coffre");
  await page.keyboard.press("Escape");

  await solve(page, /Le coffre/, "DEMO{coffre_ouvert}");
  await expect(page.locator(".notification")).toContainText("Le coffre s'ouvre");
  await page.keyboard.press("Escape");

  await page.goto("/team");
  await expect(page.locator(".inventory")).toContainText("Clé de cryptographie");
  await expect(page.locator(".inventory")).toContainText("Clé d'OSINT");
});

test("indices et journal", async ({ browser }) => {
  const page = await newPlayer(browser, { create: `Lecteurs ${counter}` });
  await page.goto("/challenges");

  await page.getByRole("button", { name: /Ave César/ }).click();
  const dialog = page.getByRole("dialog");
  await expect(dialog.locator(".hint").first()).toContainText("Gratuit");
  await dialog.getByRole("button", { name: "Révéler" }).first().click();
  await expect(dialog.locator(".hint").first()).toContainText("empereur romain");
  await page.keyboard.press("Escape");

  await solve(page, /Bienvenue/, "DEMO{bienvenue_a_bord}");
  await expect(page.locator(".rewards")).toContainText("Nouveau chapitre dans le journal : Premiers pas");
  await page.keyboard.press("Escape");

  const journal = page.getByRole("link", { name: /Journal/ });
  await expect(journal.locator(".badge")).toHaveText("2");
  await journal.click();
  await expect(page.getByRole("heading", { name: "Premiers pas" })).toBeVisible();
  await expect(page.getByText("1 chapitre(s) encore à découvrir.")).toBeVisible();
  await expect(journal.locator(".badge")).toHaveCount(0);
});

test("temps réel : coéquipiers, déblocage et premier sang", async ({ browser }) => {
  const alice = await newPlayer(browser, { create: `Temps Réel ${counter}` });
  const invite = (await alice.locator(".invite").textContent())!;
  const carol = await newPlayer(browser, { join: invite });
  const rival = await newPlayer(browser, { create: `Rivaux ${counter}` });
  for (const page of [carol, rival, alice]) await page.goto("/challenges");
  // Laisse les flux temps réel s'établir.
  await alice.waitForTimeout(500);

  // La coéquipière est prévenue et son tableau se met à jour sans recharger la page.
  await solve(alice, /Ave César/, "DEMO{jules_serait_fier}");
  await expect(carol.locator(".toast", { hasText: "a résolu « Ave César »" })).toBeVisible();
  await expect(carol.locator(".challenge-card.solved")).toContainText("Ave César");
  await alice.keyboard.press("Escape");

  // Le déblocage gagné par Alice apparaît aussi chez Carol.
  await solve(alice, /Mille-feuille/, "DEMO{trois_couches_suffisent}");
  await expect(carol.locator(".toast", { hasText: "Nouveau défi : Niveau supérieur" })).toBeVisible();
  await expect(carol.getByRole("button", { name: /Niveau supérieur/ })).toBeVisible();
  await alice.keyboard.press("Escape");

  // Personne n'a encore résolu « Niveau supérieur » : l'équipe rivale voit le premier sang.
  await solve(alice, /Niveau supérieur/, "DEMO{niveau_superieur}");
  await expect(alice.locator(".rewards")).toContainText("Premier sang");
  await expect(rival.locator(".toast", { hasText: "premier sang sur « Niveau supérieur »" })).toBeVisible();
  // … mais rien de ce qui est propre à l'équipe d'Alice.
  await expect(rival.locator(".toast", { hasText: "a résolu" })).toHaveCount(0);
  await expect(rival.locator(".challenge-card.locked")).toContainText("Niveau supérieur");
});
