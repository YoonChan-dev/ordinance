#!/usr/bin/env python3
"""
광주광역시·전라남도 조례 목록 수집 스크립트
법제처 Open API → data/ordinances.json

사용법:
    pip install requests
    python3 scripts/collect.py
"""

import json
import re
import time
from datetime import date
from pathlib import Path
from xml.etree import ElementTree as ET

import requests

# ── 설정 ──────────────────────────────────────────
OC          = 'kyungsamko'
API_URL     = 'https://www.law.go.kr/DRF/lawSearch.do'
PER_PAGE    = 100
DELAY       = 1.0   # 요청 간 대기 (초) — 서버 부하 및 rate limit 방지
MAX_RETRIES = 3     # 페이지 실패 시 재시도 횟수
OUTPUT      = Path(__file__).parent.parent / 'data' / 'ordinances.json'

# 광주: '광주광역시' 먼저 실행(seen 비어 있을 때 최대 수집) → 구별 쿼리로 누락분 보완
GJ_QUERIES = [
    '광주광역시',        # 본청 + 전 구 포함 (가장 광범위, 첫 번째 실행)
    '광주광역시 동구',
    '광주광역시 서구',
    '광주광역시 남구',
    '광주광역시 북구',
    '광주광역시 광산구',
    '광주광역시교육청',
]

# 전남: '전라남도 XX' 형태로 통일 (단순 시군명은 API 결과가 100건으로 잘림)
JN_QUERIES = [
    '전라남도',
    '전라남도 목포시', '전라남도 여수시', '전라남도 순천시', '전라남도 나주시', '전라남도 광양시',
    '전라남도 담양군', '전라남도 곡성군', '전라남도 구례군', '전라남도 고흥군', '전라남도 보성군',
    '전라남도 화순군', '전라남도 장흥군', '전라남도 강진군', '전라남도 해남군', '전라남도 영암군',
    '전라남도 무안군', '전라남도 함평군', '전라남도 영광군', '전라남도 장성군', '전라남도 완도군',
    '전라남도 진도군', '전라남도 신안군',
    '전라남도교육청',
]
# ──────────────────────────────────────────────────


def fetch_page(query: str, page: int) -> ET.Element:
    resp = requests.get(API_URL, params={
        'OC':      OC,
        'target':  'ordin',
        'type':    'XML',
        'query':   query,
        'display': PER_PAGE,
        'page':    page,
    }, timeout=20)
    resp.raise_for_status()
    return ET.fromstring(resp.content)


def fetch_page_with_retry(query: str, page: int) -> ET.Element | None:
    for attempt in range(MAX_RETRIES):
        try:
            return fetch_page(query, page)
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                print(f'\n  [{query}] p{page} 오류 (재시도 {attempt+1}/{MAX_RETRIES-1}): {e}', flush=True)
                time.sleep(2)
            else:
                print(f'\n  [{query}] p{page} 오류 ({MAX_RETRIES}회 모두 실패): {e}', flush=True)
    return None


def clean_name(raw: str) -> str:
    return re.sub(r'^\d+[\.\)\-\s]+', '', (raw or '').strip()).strip()


def collect(queries: list, region_filter, label: str) -> list:
    items = []
    seen  = set()

    for query in queries:
        page  = 1
        total = None

        while True:
            xml = fetch_page_with_retry(query, page)
            if xml is None:
                break

            if page == 1:
                total = int(xml.findtext('totalCnt') or 0)
                print(f'  [{query}] {total}건', flush=True)
                if total == 0:
                    break

            for law in xml.findall('law'):
                mst = (law.findtext('자치법규일련번호') or '').strip()
                if mst in seen:
                    continue

                org = (law.findtext('지자체기관명') or '').strip()
                if not region_filter(org):
                    continue

                name = clean_name(law.findtext('자치법규명') or '')
                if not name:
                    continue

                seen.add(mst)
                items.append({
                    'name':  name,
                    'id':    (law.findtext('자치법규ID')    or '').strip(),
                    'mst':   mst,
                    'type':  (law.findtext('자치법규종류')  or '조례').strip(),
                    'org':   org,
                    'prom':  (law.findtext('공포일자')      or '').strip(),  # YYYYMMDD
                    'dept':  (law.findtext('소관부서명')    or '').strip(),
                    'amend': (law.findtext('제개정구분명')  or '').strip(),
                })

            if page * PER_PAGE >= total:
                break

            page += 1
            time.sleep(DELAY)

    print(f'  → {label} 합계: {len(items)}건\n', flush=True)
    return items


def main():
    print('=' * 50)
    print(' 광주광역시·전라남도 조례 수집')
    print('=' * 50)

    print('\n▶ 광주광역시')
    gj = collect(GJ_QUERIES, lambda org: '광주광역시' in org, '광주광역시')

    print('▶ 전라남도')
    jn = collect(JN_QUERIES, lambda org: '전라남도' in org, '전라남도')

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps({'updated': date.today().isoformat(), 'gj': gj, 'jn': jn},
                   ensure_ascii=False, indent=2),
        encoding='utf-8',
    )

    size_kb = OUTPUT.stat().st_size / 1024
    print(f'저장 완료: {OUTPUT}')
    print(f'  광주광역시: {len(gj):,}건')
    print(f'  전라남도:   {len(jn):,}건')
    print(f'  파일 크기:  {size_kb:.0f} KB')


if __name__ == '__main__':
    main()
