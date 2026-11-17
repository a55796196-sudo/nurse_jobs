"""기관 채용 사이트를 실제 브라우저로 렌더링해서 근무조건이 읽히는지 확인 (디버그)."""
import re

from playwright.sync_api import sync_playwright

URLS = [
    "https://nhimc.recruiter.co.kr/career/jobs/121616",            # 상세 (recruiter 신형)
    "https://nhimc.recruiter.co.kr",                                # 첫 화면 → 공고 목록
    "https://nmc.recruiter.co.kr/app/jobnotice/view?systemKindCode=MRS2&jobnoticeSn=271576",  # 상세 (구형)
]
with sync_playwright() as p:
    b = p.chromium.launch()
    page = b.new_page()
    for url in URLS:
        try:
            page.goto(url, wait_until="networkidle", timeout=60000)
            page.wait_for_timeout(2000)
        except Exception as e:  # noqa: BLE001
            print("\n===", url, "실패", e)
            continue
        text = " ".join(page.inner_text("body").split())
        print(f"\n=== {url}\n제목: {page.title()} / 본문 {len(text)}자")
        for kw in ("보수", "연봉", "만원", "근무시간", "복리후생"):
            i = text.find(kw)
            print(f"[{kw}]", text[max(0, i - 100): i + 250] if i >= 0 else "없음")
        imgs = page.eval_on_selector_all("img", "els => els.map(e => [e.src, e.naturalWidth]).filter(x => x[1] > 400)")
        print("큰 이미지:", imgs[:5])
        frames = [f.url for f in page.frames][:5]
        print("프레임:", frames)
        links = page.eval_on_selector_all("a", "els => els.map(e => [e.innerText.trim().slice(0,60), e.href]).filter(x => /job|notice|공고/.test(x[1]+x[0]))")
        print("공고 링크:", links[:15])
    b.close()
