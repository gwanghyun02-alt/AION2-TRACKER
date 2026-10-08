"""GitHub Actions 러너(데이터센터 IP)에서 각 소스 접속이 되는지 확인."""
import re
import time
import requests

UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/130.0 Safari/537.36')
MUA = ('Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 '
       '(KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1')
tests = [
    ('steam_reviews', 'https://store.steampowered.com/appreviews/3393110?json=1&language=all&purchase_type=all&num_per_page=0', UA, 'total_positive'),
    ('steam_forum', 'https://steamcommunity.com/app/3393110/discussions/1/', UA, 'forum_topic'),
    ('reddit_new_rss', 'https://www.reddit.com/r/Aion2/new/.rss?limit=5', UA, '<entry>'),
    ('reddit_comments_rss', 'https://www.reddit.com/r/Aion2/comments/.rss?limit=5', UA, '<entry>'),
    ('reddit_json', 'https://www.reddit.com/r/Aion2/new.json?limit=2', UA, '"kind"'),
    ('dc_pc_list', 'https://gall.dcinside.com/mgallery/board/lists/?id=aion2&list_num=100', UA, 'ub-content'),
    ('dc_mobile_list', 'https://m.dcinside.com/board/aion2', MUA, 'gall-detail-lst'),
    ('translate', 'https://translate.googleapis.com/translate_a/single?client=dict-chrome-ex&sl=auto&tl=ko&dt=t&q=hello', UA, '['),
]
ip = requests.get('https://api.ipify.org', timeout=10).text
print('runner ip', ip)
for name, url, ua, marker in tests:
    for attempt in range(2):
        try:
            r = requests.get(url, headers={'User-Agent': ua}, timeout=20)
            ok = r.status_code == 200 and marker in r.text
            print(f'{name:20} HTTP {r.status_code} bytes {len(r.content):7} marker {"OK" if ok else "MISSING"}'
                  + (f" ratelimit-remaining {r.headers.get('x-ratelimit-remaining')}" if 'reddit' in name else ''))
            if r.status_code == 429:
                time.sleep(float(r.headers.get('x-ratelimit-reset', 30)) + 2)
                continue
            break
        except Exception as e:
            print(f'{name:20} ERROR {type(e).__name__}: {str(e)[:120]}')
            break
    if 'reddit' in name:
        time.sleep(65)  # 비인증 RSS 쿨다운
# DC 글 페이지(모바일) 하나
m = requests.get('https://m.dcinside.com/board/aion2', headers={'User-Agent': MUA}, timeout=20).text
no = re.search(r'/board/aion2/(\d+)', m)
if no:
    r = requests.get(f'https://m.dcinside.com/board/aion2/{no.group(1)}', headers={'User-Agent': MUA}, timeout=20)
    print(f'{"dc_mobile_view":20} HTTP {r.status_code} bytes {len(r.content):7} comments {"OK" if "all-comment-lst" in r.text else "MISSING"}')
