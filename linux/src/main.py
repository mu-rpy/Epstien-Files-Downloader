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

    async def setup_browser(self, p):
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent=self.headers["User-Agent"])
        return browser, context

    async def download_pdf(self, client, url, dataset_id):
        folder = os.path.join(self.base_folder, f"Dataset-{dataset_id}")
        os.makedirs(folder, exist_ok=True)
        filename = url.split("/")[-1].split("?")[0]
        filepath = os.path.join(folder, filename)
        
        if os.path.exists(filepath):
            return filename

        try:
            response = await client.get(url, timeout=60.0)
            if response.status_code == 200:
                with open(filepath, "wb") as f:
                    f.write(response.content)
                print(f"  [SAVED] {filename}")
                return filename
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
                            response = await page.goto(target_url, wait_until="domcontentloaded")
                            if response.status == 404:
                                break
                        except:
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
                        
                        for pdf_url in current_page_pdfs:
                            await self.download_pdf(client, pdf_url, ds_id)
                        
                        prev_page_pdfs = pdf_names
                        page_num += 1

            await browser.close()

if __name__ == "__main__":
    downloader = EpsteinDataDownloader()
    asyncio.run(downloader.run())