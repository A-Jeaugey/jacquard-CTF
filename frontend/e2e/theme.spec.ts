import { expect, test, type Page } from "@playwright/test";

let counter = 0;

async function newTeam(page: Page, team: string): Promise<void> {
  const username = `carto${Date.now() % 100000}${counter++}`;
  await page.goto("/register");
  await page.getByLabel("Pseudo").fill(username);
  await page.getByLabel("Mot de passe").fill("motdepasse-solide");
  await page.getByRole("button", { name: "Créer mon compte" }).click();
  await expect(page).toHaveURL(/\/team$/);
  // Nom unique : la base de test survit d'un passage à l'autre (tests répétés).
  await page.getByLabel(/Nom de l.équipe/).fill(`${team} ${username.slice(5)}`);
  await page.getByRole("button", { name: "Créer", exact: true }).click();
  await expect(page.locator(".code-valeur")).toBeVisible();
}

test("le thème du pack change les libellés, pas la direction artistique", async ({ page }) => {
  await newTeam(page, `Thème ${counter}`);
  await page.goto("/challenges");
  await expect(page.getByRole("heading", { name: "Le plan du coffre" })).toBeVisible();
  // Les couleurs et les polices sont celles de DESIGN.md, quel que soit le pack.
  const lumignon = await page.evaluate(() => getComputedStyle(document.documentElement).getPropertyValue("--lumignon").trim());
  expect(lumignon.toLowerCase()).toBe("#f5a23d");
  await expect(page.locator("link[data-theme-css]")).toHaveCount(0);
});

test("la ville reflète la progression et filtre les défis", async ({ page }) => {
  await newTeam(page, `Cartographes ${counter}`);
  await page.goto("/challenges");
  const crypto = page.locator('.carte .quartier[data-categorie="crypto"]');
  await expect(crypto).toHaveAttribute("aria-label", /Cryptographie\s*:\s*0 sur 3/);
  await expect(crypto.locator('.fen[data-etat="resolu"]')).toHaveCount(0);

  await page.getByRole("link", { name: /Ave César/ }).click();
  await page.locator("#flag").fill("DEMO{jules_serait_fier}");
  await page.getByRole("button", { name: "Valider" }).click();
  await expect(page.locator("section.panneau").getByRole("heading", { name: "Défi résolu" })).toBeVisible();
  await page.keyboard.press("Escape");

  await expect(crypto).toHaveAttribute("aria-label", /Cryptographie\s*:\s*1 sur 3/);
  await expect(crypto.locator('.fen[data-etat="resolu"]')).toHaveCount(1);

  // Choisir un quartier n'affiche que ses défis ; « Revoir toute la ville » rend tout.
  const sections = page.locator("section.quartier-liste");
  const total = await sections.count();
  expect(total).toBeGreaterThan(1);
  await crypto.click();
  await expect(crypto).toHaveAttribute("aria-pressed", "true");
  await expect(sections).toHaveCount(1);
  await expect(sections.getByRole("heading", { level: 2 })).toHaveText("Cryptographie");
  await page.getByRole("button", { name: "Revoir toute la ville" }).first().click();
  await expect(sections).toHaveCount(total);
  await expect(crypto).toBeFocused();
});

test("le grand écran est public et ne révèle pas les défis", async ({ page }) => {
  await page.goto("/ecran/projecteur");
  await expect(page.getByRole("heading", { level: 1 })).toContainText(/Démo/);
  await expect(page.locator(".carte")).toBeVisible();
  await expect(page.locator(".classement li").first()).toBeVisible();
  await expect(page.locator("nav")).toHaveCount(0);
  const text = await page.locator(".ecran").textContent();
  expect(text).not.toContain("Le coffre");
  expect(text).not.toContain("DEMO{");
});
