import { expect, test, type Page } from "@playwright/test";

let counter = 0;

async function newTeam(page: Page, team: string): Promise<void> {
  const username = `carto${Date.now() % 100000}${counter++}`;
  await page.goto("/register");
  await page.getByLabel("Pseudo").fill(username);
  await page.getByLabel("Mot de passe").fill("motdepasse-solide");
  await page.getByRole("button", { name: "Créer mon compte" }).click();
  await expect(page).toHaveURL(/\/team$/);
  await page.getByLabel("Nom de l'équipe").fill(team);
  await page.getByRole("button", { name: "Créer", exact: true }).click();
  await expect(page.locator(".invite")).toBeVisible();
}

test("le thème du pack s'applique : libellés et couleurs", async ({ page }) => {
  await newTeam(page, `Thème ${counter}`);
  await page.goto("/challenges");
  await expect(page.getByRole("heading", { name: "Le plan du coffre" })).toBeVisible();
  const accent = await page.evaluate(() => getComputedStyle(document.documentElement).getPropertyValue("--color-accent").trim());
  expect(accent).toBe("#38bdf8");
  await expect(page.locator("link[data-theme-css]")).toHaveCount(1);
});

test("la carte reflète la progression et filtre les défis", async ({ page }) => {
  await newTeam(page, `Cartographes ${counter}`);
  await page.goto("/challenges");
  const crypto = page.locator("#zone-crypto");
  await expect(crypto).toHaveClass(/is-available/);

  await page.getByRole("button", { name: /Ave César/ }).click();
  await page.locator("#flag").fill("DEMO{jules_serait_fier}");
  await page.getByRole("button", { name: "Valider" }).click();
  await expect(page.getByRole("dialog").getByRole("status")).toHaveText("Bravo, flag correct !");
  await page.keyboard.press("Escape");

  await expect(crypto).toHaveClass(/is-in-progress/);
  await expect(page.locator(".zone-chip", { hasText: "La salle des chiffres : 1/3" })).toBeVisible();

  // Filtre : clic sur la zone, puis clavier sur la pastille pour tout réafficher.
  await crypto.click();
  await expect(page.locator(".column-title")).toHaveText([/Cryptographie/]);
  await page.locator(".zone-chip", { hasText: "La salle des chiffres : 1/3" }).press("Enter");
  await expect(page.locator(".column-title")).toHaveCount(3);

  // Vue grille : la carte disparaît, le choix est mémorisé.
  await page.getByRole("button", { name: "Vue grille" }).click();
  await expect(page.locator(".map-canvas")).toHaveCount(0);
  await page.reload();
  await expect(page.locator(".map-canvas")).toHaveCount(0);
  await page.getByRole("button", { name: "Vue carte" }).click();
  await expect(page.locator(".map-canvas svg")).toBeVisible();
});

test("le grand écran est public et ne révèle pas les défis", async ({ page }) => {
  await page.goto("/ecran/projecteur");
  await expect(page.getByRole("heading", { name: "Démo — grand écran" })).toBeVisible();
  await expect(page.locator(".map-canvas svg")).toBeVisible();
  await expect(page.locator(".screen-top li").first()).toBeVisible();
  await expect(page.locator("nav")).toHaveCount(0);
  const text = await page.locator(".screen").textContent();
  expect(text).not.toContain("Le coffre");
  expect(text).not.toContain("DEMO{");
});
