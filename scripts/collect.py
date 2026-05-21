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
OC       = 'kyungsamko'
API_URL  = 'https://www.law.go.kr/DRF/lawSearch.do'
PER_PAGE = 100
DELAY    = 0.4   # 요청 간 대기 (초) — API 서버 부하 방지
OUTPUT   = Path(__file__).parent.parent / 'data' / 'ordinances.json'

# 광주: 구별 + 본청 개별 검색 (단일 쿼리는 API 결과 상한에 걸림)
GJ_QUERIES = [
    '광주광역시 동구',
    '광주광역시 서구',
    '광주광역시 남구',
    '광주광역시 북구',
    '광주광역시 광산구',
    '광주광역시교육청',
    '광주광역시',        # 본청 (구 이름 없는 조례 포함), seen으로 중복 제거
]

# 전남: 도청 본청 + 22개 시군 개별 검색
JN_QUERIES = [
    '전라남도',
    '목포시', '여수시', '순천시', '나주시', '광양시',
    '담양군', '곡성군', '구례군', '고흥군', '보성군',
    '화순군', '장흥군', '강진군', '해남군', '영암군',
    '무안군', '함평군', '영광군', '장성군', '완도군',
    '진도군', '신안군',
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
    }, timeout=15)
    resp.raise_for_status()
    return ET.fromstring(resp.content)


def clean_name(raw: str) -> str:
    return re.sub(r'^\d+[\.\)\-\s]+', '', (raw or '').strip()).strip()


def collect(queries: list, region_filter, label: str) -> list:
    items = []
    seen  = set()

    for query in queries:
        page  = 1
        total = None

        while True:
            try:
                xml = fetch_page(query, page)
            except Exception as e:
                print(f'\n  [{query}] p{page} 오류: {e}', flush=True)
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
