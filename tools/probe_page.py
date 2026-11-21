"""(임시) 게시판 글 첨부(hwpx)를 내려받아 본문 출력."""
import re, sys, zipfile, io
from playwright.sync_api import sync_playwright
URL, WANT = sys.argv[1], sys.argv[2].split(",")
def hwpx_text(data):
    z = zipfile.ZipFile(io.BytesIO(data)); t = ""
    for n in sorted(x for x in z.namelist() if x.startswith("Contents/section")):
        t += re.sub(r"<[^>]+>", " ", z.read(n).decode("utf8"))
    return " ".join(t.split())
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(accept_downloads=True)
    for no in WANT:
        try:
            pg.goto(URL, wait_until="networkidle", timeout=60000); pg.wait_for_timeout(1500)
            pg.query_selector(f"table tbody tr:has(td:text-is('{no}'))").query_selector("a").click()
            pg.wait_for_load_state("networkidle"); pg.wait_for_timeout(1000)
            link = [a for a in pg.query_selector_all("a") if re.search(r"\.hwpx", a.inner_text(), re.I)][0]
            with pg.expect_download(timeout=30000) as dl:
                link.click()
            data = open(dl.value.path(), "rb").read()
            t = hwpx_text(data)
            print("\n####", no, len(t)); print("TEXT", t[:5000])
        except Exception as e:
            print("ERR", no, e)
    b.close()
