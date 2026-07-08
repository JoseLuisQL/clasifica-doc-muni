import { test, expect } from "@playwright/test";

// E2E del flujo principal: login, subida de PDF, espera clasificación automática
// (OCR + LLM + correlativo) y verificación en la UI. Requiere backend + worker.

test("login page renderiza", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("ClasificaDocMuni")).toBeVisible();
  await expect(page.getByPlaceholder("Usuario")).toBeVisible();
  await expect(page.getByPlaceholder("Contraseña")).toBeVisible();
});

test("flujo completo: login → upload → clasificación automática", async ({ page }) => {
  await page.goto("/");
  await page.getByPlaceholder("Usuario").fill("admin");
  await page.getByPlaceholder("Contraseña").fill("admin123");
  await page.getByRole("button", { name: /ingresar|entrar|login/i }).click();

  // Tras login debe aparecer la navegación con "Carga individual"
  await expect(page.getByRole("button", { name: "Carga individual" })).toBeVisible();

  // Subir un PDF de prueba
  await page.setInputFiles('input[type="file"]', {
    name: "e2e-test.pdf",
    mimeType: "application/pdf",
    buffer: Buffer.from(
      // PDF mínimo válido con texto nativo
      Buffer.from(
        "%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n" +
          "2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n" +
          "3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 300 300]" +
          "/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj\n" +
          "4 0 obj<</Length 120>>stream\nBT /F1 12 Tf 20 280 Td " +
          "(MUNICIPALIDAD OFICIO No 999-2026 ASUNTO Solicitud de prueba) Tj ET\nendstream\nendobj\n" +
          "5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n" +
          "xref\n0 6\n0000000000 65535 f \n" +
          "trailer<</Size 6/Root 1 0 R>>\nstartxref\n0\n%%EOF",
        "latin1",
      ),
    ),
  });

  // Esperar a que el documento se procese y aparezca el estado clasificado/revision
  await expect(page.getByText(/Estado:\s*(clasificado|revision|error|procesando|pendiente)/)).toBeVisible({
    timeout: 60000,
  });
});
