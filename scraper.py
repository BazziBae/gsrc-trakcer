import json
import re
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

# 2026 춘천마라톤 고유 번호 176 고정
EVENT_ID = "176"

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

# 후보 URL 템플릿
URL_TEMPLATES = [
    "https://myresult.co.kr/api/event/{event_id}/player/{bib}",
    "https://www.myresult.co.kr/api/event/{event_id}/player/{bib}",
    "https://myresult.co.kr/{event_id}/{bib}"
]

def parse_point_name_to_km(name_str):
    """구간 명칭을 정확한 km 숫자로 변환 (5K가 15K/25K에 오탐되지 않도록 단어 경계 엄격 적용)"""
    if not name_str:
        return None
    s = str(name_str).upper().strip()

    if any(k in s for k in ["FINISH", "완주", "도착", "골인", "42.195"]):
        return 42.195
    if any(k in s for k in ["HALF", "하프", "21.0975"]):
        return 21.0975
    if any(k in s for k in ["START", "출발"]):
        return 0.1

    m = re.search(r'(?<![0-9.])(\d+(?:\.\d+)?)\s*(?:K|KM)\b', s)
    if m:
        val = float(m.group(1))
        if 0 < val <= 42.2:
            return val
    return None

def is_valid_time(val):
    """해당 구간에 실제 유효한 통과 시간(HH:MM:SS 또는 MM:SS)이 찍혔는지 검증"""
    if not val:
        return False
    s = str(val).strip()
    if s in ["", "-", "--", "00:00:00", "00:00", "0:00:00", "null", "None"]:
        return False
    if re.search(r'\b([0-9]{1,2}:[0-5][0-9](?::[0-5][0-9])?)\b', s):
        if not re.match(r'^0+:0+(?::0+)?$', s):
            return True
    return False

def extract_km_from_json(data):
    """JSON 구조를 직접 순회하며 구간(point)과 시간(time)이 쌍으로 존재하는 데이터만 안전하게 파싱"""
    max_km = 0.0

    def traverse(obj):
        nonlocal max_km
        if isinstance(obj, dict):
            point_candidate = (
                obj.get("point") or obj.get("pointName") or obj.get("section") or 
                obj.get("name") or obj.get("title") or obj.get("km") or obj.get("distance")
            )
            time_candidate = (
                obj.get("time") or obj.get("netTime") or obj.get("passTime") or 
                obj.get("record") or obj.get("chipTime") or obj.get("clockTime")
            )

            if point_candidate is not None and time_candidate is not None:
                km = parse_point_name_to_km(point_candidate)
                if km is not None and is_valid_time(time_candidate):
                    max_km = max(max_km, km)

            for k, v in obj.items():
                if isinstance(v, (str, int, float)):
                    km = parse_point_name_to_km(k)
                    if km is not None and is_valid_time(v):
                        max_km = max(max_km, km)
                else:
                    traverse(v)

        elif isinstance(obj, list):
            for item in obj:
                traverse(item)

    traverse(data)
    return max_km

def find_working_template(sample_bib):
    """JSON 응답을 정상 반환하는 API 템플릿을 최우선으로 찾아 고정"""
    headers = {'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json, text/plain, */*'}
    fallback_tpl = URL_TEMPLATES[0]
    
    for tpl in URL_TEMPLATES:
        url = tpl.format(event_id=EVENT_ID, bib=sample_bib)
        try:
            res = requests.get(url, headers=headers, timeout=3)
            if res.status_code == 200:
                fallback_tpl = tpl
                # JSON 파싱이 가능한 진짜 API 엔드포인트면 즉시 채택
                try:
                    res.json()
                    return tpl
                except ValueError:
                    continue
        except Exception:
            continue
    return fallback_tpl

def fetch_single_runner(runner, template):
    """개별 선수 데이터 요청 (병렬 스레드에서 실행)"""
    bib = runner["bib"]
    headers = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)',
        'Accept': 'application/json, text/plain, */*',
        'Referer': f'https://myresult.co.kr/{EVENT_ID}/{bib}'
    }
    url = template.format(event_id=EVENT_ID, bib=bib)

    try:
        res = requests.get(url, headers=headers, timeout=3.5)
        if res.status_code != 200:
            return bib, None

        # 1순위: JSON 응답 직접 파싱
        try:
            data = res.json()
            km = extract_km_from_json(data)
            return bib, km
        except ValueError:
            pass

        # 2순위: HTML 응답일 경우 Next.js/SPA 내장 JSON(__NEXT_DATA__) 추출
        text = res.text
        json_matches = re.findall(r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>', text, re.DOTALL)
        for jm in json_matches:
            try:
                data = json.loads(jm)
                km = extract_km_from_json(data)
                return bib, km
            except Exception:
                pass

        return bib, 0.0
    except Exception:
        return bib, None

def main():
    prev_map = {}
    try:
        with open('data.json', 'r', encoding='utf-8') as f:
            for item in json.load(f):
                prev_map[item['bib']] = float(item.get('km', 0.0))
    except Exception:
        pass

    working_tpl = find_working_template(runners[0]["bib"])

    results = {}
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_bib = {
            executor.submit(fetch_single_runner, r, working_tpl): r["bib"]
            for r in runners
        }
        for future in as_completed(future_to_bib):
            bib = future_to_bib[future]
            try:
                _, km_val = future.result()
                results[bib] = km_val
            except Exception:
                results[bib] = None

    updated_data = []
    for r in runners:
        bib = r["bib"]
        fetched_km = results.get(bib)
        old_km = prev_map.get(bib, 0.0)

        if fetched_km is None:
            final_km = old_km
        else:
            final_km = max(fetched_km, old_km)

        updated_data.append({
            "name": r["name"],
            "bib": bib,
            "km": round(final_km, 2)
        })

    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(updated_data, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
