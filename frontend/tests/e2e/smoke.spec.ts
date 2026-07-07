import { test, expect } from "@playwright/test";

// E2E básico: la página de login se renderiza. Requiere el frontend
// corriendo (npm run dev) y el backend disponible para el flujo completo.
test("login page renderiza", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("ClasificaDocMuni")).toBeVisible();
  await expect(page.getByPlaceholder("Usuario")).toBeVisible();
  await expect(page.getByPlaceholder("Contraseña")).toBeVisible();
});
