import asyncio
import os
import httpx
from playwright.async_api import async_playwright

class EpsteinDataDownloader:
    def __init__(self):
        self.base_url = "https://www.justice.gov/epstein/doj-disclosures/data-set-{}-files?page={}"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Referer": "https://www.google.com/"
        }
        self.root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.base_folder = os.path.join(self.root_dir, "Epstein Files")
        self.min_pdf_size = 1024

    async def setup_browser(self, p):
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent=self.headers["User-Agent"])
        return browser, context

    async def handle_robot_check(self, page):
        try:
            button = await page.query_selector("input[value='I am not a robot']")
            if button:
                print("  [AUTH] Handling robot check...")
                await page.evaluate("reauth()")
                await page.wait_for_load_state("domcontentloaded")
                await asyncio.sleep(1)
                return True
        except Exception as e:
            print(f"  [AUTH] Robot check failed: {e}")
        return False

    async def handle_age_gate(self, page):
        try:
            yes_button = await page.query_selector("#age-button-yes")
            if yes_button:
                print("  [AGE] Clicking age verification...")
                await yes_button.click()
                await asyncio.sleep(0.5)
                return True
        except Exception as e:
            print(f"  [AGE] Age gate handling failed: {e}")
        return False

    async def navigate_with_auth(self, page, url):
        response = await page.goto(url, wait_until="domcontentloaded")
        if response and response.status == 404:
            return response

        robot_button = await page.query_selector("input[value='I am not a robot']")
        if robot_button:
            await self.handle_robot_check(page)
            response = await page.goto(url, wait_until="domcontentloaded")

        await self.handle_age_gate(page)

        return response

    async def is_valid_pdf(self, filepath):
        if not os.path.exists(filepath):
            return False
        if os.path.getsize(filepath) < self.min_pdf_size:
            return False
        with open(filepath, "rb") as f:
            header = f.read(5)
        return header == b"%PDF-"

    async def download_pdf(self, client, url, dataset_id):
        folder = os.path.join(self.base_folder, f"Dataset-{dataset_id}")
        os.makedirs(folder, exist_ok=True)
        filename = url.split("/")[-1].split("?")[0]
        filepath = os.path.join(folder, filename)

        if await self.is_valid_pdf(filepath):
            return filename

        try:
            response = await client.get(url, timeout=60.0)
            if response.status_code == 200:
                content = response.content

                if len(content) < self.min_pdf_size or not content.startswith(b"%PDF-"):
                    print(f"  [SKIP] {filename} — not a valid PDF ({len(content)} bytes)")
                    return None

                with open(filepath, "wb") as f:
                    f.write(content)
                print(f"  [SAVED] {filename} ({len(content)} bytes)")
                return filename
            else:
                print(f"  [HTTP {response.status_code}] {filename}")
        except Exception as e:
            print(f"  [ERROR] Failed {filename}: {e}")
        return None

    async def run(self):
        async with async_playwright() as p:
            browser, context = await self.setup_browser(p)
            page = await context.new_page()

            async with httpx.AsyncClient(headers=self.headers, follow_redirects=True) as client:
                for ds_id in range(0, 15):
                    print(f"\n[DATASET {ds_id}] Checking source...")
                    prev_page_pdfs = set()
                    page_num = 0

                    while True:
                        target_url = self.base_url.format(ds_id, page_num)
                        try:
                            response = await self.navigate_with_auth(page, target_url)
                            if response and response.status == 404:
                                break
                        except Exception as e:
                            print(f"  [NAV ERROR] {e}")
                            break

                        links = await page.query_selector_all("a[href*='.pdf']")
                        current_page_pdfs = []

                        for link in links:
                            href = await link.get_attribute("href")
                            if href:
                                full_url = href if href.startswith("http") else f"https://www.justice.gov{href}"
                                current_page_pdfs.append(full_url)

                        pdf_names = {u.split("/")[-1] for u in current_page_pdfs}

                        if not pdf_names or pdf_names == prev_page_pdfs:
                            break

                        cookies = await context.cookies()
                        cookie_header = "; ".join(f"{c['name']}={c['value']}" for c in cookies)
                        client.headers.update({"Cookie": cookie_header})

                        for pdf_url in current_page_pdfs:
                            await self.download_pdf(client, pdf_url, ds_id)

                        prev_page_pdfs = pdf_names
                        page_num += 1

            await browser.close()

if __name__ == "__main__":
    downloader = EpsteinDataDownloader()
    asyncio.run(downloader.run())