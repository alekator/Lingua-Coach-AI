import { expect, test } from "@playwright/test";

test("seeded profile opens dashboard and chat", async ({ page, request }) => {
  await request.post("http://127.0.0.1:8000/app/reset", {
    data: { confirmation: "RESET" },
  });
  await request.post("http://127.0.0.1:8000/profile/setup", {
    data: {
      user_id: 1,
      native_lang: "ru",
      target_lang: "en",
      level: "A2",
      goal: "travel",
      preferences: { strictness: "medium", daily_minutes: 15 },
    },
  });

  await page.goto("/app");
  await expect(page).toHaveURL(/\/app$/);
  await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();
  await expect(page.getByText("OpenAI key is not configured.")).toBeVisible();

  await page.locator("a[href='/app/chat']").first().click();
  await expect(page).toHaveURL(/\/app\/chat$/);
  await expect(page.getByRole("heading", { name: "Coach Chat Studio" })).toBeVisible();
});
