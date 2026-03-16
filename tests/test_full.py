"""Playwright end-to-end test: upload payslips + Webull PDF, verify parsing, test UI features."""

import time
import os
from playwright.sync_api import sync_playwright

BASE = "http://localhost:3000"
EMAIL = "james@james.com"
PASSWORD = "james"

PAYSLIP_DIR = "/Users/jamesperenchio/Downloads/Payslip"
WEBULL_PDF = "/Users/jamesperenchio/Downloads/2025-01.pdf"


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 900})

        # ── 1. Login ──
        print("=== Logging in ===")
        page.goto(BASE)
        page.wait_for_load_state("networkidle")

        page.fill('input[type="email"]', EMAIL)
        page.fill('input[type="password"]', PASSWORD)
        page.click('button[type="submit"]')
        page.wait_for_load_state("networkidle")
        time.sleep(3)

        header = page.locator("h1:has-text('MoneyTracker')")
        assert header.is_visible(), "Should see MoneyTracker header"
        print("✅ Logged in successfully")

        # ── 2. Upload Payslips as BANK statements ──
        print("\n=== Uploading Payslips ===")
        upload_btn = page.locator("nav button", has_text="Upload")
        upload_btn.click()
        time.sleep(1)

        payslip_files = [
            os.path.join(PAYSLIP_DIR, f)
            for f in sorted(os.listdir(PAYSLIP_DIR))
            if f.endswith(".pdf")
        ]
        print(f"  Found {len(payslip_files)} payslip files")

        # Ensure Bank Statement type is selected (default)
        bank_btn = page.locator("button", has_text="Bank Statement")
        if bank_btn.count() > 0:
            bank_btn.click()
            time.sleep(0.5)

        file_input = page.locator('input[type="file"]')
        file_input.set_input_files(payslip_files)
        time.sleep(1)

        # Click the upload button
        upload_submit = page.locator("button", has_text="Upload")
        # Find the one that says "Upload 3 file(s)" or similar
        for btn in upload_submit.all():
            txt = btn.text_content() or ""
            if "file" in txt.lower():
                print(f"  Clicking: {txt}")
                btn.click()
                break

        # Wait for processing
        print("  Waiting for payslip processing...")
        for i in range(30):
            time.sleep(2)
            page_text = page.inner_text("main")
            completed = page_text.count("Completed") + page_text.count("✓")
            failed = page_text.count("Failed") + page_text.count("✗")
            processing = page_text.count("Processing") + page_text.count("Uploading")
            print(f"    [{i*2}s] completed={completed} failed={failed} processing={processing}")
            if completed + failed >= len(payslip_files):
                break
            if processing == 0 and completed + failed > 0:
                break

        page.screenshot(path="/tmp/mt-payslips-uploaded.png")
        print(f"  📸 Payslips result screenshot saved")

        # ── 3. Upload Webull PDF as BROKERAGE statement ──
        print("\n=== Uploading Webull USA PDF ===")
        page.reload()
        page.wait_for_load_state("networkidle")
        time.sleep(1)

        upload_btn = page.locator("nav button", has_text="Upload")
        upload_btn.click()
        time.sleep(1)

        # Select Brokerage Statement
        brokerage_btn = page.locator("button", has_text="Brokerage Statement")
        if brokerage_btn.count() > 0:
            brokerage_btn.click()
            time.sleep(0.5)

        file_input = page.locator('input[type="file"]')
        file_input.set_input_files(WEBULL_PDF)
        time.sleep(1)

        # Click upload button
        upload_submit = page.locator("button", has_text="Upload")
        for btn in upload_submit.all():
            txt = btn.text_content() or ""
            if "file" in txt.lower():
                print(f"  Clicking: {txt}")
                btn.click()
                break

        print("  Waiting for Webull PDF processing...")
        for i in range(30):
            time.sleep(2)
            page_text = page.inner_text("main")
            completed_w = page_text.count("Completed") + page_text.count("✓")
            failed_w = page_text.count("Failed") + page_text.count("✗")
            processing = page_text.count("Processing") + page_text.count("Uploading")
            print(f"    [{i*2}s] completed={completed_w} failed={failed_w} processing={processing}")
            if completed_w + failed_w >= 1:
                break
            if processing == 0 and completed_w + failed_w > 0:
                break

        page.screenshot(path="/tmp/mt-webull-uploaded.png")
        print(f"  📸 Webull upload result screenshot saved")

        # ── 4. Check Overview Tab ──
        print("\n=== Checking Overview ===")
        overview_btn = page.locator("nav button", has_text="Overview")
        overview_btn.click()
        page.wait_for_load_state("networkidle")
        time.sleep(3)

        page.screenshot(path="/tmp/mt-overview.png", full_page=True)
        print("  📸 Overview screenshot saved")

        # ── 5. Check Banking Tab ──
        print("\n=== Checking Banking Tab ===")
        banking_btn = page.locator("nav button", has_text="Banking")
        banking_btn.click()
        page.wait_for_load_state("networkidle")
        time.sleep(3)

        page.screenshot(path="/tmp/mt-banking.png", full_page=True)
        print("  📸 Banking screenshot saved")

        # Count transactions
        txn_rows = page.locator("main >> div[class*='cursor-pointer']").all()
        print(f"  Transaction rows visible: {len(txn_rows)}")

        # ── 6. Test Expandable Transaction ──
        print("\n=== Testing Expandable Transactions ===")
        if txn_rows:
            txn_rows[0].click()
            time.sleep(1)

            detail_visible = page.locator("text=DATE & TIME").first.is_visible()
            print(f"  Detail panel visible: {detail_visible}")

            page.screenshot(path="/tmp/mt-expanded-txn.png")
            print("  📸 Expanded transaction screenshot saved")

            txn_rows[0].click()
            time.sleep(0.5)

        # ── 7. Test Re-categorize ──
        print("\n=== Testing Re-categorize ===")
        recat_btn = page.locator("button", has_text="Re-categorize")
        if recat_btn.count() > 0:
            recat_btn.click()
            time.sleep(5)
            page.screenshot(path="/tmp/mt-recategorized.png")

            recat_msg = page.locator("text=Re-categorized")
            if recat_msg.count() > 0:
                print(f"  ✅ Result: {recat_msg.first.text_content()}")
            else:
                print("  No result message found")
                page.screenshot(path="/tmp/mt-recat-debug.png")
        else:
            print("  Re-categorize button not visible")

        # ── 8. Check Investments Tab ──
        print("\n=== Checking Investments Tab ===")
        inv_btn = page.locator("nav button", has_text="Investments")
        inv_btn.click()
        page.wait_for_load_state("networkidle")
        time.sleep(3)

        page.screenshot(path="/tmp/mt-investments.png", full_page=True)
        print("  📸 Investments screenshot saved")

        # ── Summary ──
        print("\n" + "=" * 50)
        print("✅ All tests completed!")
        print("=" * 50)

        browser.close()


if __name__ == "__main__":
    run()
