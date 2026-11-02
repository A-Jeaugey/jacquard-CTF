import { expect, test, type Page } from "@playwright/test";

async function register(page: Page, username: string): Promise<void> {
  await page.goto("/register");
  await page.getByLabel("Pseudo").fill(username);
  await page.getByLabel("Mot de passe").fill("motdepasse-solide");
  await page.getByRole("button", { name: "Créer mon compte" }).click();
  await expect(page).toHaveURL(/\/team$/);
}

test("parcours joueur : inscription, équipe, défi, classement", async ({ page, browser }) => {
  await register(page, "alice");
  await page.getByLabel("Nom de l'équipe").fill("Les Testeurs");
  await page.getByRole("button", { name: "Créer", exact: true }).click();
  const invite = await page.locator(".invite").textContent();
  expect(invite).toMatch(/^[A-Z2-9]{10}$/);

  // Un coéquipier rejoint avec le code d'invitation.
  const bob = await (await browser.newContext()).newPage();
  await register(bob, "bob");
  await bob.getByLabel("Code d'invitation").fill(invite!);
  await bob.getByRole("button", { name: "Rejoindre" }).click();
  await expect(bob.getByRole("heading", { name: "Les Testeurs" })).toBeVisible();

  await page.getByRole("link", { name: "Défis" }).click();
  await page.getByRole("button", { name: /Ave César/ }).click();
  const dialog = page.getByRole("dialog");
  await expect(dialog.getByRole("heading", { name: "Ave César" })).toBeVisible();

  await dialog.locator("#flag").fill("DEMO{faux}");
  await dialog.getByRole("button", { name: "Valider" }).click();
  await expect(dialog.getByRole("status")).toHaveText("Ce n'est pas le bon flag.");

  const download = page.waitForEvent("download");
  await dialog.getByRole("link", { name: "message.txt" }).click();
  expect((await download).suggestedFilename()).toBe("message.txt");

  await dialog.locator("#flag").fill("demo{jules_serait_fier}");
  await dialog.getByRole("button", { name: "Valider" }).click();
  await expect(dialog.getByRole("status")).toHaveText("Bravo, flag correct !");
  await page.keyboard.press("Escape");
  await expect(page.locator(".challenge-card.solved")).toHaveCount(1);

  // Le coéquipier voit le défi résolu.
  await bob.goto("/challenges");
  await expect(bob.locator(".challenge-card.solved")).toContainText("Ave César");

  await page.getByRole("link", { name: "Classement" }).click();
  const row = page.locator("table.scoreboard tbody tr").first();
  await expect(row).toContainText("Les Testeurs");
  await expect(row).toContainText("530");
});

test("l'admin voit les soumissions", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Pseudo").fill("orga");
  await page.getByLabel("Mot de passe").fill("admin-password-123");
  await page.getByRole("button", { name: "Se connecter" }).click();
  await page.getByRole("link", { name: "Admin" }).click();
  await expect(page.locator("table tbody tr").first()).toContainText("demo{jules_serait_fier}");
});

test("les routes protégées redirigent vers la connexion", async ({ page }) => {
  await page.goto("/challenges");
  await expect(page).toHaveURL(/\/login$/);
});
