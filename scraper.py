import json
import requests
from bs4 import BeautifulSoup

runners = [
    {"name": "서형관", "bib": "6327"}, {"name": "한태호", "bib": "12635"},
    {"name": "손태민", "bib": "13661"}, {"name": "이재형", "bib": "1234"},
    {"name": "김민성", "bib": "6086"}, {"name": "이강훈", "bib": "7664"},
    {"name": "김민호", "bib": "3093"}, {"name": "박해정", "bib": "11025"},
    {"name": "강성원", "bib": "3009"}, {"name": "김영환", "bib": "6857"},
    {"name": "양승열", "bib": "6388"}, {"name": "전희경", "bib": "11424"},
    {"name": "최현식", "bib": "13318"}, {"name": "이성희", "bib": "17111"},
    {"name": "김영식", "bib": "4332"}, {"name": "김희정", "bib": "5006"},
    {"name": "이지훈", "bib": "7381"}, {"name": "최이현", "bib": "8036"},
    {"name": "하늘이", "bib": "14428"}, {"name": "정슬아", "bib": "14400"},
    {"name": "김병채", "bib": "15089"}, {"name": "이광은", "bib": "16089"}
]

updated_data = []

for r in runners:
    km = 0.0
    try:
        url = f"https://www.myresult.co.kr/176/{r['bib']}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=5)
        
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            # TODO: 마이리절트 실제 HTML 구조에 맞는 파싱 로직 추가 필요
            pass
    except Exception as e:
        pass

    updated_data.append({
        "name": r["name"],
        "bib": r["bib"],
        "km": km
    })

with open('data.json', 'w', encoding='utf-8') as f:
    json.dump(updated_data, f, ensure_ascii=False, indent=2)
