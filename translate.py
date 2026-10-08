# -*- coding: utf-8 -*-
"""외국어 글 → 한국어 번역 (Google 번역 공개 엔드포인트, 키 불필요).

화면에 보이는 것(검토 엑셀 항목, Top3 제목)만 번역하고 data/translations.json 에 캐시한다.
실패하면 빈 문자열을 돌려주고 수집은 그대로 진행한다 — 번역은 보조 정보다.
"""
import hashlib
import json
import os
import re
import threading
import time

import requests

BASE = os.path.dirname(os.path.abspath(__file__))
CACHE_P = os.path.join(BASE, 'data', 'translations.json')
CACHE_MAX = 20000
_lock = threading.Lock()
_cache = None
_last = 0.0


def _load():
    global _cache
    if _cache is None:
        try:
            _cache = json.load(open(CACHE_P, encoding='utf-8'))
        except Exception:  # noqa
            _cache = {}
    return _cache


def save():
    if _cache is None:
        return
    with _lock:
        items = list(_cache.items())[-CACHE_MAX:]
        tmp = CACHE_P + '.tmp'
        json.dump(dict(items), open(tmp, 'w', encoding='utf-8'), ensure_ascii=False)
        os.replace(tmp, CACHE_P)


def is_korean(text):
    t = re.sub(r'[\s\d\W_]+', '', text or '')
    if not t:
        return True
    return len(re.findall(r'[가-힣ㄱ-ㅎㅏ-ㅣ]', t)) / len(t) >= 0.3


def _key(text):
    return hashlib.md5(text.encode('utf-8')).hexdigest()


# 한 프로세스(한 회차)에서 번역에 쓰는 시간 상한. 절전에서 막 깨어나 네트워크가 불안정하면
# 재시도가 쌓여 회차 하나가 17분까지 늘어난 일이 있었다(2026-10-07 08:01). 번역은 보조 정보라 넘치면 건너뛴다.
BUDGET_SEC = 120
_CLIENTS = ['gtx', 'dict-chrome-ex']
_HDR = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                      '(KHTML, like Gecko) Chrome/130.0 Safari/537.36'}
_t0 = time.time()
_fails = 0


def to_ko(text, limit=1500):
    """한국어면 '' 반환(번역 불필요). 실패·시간 초과도 ''(캐시에 남기지 않아 다음 회차에 다시 시도)."""
    global _last, _fails
    text = (text or '').strip()[:limit]
    if not text or is_korean(text):
        return ''
    cache = _load()
    k = _key(text)
    if k in cache:
        return cache[k]
    if time.time() - _t0 > BUDGET_SEC or _fails >= 3:
        return ''
    # client=gtx 가 파이썬 요청에만 429('Sorry...')로 막힌 일이 있었다(2026-10-07, curl 은 정상).
    # 같은 엔드포인트의 client=dict-chrome-ex 는 열려 있어 막히면 그쪽으로 넘어간다.
    for attempt, client in enumerate(list(_CLIENTS)):
        gap = 0.6 - (time.time() - _last)
        if gap > 0:
            time.sleep(gap)
        _last = time.time()
        try:
            r = requests.get('https://translate.googleapis.com/translate_a/single', timeout=8, headers=_HDR,
                             params={'client': client, 'sl': 'auto', 'tl': 'ko', 'dt': 't', 'q': text})
            if r.status_code == 429 and attempt == 0:
                _CLIENTS.reverse()  # 이번 프로세스에서는 열린 쪽을 먼저 쓴다
                continue
            if r.status_code == 200:
                j = r.json()
                out = ''.join(seg[0] for seg in j[0] if seg and seg[0]).strip()
                if j[2] == 'ko' or out == text:  # 한국어이거나 번역할 게 없음(링크·숫자만)
                    out = ''
                with _lock:
                    cache[k] = out
                _fails = 0
                return out
        except Exception:  # noqa
            pass
        time.sleep(1)
    _fails += 1  # 연속 3건 실패하면 이 회차 번역 중단
    return ''
