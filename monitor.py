import re
import sys
import json
from urllib.parse import urljoin

import requests

LIST_URL = "https://job.koica.go.kr/application/applicationListPage.do?menuId=MENU0098"

# 찾고 싶은 키워드들 (원하면 더 추가 가능)
KEYWORDS = ["모집", "자동차", "전문가", "스리랑카", "직업훈련원"]

def fetch_html(url: str) -> str:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    }
    r = requests.get(url, headers=headers, timeout=30, verify=False)
    r.raise_for_status()
    return r.text

def extract_posts(html: str):
    """
    KOICA 커리어센터는 상세페이지가 보통
    applicationDetailPage.do?empmnPblancSn=숫자
    형태로 들어가므로, 그 링크를 찾아 제목을 같이 뽑아보는 방식.
    HTML 구조가 바뀌어도 최대한 버티도록 '정규식 기반'으로 단순하게 간다.
    """
    # 상세 페이지 링크의 empmnPblancSn만 우선 찾기
    sns = sorted(set(re.findall(r"empmnPblancSn=(\d+)", html)), reverse=True)

    posts = []
    for sn in sns[:80]:  # 최근 80개 정도만 훑기 (너무 많이 돌 필요 없음)
        detail = f"https://job.koica.go.kr/application/applicationDetailPage.do?empmnPblancSn={sn}&entrpsSn=&menuId=MENU0098&pageIndex=1"
        posts.append({"sn": sn, "url": detail})
    return posts

def keyword_match(text: str) -> bool:
    t = text.lower()
    return any(k.lower() in t for k in KEYWORDS)

def load_seen(path="seen.json"):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return set(json.load(f))
    except FileNotFoundError:
        return set()

def save_seen(seen_set, path="seen.json"):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(sorted(seen_set), f, ensure_ascii=False, indent=2)

def main():
    html = fetch_html(LIST_URL)
    posts = extract_posts(html)

    seen = load_seen()
    new_matches = []

    # 상세 페이지를 열어서 키워드가 들어있는지 확인
    for p in posts[:30]:  # 처음엔 최근 30개만 확인 (트래픽/시간 절약)
        sn = p["sn"]
        if sn in seen:
            continue

        try:
            dhtml = fetch_html(p["url"])
        except Exception:
            # 일시적으로 튕기면 다음 실행 때 다시 시도
            continue

        # 페이지 전체에서 키워드 검사 (제목만 뽑는 것보다 단순하지만 잘 맞음)
        if keyword_match(dhtml):
            new_matches.append(p)

        seen.add(sn)

    # 저장
    save_seen(seen)

    # 새로 잡힌 매치가 있으면 issue로 올릴 markdown 생성
    if new_matches:
        lines = ["KOICA 채용 공고에서 키워드 매칭된 새 항목이 발견됨\n"]
        for m in new_matches:
            lines.append(f"- {m['url']}")
        with open("issue_body.md", "w", encoding="utf-8") as f:
            f.write("\n".join(lines).strip() + "\n")

        print("FOUND=1")
    else:
        print("FOUND=0")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
