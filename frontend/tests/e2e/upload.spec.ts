import { test, expect, Page } from "@playwright/test";
import path from "path";
import fs from "fs";
import os from "os";

const BASE = "http://localhost:3000";
const EMAIL = "james@james.com";
const PASSWORD = "james";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
async function loginAndGoToUpload(page: Page) {
  await page.goto(BASE);
  await expect(page.getByPlaceholder("Email")).toBeVisible();
  await page.getByPlaceholder("Email").fill(EMAIL);
  await page.getByPlaceholder("Password").fill(PASSWORD);
  await page.getByRole("button", { name: "Sign In" }).click();
  await expect(page.getByRole("button", { name: /Upload/i })).toBeVisible({ timeout: 10_000 });
  await page.getByRole("button", { name: /Upload/i }).click();
  await expect(page.getByText("Upload Statements")).toBeVisible();
}

function makeTempCsv(content: string): string {
  const tmpPath = path.join(os.tmpdir(), `test_${Date.now()}.csv`);
  fs.writeFileSync(tmpPath, content);
  return tmpPath;
}

function panel(page: Page, type: "bank" | "credit_card" | "brokerage") {
  return page.locator(`[data-testid="upload-panel-${type}"]`);
}

// ---------------------------------------------------------------------------
// Auth tests
// ---------------------------------------------------------------------------
test.describe("Auth", () => {
  test("shows login form on first visit", async ({ page }) => {
    await page.goto(BASE);
    await expect(page.getByPlaceholder("Email")).toBeVisible();
    await expect(page.getByPlaceholder("Password")).toBeVisible();
    await expect(page.getByRole("button", { name: "Sign In" })).toBeVisible();
  });

  test("shows error for wrong credentials", async ({ page }) => {
    await page.goto(BASE);
    await page.getByPlaceholder("Email").fill("wrong@wrong.com");
    await page.getByPlaceholder("Password").fill("badpassword");
    await page.getByRole("button", { name: "Sign In" }).click();
    await expect(page.locator("p").filter({ hasText: /failed|incorrect|invalid/i })).toBeVisible({ timeout: 5_000 });
  });

  test("logs in with valid credentials and shows dashboard nav", async ({ page }) => {
    await page.goto(BASE);
    await page.getByPlaceholder("Email").fill(EMAIL);
    await page.getByPlaceholder("Password").fill(PASSWORD);
    await page.getByRole("button", { name: "Sign In" }).click();
    await expect(page.getByRole("button", { name: /Overview/i })).toBeVisible({ timeout: 10_000 });
    await expect(page.getByRole("button", { name: /Investments/i })).toBeVisible();
    await expect(page.getByRole("button", { name: /Banking/i })).toBeVisible();
    await expect(page.getByRole("button", { name: /Upload/i })).toBeVisible();
  });
});

// ---------------------------------------------------------------------------
// Upload tab layout
// ---------------------------------------------------------------------------
test.describe("Upload Tab layout", () => {
  test("shows three separate upload panels", async ({ page }) => {
    await loginAndGoToUpload(page);
    await expect(panel(page, "bank")).toBeVisible();
    await expect(panel(page, "credit_card")).toBeVisible();
    await expect(panel(page, "brokerage")).toBeVisible();
  });

  test("bank panel heading is 'Bank Statement'", async ({ page }) => {
    await loginAndGoToUpload(page);
    await expect(panel(page, "bank").getByRole("heading", { name: "Bank Statement" })).toBeVisible();
  });

  test("bank panel shows supported Thai institutions", async ({ page }) => {
    await loginAndGoToUpload(page);
    const p = panel(page, "bank");
    await expect(p.getByText("Kasikorn (KBank)")).toBeVisible();
    await expect(p.getByText("SCB")).toBeVisible();
    await expect(p.getByText("Bangkok Bank")).toBeVisible();
  });

  test("brokerage panel shows supported brokerages", async ({ page }) => {
    await loginAndGoToUpload(page);
    const p = panel(page, "brokerage");
    await expect(p.getByText("Webull USA")).toBeVisible();
    await expect(p.getByText("Webull Thailand")).toBeVisible();
    await expect(p.getByText("Dime")).toBeVisible();
  });

  test("CC panel shows reconciliation subtitle", async ({ page }) => {
    await loginAndGoToUpload(page);
    await expect(panel(page, "credit_card").getByText(/auto-links to your bank payoff/i)).toBeVisible();
  });

  test("upload tab shows CC reconciliation how-to section", async ({ page }) => {
    await loginAndGoToUpload(page);
    await expect(page.getByRole("heading", { name: /How CC reconciliation works/i })).toBeVisible();
    await expect(page.getByText(/bank statement/i).first()).toBeVisible();
  });
});

// ---------------------------------------------------------------------------
// Upload functionality
// ---------------------------------------------------------------------------
test.describe("Upload functionality", () => {
  test("uploading a bank CSV shows audit trail panel", async ({ page }) => {
    await loginAndGoToUpload(page);

    const csv = [
      "Date,Description,Debit,Credit,Balance",
      "2026-02-01,GRAB FOOD,150,,9850",
      "2026-02-05,SALARY,,30000,39850",
      "2026-02-28,CREDIT CARD PAYMENT,25000,,14850",
    ].join("\n");
    const csvPath = makeTempCsv(csv);

    await panel(page, "bank").locator('input[type="file"]').setInputFiles(csvPath);

    // Audit trail card should appear (file name shown)
    await expect(page.getByText(/\.csv/i)).toBeVisible({ timeout: 10_000 });
    // Status badge appears
    await expect(page.locator(".rounded-full").filter({ hasText: /pending|processing|completed|failed/i })).toBeVisible({ timeout: 10_000 });

    fs.unlinkSync(csvPath);
  });

  test("uploading a brokerage CSV shows audit trail panel", async ({ page }) => {
    await loginAndGoToUpload(page);

    const csv = [
      "Date,Action,Symbol,Quantity,Price,Amount,Fees",
      "2026-02-10,buy,AAPL,10,180.50,1805.00,1.50",
      "2026-02-15,buy,TSLA,5,200.00,1000.00,1.00",
    ].join("\n");
    const csvPath = makeTempCsv(csv);

    await panel(page, "brokerage").locator('input[type="file"]').setInputFiles(csvPath);

    await expect(page.getByText(/\.csv/i)).toBeVisible({ timeout: 10_000 });
    await expect(page.locator(".rounded-full").filter({ hasText: /pending|processing|completed|failed/i })).toBeVisible({ timeout: 10_000 });

    fs.unlinkSync(csvPath);
  });

  test("uploading a credit card CSV shows audit trail panel", async ({ page }) => {
    await loginAndGoToUpload(page);

    const csv = [
      "Date,Description,Amount,Type",
      "2026-02-02,SHOPEE PURCHASE,500,debit",
      "2026-02-10,GRAB FOOD,180,debit",
      "2026-02-28,PAYMENT RECEIVED,680,credit",
    ].join("\n");
    const csvPath = makeTempCsv(csv);

    await panel(page, "credit_card").locator('input[type="file"]').setInputFiles(csvPath);

    await expect(page.getByText(/\.csv/i)).toBeVisible({ timeout: 10_000 });
    await expect(page.locator(".rounded-full").filter({ hasText: /pending|processing|completed|failed/i })).toBeVisible({ timeout: 10_000 });

    fs.unlinkSync(csvPath);
  });

  test("rejects unsupported file type (.txt) with error message", async ({ page }) => {
    await loginAndGoToUpload(page);

    const tmpPath = path.join(os.tmpdir(), "test.txt");
    fs.writeFileSync(tmpPath, "not a valid file");

    await panel(page, "bank").locator('input[type="file"]').setInputFiles(tmpPath);

    await expect(page.getByText(/not supported|Upload failed/i)).toBeVisible({ timeout: 8_000 });

    fs.unlinkSync(tmpPath);
  });
});

// ---------------------------------------------------------------------------
// Dashboard tabs
// ---------------------------------------------------------------------------
test.describe("Dashboard tabs", () => {
  test("Overview tab shows stat cards", async ({ page }) => {
    await loginAndGoToUpload(page);
    await page.getByRole("button", { name: /Overview/i }).click();
    await expect(page.getByText("Net Worth")).toBeVisible();
    await expect(page.getByText("Total Investments")).toBeVisible();
    await expect(page.getByText("Monthly Spending")).toBeVisible();
  });

  test("Investments tab renders portfolio section", async ({ page }) => {
    await loginAndGoToUpload(page);
    await page.getByRole("button", { name: /Investments/i }).click();
    await expect(page.getByText("Portfolio Value")).toBeVisible();
    await expect(page.getByRole("heading", { name: "Holdings" })).toBeVisible();
  });

  test("Banking tab renders transactions section", async ({ page }) => {
    await loginAndGoToUpload(page);
    await page.getByRole("button", { name: /Banking/i }).click();
    await expect(page.getByText("Total Cash")).toBeVisible();
    await expect(page.getByRole("heading", { name: "All Transactions" })).toBeVisible();
  });
});
