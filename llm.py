# -*- coding: utf-8 -*-
"""Claude 로 반응 분류 (사용자 라벨·판단 이유를 지침과 예시로 사용).

- 시스템 프롬프트 = 판단 지침 + 사용자 라벨 예시(이유 포함). 라벨이 바뀔 때만 달라지므로 프롬프트 캐시로 재사용.
- 한 요청에 최대 BATCH 건, 출력은 [번호, 라벨, 확신도] 만 (출력 토큰이 비용의 큰 몫이라 최소화).
- 실패하면 None 을 돌려주고 호출부는 사전 분류로 대체한다. 사용량·비용은 data/llm_usage.jsonl 에 남긴다.
"""
import json
import os
import random
import threading
import time
from datetime import datetime, timedelta, timezone

BASE = os.path.dirname(os.path.abspath(__file__))
USAGE_P = os.path.join(BASE, 'data', 'llm_usage.jsonl')
KST = timezone(timedelta(hours=9))
MODEL = 'claude-sonnet-5'
PRICE = {'claude-sonnet-5': (2.0, 10.0), 'claude-haiku-4-5': (1.0, 5.0)}  # $/1M 입력·출력 (캐시 읽기 0.1x, 쓰기 1.25x)
BATCH = 40
MAX_EXAMPLES = 160
TEXT_CHARS = 500
_LAB = {'P': '긍정', 'U': '중립', 'N': '부정'}
_lock = threading.Lock()

GUIDE = """당신은 게임 커뮤니티(DC인사이드 갤러리, Reddit, Steam 토론) 글과 댓글이 **이 게임({game})에 대해** 어떤 반응인지 분류합니다.
분류 기준은 이 프로젝트 담당자가 직접 라벨을 달며 정한 기준이며, 아래 예시가 그 기준의 1차 자료입니다. 예시와 같은 방식으로 판단하세요.

라벨
- P(긍정): 게임·업데이트·운영·BM에 대한 호평, 기대, 재미, 옹호(예: "과금 그렇게 비싸지 않다", "다른 게임보다 낫다"), 흥행에 대한 긍정적 전망.
- N(부정): 게임·운영사·BM·최적화·서버·콘텐츠·밸런스에 대한 비판이나 불만, 이탈 예고, 흥행 부정 전망, 그리고 **비꼼·조롱**(예: "What story?", "Is this your first time playing NCSoft products?", "기술력의 NC 감탄만 나옵니다").
  '모바일 게임 같다/PC 이식이 나쁘다', '숙제·반복이 피곤하다', '스토리가 부실하다', '돈 우선 운영'도 부정입니다.
- U(중립): 게임에 대한 호불호가 드러나지 않는 글 — 질문, 정보 공유, 공략·해결 팁, 단순 잡담, 게임과 무관한 이야기,
  **유저끼리의 다툼·욕설**(게임 평가가 아니면 욕이 섞여도 중립), 과거 버그가 있었는지 묻는 질문 등.

주의
- 욕설·비속어 자체는 판단 근거가 아닙니다. 무엇을 향한 감정인지 보세요.
- 댓글은 함께 주어지는 게시글 제목을 맥락으로 쓰되, 판단 대상은 댓글 자체입니다.
- 영어·독일어 등 외국어도 같은 기준입니다.
- 확신도 c: h(분명함) / m(어느 정도) / l(애매함 — 사람이 다시 보면 좋겠음).

출력: 입력의 모든 항목에 대해 {{"i": 번호, "l": "P"|"U"|"N", "c": "h"|"m"|"l"}} 를 results 배열로."""

SCHEMA = {
    'type': 'object',
    'properties': {
        'results': {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'i': {'type': 'integer'},
                    'l': {'type': 'string', 'enum': ['P', 'U', 'N']},
                    'c': {'type': 'string', 'enum': ['h', 'm', 'l']},
                },
                'required': ['i', 'l', 'c'],
                'additionalProperties': False,
            },
        },
    },
    'required': ['results'],
    'additionalProperties': False,
}


KEY_FILE = os.path.join(os.path.expanduser('~'), '.config', 'anthropic', 'api_key.txt')  # OneDrive 밖(동기화 안 됨)


def api_key():
    """환경변수 → 키 파일 순. 'your-api-key' 같은 자리표시 값은 무시한다(이 PC 사용자 환경변수에 실제로 들어 있었음)."""
    k = (os.environ.get('ANTHROPIC_API_KEY') or '').strip()
    if k.startswith('sk-ant-'):
        return k
    try:
        k = open(KEY_FILE, encoding='utf-8').read().strip()
        return k if k.startswith('sk-ant-') else None
    except OSError:
        return None


def _client():
    import anthropic
    k = api_key()
    if not k:
        raise RuntimeError(f'Anthropic API 키 없음 — {KEY_FILE} 에 sk-ant-… 키를 넣으세요')
    return anthropic.Anthropic(api_key=k, max_retries=3, timeout=120.0)


# ---------------------------------------------------------------- 구독(Claude Code CLI) 경로
# API 키 없이 사용자의 Claude 구독(Pro)으로 분류한다. 구독 사용 한도를 대화형 사용과 함께 쓰므로
# 호출마다 붙는 Claude Code 기본 지침(~3.7만 토큰)을 --system-prompt-file 로 바꿔치고 도구·MCP 를 꺼서
# ~1.8천 토큰으로 줄이고(2026-10-07 실측), 한 번에 많이 묶어 보낸다.
# --bare 는 API 키 인증만 받아서 못 쓴다. 사용자 환경변수 ANTHROPIC_API_KEY 에 자리표시 값이 있어
# 그대로 두면 구독 로그인 대신 그 값이 잡히므로 하위 프로세스 환경에서 뺀다.
CLI_BATCH = 80


def claude_cli():
    import glob
    import shutil
    p = shutil.which('claude')
    if p:
        return p
    found = sorted(glob.glob(os.path.join(os.path.expanduser('~'), '.vscode', 'extensions',
                                          'anthropic.claude-code-*', 'resources', 'native-binary', 'claude.exe')))
    return found[-1] if found else None  # 확장이 업데이트되면 버전 폴더가 바뀌므로 매번 최신을 찾는다


def _call_cli(exe, system_text, batch, model_alias, tag):
    import subprocess
    import tempfile
    payload = [{'i': k, 'src': it.get('src'), 'kind': it.get('kind'),
                'title': (it.get('title') or '')[:120] if it.get('kind') == '댓글' else None,
                'text': (it.get('text') or '')[:TEXT_CHARS]} for k, it in enumerate(batch)]
    env = {k: v for k, v in os.environ.items() if k not in ('ANTHROPIC_API_KEY', 'ANTHROPIC_AUTH_TOKEN')}
    with tempfile.TemporaryDirectory() as td:  # 빈 작업 폴더: 프로젝트 CLAUDE.md 등을 읽지 않게
        sp = os.path.join(td, 'system.txt')
        with open(sp, 'w', encoding='utf-8') as f:
            f.write(system_text)
        cmd = [exe, '-p', 'stdin 으로 받은 JSON 배열의 모든 항목을 지침대로 분류해 results 로 답하라.',
               '--model', model_alias, '--system-prompt-file', sp, '--tools', '',
               '--strict-mcp-config', '--mcp-config', '{"mcpServers":{}}', '--no-session-persistence',
               '--json-schema', json.dumps(SCHEMA), '--output-format', 'json']
        r = subprocess.run(cmd, input=json.dumps(payload, ensure_ascii=False), capture_output=True,
                           text=True, encoding='utf-8', cwd=td, env=env, timeout=600,
                           creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    if r.returncode != 0 and not r.stdout.strip():
        raise RuntimeError(f'claude CLI 실패 rc={r.returncode}: {r.stderr[:300]}')
    d = json.loads(r.stdout)
    if d.get('is_error'):
        raise RuntimeError(f"claude CLI 오류: {str(d.get('result'))[:300]}")  # 사용 한도 초과 등
    data = (d.get('structured_output') or json.loads(d['result']))['results']
    u = d.get('usage', {})
    _log_usage({'ts': datetime.now(KST).strftime('%Y-%m-%dT%H:%M:%S'), 'tag': tag, 'backend': 'subscription',
                'model': ','.join(d.get('modelUsage', {}).keys()) or model_alias, 'n': len(batch),
                'in': u.get('input_tokens', 0), 'out': u.get('output_tokens', 0),
                'cache_read': u.get('cache_read_input_tokens', 0), 'cache_write': u.get('cache_creation_input_tokens', 0),
                'usd': 0.0, 'notional_usd': round(d.get('total_cost_usd', 0), 5)})
    return {r_['i']: (_LAB[r_['l']], r_['c']) for r_ in data if 0 <= r_['i'] < len(batch)}


def build_system(game, examples):
    """examples: [{'text','label','reason','reason_type','src','title'}] — 라벨이 같으면 결과도 같다(캐시 유지)."""
    code = {'긍정': 'P', '중립': 'U', '부정': 'N'}
    ex = sorted(examples, key=lambda r: str(r.get('id')))
    # 이유를 적은 예시를 우선, 그다음 라벨 균형
    with_reason = [r for r in ex if r.get('reason') or r.get('reason_type')]
    rest = [r for r in ex if r not in with_reason]
    picked = (with_reason + rest)[:MAX_EXAMPLES]
    lines = []
    for r in picked:
        why = ' / '.join(x for x in (r.get('reason_type'), r.get('reason')) if x)
        title = f" [제목: {r['title'][:80]}]" if r.get('title') and r.get('title') != (r.get('text') or '')[:len(r['title'])] else ''
        lines.append(f"- ({r.get('src') or ''}){title} \"{(r.get('text') or '')[:300]}\" → {code[r['label']]}"
                     + (f"  // 이유: {why[:160]}" if why else ''))
    return [
        {'type': 'text', 'text': GUIDE.format(game=game)},
        {'type': 'text', 'text': '담당자 라벨 예시\n' + '\n'.join(lines), 'cache_control': {'type': 'ephemeral'}},
    ]


def _cost(model, u):
    pin, pout = PRICE.get(model, (2.0, 10.0))
    cr = getattr(u, 'cache_read_input_tokens', 0) or 0
    cw = getattr(u, 'cache_creation_input_tokens', 0) or 0
    return (u.input_tokens * pin + cr * pin * 0.1 + cw * pin * 1.25 + u.output_tokens * pout) / 1e6


def _log_usage(rec):
    with _lock:
        os.makedirs(os.path.dirname(USAGE_P), exist_ok=True)
        with open(USAGE_P, 'a', encoding='utf-8') as f:
            f.write(json.dumps(rec, ensure_ascii=False) + '\n')


def _call(client, system, batch, model, tag):
    payload = [{'i': k, 'src': it.get('src'), 'kind': it.get('kind'),
                'title': (it.get('title') or '')[:120] if it.get('kind') == '댓글' else None,
                'text': (it.get('text') or '')[:TEXT_CHARS]} for k, it in enumerate(batch)]
    resp = client.messages.create(
        model=model,
        max_tokens=4000,
        thinking={'type': 'disabled'},
        system=system,
        messages=[{'role': 'user', 'content': '다음 항목을 분류하세요.\n' + json.dumps(payload, ensure_ascii=False)}],
        output_config={'format': {'type': 'json_schema', 'schema': SCHEMA}},
    )
    text = next(b.text for b in resp.content if b.type == 'text')
    data = json.loads(text)['results']
    u = resp.usage
    _log_usage({'ts': datetime.now(KST).strftime('%Y-%m-%dT%H:%M:%S'), 'tag': tag, 'model': model, 'n': len(batch),
                'in': u.input_tokens, 'out': u.output_tokens,
                'cache_read': getattr(u, 'cache_read_input_tokens', 0) or 0,
                'cache_write': getattr(u, 'cache_creation_input_tokens', 0) or 0,
                'usd': round(_cost(model, u), 5)})
    out = {}
    for r in data:
        if 0 <= r['i'] < len(batch):
            out[r['i']] = (_LAB[r['l']], r['c'])
    return out


def classify_items(items, game, examples, model=MODEL, tag='run', workers=4, allow_api=True):
    """items 리스트(순서 유지)에 대해 [(label, conf) | None] 반환. 일부 배치가 실패하면 그 항목만 None."""
    if not items:
        return [], []
    system = build_system(game, examples)
    # 구독(Claude Code CLI) 우선 → 실패(사용 한도 소진 등)가 연속 2번이면 이 회차 남은 분량은 API 키로.
    # API 도 실패하면(크레딧 부족 등) 그 항목은 None → 호출부가 사전 분류로 대체.
    exe = claude_cli()
    text = '\n\n'.join(block['text'] for block in system)
    alias = 'sonnet' if 'sonnet' in model else 'haiku' if 'haiku' in model else model
    state = {'cli_fail': 0 if exe else 99, 'api': None}

    def call(b):
        if state['cli_fail'] < 2:
            try:
                out = _call_cli(exe, text, b, alias, tag)
                state['cli_fail'] = 0
                return out
            except Exception as e:  # noqa
                state['cli_fail'] += 1
                errors.append(f'구독 경로 실패: {str(e)[:160]}')
        if not allow_api or not api_key():
            raise RuntimeError('구독 경로 실패, API 키 없음')
        if state['api'] is None:
            state['api'] = _client()
        if within_api_budget() is False:
            raise RuntimeError(f'API 일일 예산(${API_DAILY_BUDGET}) 초과')
        return _call(state['api'], system, b, model, tag + ':api')

    size = CLI_BATCH if exe else BATCH
    batches = [items[i:i + size] for i in range(0, len(items), size)]
    results = [None] * len(items)
    errors = []

    def run(bi):
        b = batches[bi]
        for attempt in range(2):
            try:
                got = call(b)
                for k, v in got.items():
                    results[bi * size + k] = v
                return
            except Exception as e:  # noqa
                errors.append(f'{type(e).__name__}: {str(e)[:200]}')
                time.sleep(5 * (attempt + 1))

    # 첫 배치로 프롬프트 캐시를 만든 뒤 나머지를 병렬로(동시 요청이 각자 캐시를 쓰는 낭비 방지)
    run(0)
    threads = []
    for bi in range(1, len(batches)):
        t = threading.Thread(target=run, args=(bi,))
        threads.append(t)
        t.start()
        if len(threads) >= workers:
            threads.pop(0).join()
    for t in threads:
        t.join()
    return results, errors


API_DAILY_BUDGET = 10.0  # USD/일 — 구독 한도 소진 후 API 로 넘어갔을 때의 안전 상한 (config llm_api_daily_usd)


def within_api_budget():
    return usage_summary()['today_usd'] < API_DAILY_BUDGET


def usage_summary():
    """오늘·이번 달 사용액(USD)."""
    today = datetime.now(KST).strftime('%Y-%m-%d')
    month = today[:7]
    d = m = 0.0
    n_d = n_m = 0
    if os.path.exists(USAGE_P):
        for line in open(USAGE_P, encoding='utf-8'):
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if r['ts'].startswith(month):
                m += r['usd']
                n_m += r['n']
                if r['ts'].startswith(today):
                    d += r['usd']
                    n_d += r['n']
    return {'today_usd': round(d, 3), 'month_usd': round(m, 2), 'today_items': n_d, 'month_items': n_m}


# ---------------------------------------------------------------- 사전 vs AI 조합 (자동 재시험용)
# 라벨이 100건 늘 때마다 tracker 가 evaluate() 를 돌려, 가장 좋은 조합이 '사전 + 5%p' 를 넘으면 그 조합으로 켠다.
VARIANTS = {
    'ai_only': 'AI만',
    'h_only': 'AI가 분명함(h)일 때만 AI',
    'hm': 'AI가 h·m 일 때 AI',
    'neutral_hm': '사전이 중립이면 AI(h·m)',
    'neutral_h': '사전이 중립이면 AI(h)',
}
MARGIN = 5.0  # %p


def combine(variant, lex, ai, conf):
    """사전 라벨 lex 와 AI (ai, conf) 를 조합 규칙대로 합친다. AI 결과가 없으면 사전."""
    if not ai:
        return lex
    if variant == 'ai_only':
        return ai
    if variant == 'h_only':
        return ai if conf == 'h' else lex
    if variant == 'hm':
        return ai if conf in ('h', 'm') else lex
    if variant == 'neutral_hm':
        return ai if lex == '중립' and conf in ('h', 'm') else lex
    if variant == 'neutral_h':
        return ai if lex == '중립' and conf == 'h' else lex
    return lex


def evaluate(rows, game, lex_fn, k=5, model=MODEL):
    """rows: 라벨 행(text,label,title,kind,src,reason…). 예시와 채점 라벨이 겹치지 않게 k-fold.
    구독 경로만 쓴다(시험에 API 크레딧을 쓰지 않음). 반환: 정확도표·최고 조합·통과 여부."""
    rows = sorted(rows, key=lambda r: str(r.get('id')))
    preds, errors = [], []
    for f in range(k):
        test = rows[f::k]
        train = [r for i, r in enumerate(rows) if i % k != f]
        res, errs = classify_items(test, game, train, model=model, tag='auto-eval', workers=2, allow_api=False)
        errors += errs
        for r, got in zip(test, res):
            preds.append((r['label'], lex_fn(r['text']), got[0] if got else None, got[1] if got else None))
    failed = sum(1 for p in preds if p[2] is None)
    if failed > len(preds) * 0.1:  # 한도 소진 등으로 10% 넘게 실패하면 이번 시험은 무효
        return {'ok': False, 'n': len(rows), 'failed': failed, 'errors': errors[:3]}
    acc = lambda fn: round(sum(1 for g, l, a, c in preds if fn(l, a, c) == g) / len(preds) * 100, 1)  # noqa
    lexicon = acc(lambda l, a, c: l)
    scores = {v: acc(lambda l, a, c, v=v: combine(v, l, a, c)) for v in VARIANTS}
    best = max(scores, key=scores.get)
    return {'ok': True, 'n': len(rows), 'lexicon': lexicon, 'scores': scores, 'best': best,
            'best_score': scores[best], 'threshold': round(lexicon + MARGIN, 1),
            'passed': scores[best] >= lexicon + MARGIN, 'failed': failed}


# ---------------------------------------------------------------- 게임 맥락 번역 (2026-10-09)
# Google 번역은 게임 용어를 일반 단어로 옮겼다(Gladiator→검투사, Cosmetics→화장품, abyss→심연, power→전력).
# 화면에 보이는 외국어(Top3 제목·검토 엑셀)만 Claude 로 게임 맥락 번역한다. 구독 → API → (호출부) Google 순.
TR_SCHEMA = {
    'type': 'object',
    'properties': {'results': {'type': 'array', 'items': {
        'type': 'object', 'properties': {'i': {'type': 'integer'}, 'ko': {'type': 'string'}},
        'required': ['i', 'ko'], 'additionalProperties': False}}},
    'required': ['results'], 'additionalProperties': False,
}
TR_BATCH = 60


def _tr_system(game, glossary, note):
    gl = '\n'.join(f'- {k} → {v}' for k, v in (glossary or {}).items())
    return f"""당신은 MMORPG '{game}'의 해외 커뮤니티(Reddit, Steam 토론) 글을 한국 게이머가 읽기 자연스러운 한국어로 번역합니다.
모든 글은 이 게임에 관한 글입니다. 일반 사전 뜻이 아니라 게임 맥락의 뜻으로 옮기세요.

규칙
- 아래 용어집의 표현은 반드시 용어집대로 옮깁니다(대소문자·복수형 무관).
- 게이머 은어는 한국 게이머가 쓰는 표현으로 옮깁니다(예: grind→파밍/노가다, nerf→너프, carry→캐리, gatekeep→진입장벽).
- 비꼼·조롱·욕설의 뉘앙스와 어조를 살립니다. 순화하거나 설명을 덧붙이지 않습니다.
- {note or '확실하지 않은 고유명사는 원문을 괄호로 병기합니다.'}
- 숫자·단위는 한국식으로(80k → 8만). 오타(bouton 등)는 뜻대로 옮깁니다.
- 번역문만 출력합니다.

용어집
{gl}"""


def translate_items(texts, game, glossary=None, note=None, tag='translate'):
    """texts(list[str]) → list[str|None]. 실패한 항목은 None(호출부가 Google 로 대체)."""
    if not texts:
        return []
    import subprocess
    import tempfile
    system = _tr_system(game, glossary, note)
    exe = claude_cli()
    out = [None] * len(texts)
    state = {'cli_fail': 0 if exe else 99}
    env = {k: v for k, v in os.environ.items() if k not in ('ANTHROPIC_API_KEY', 'ANTHROPIC_AUTH_TOKEN')}

    def via_cli(batch):
        payload = [{'i': k, 'text': t[:TEXT_CHARS]} for k, t in enumerate(batch)]
        with tempfile.TemporaryDirectory() as td:
            sp = os.path.join(td, 'system.txt')
            open(sp, 'w', encoding='utf-8').write(system)
            r = subprocess.run([exe, '-p', 'stdin 의 JSON 배열 각 항목 text 를 지침대로 번역해 results 로 답하라.',
                                '--model', 'sonnet', '--system-prompt-file', sp, '--tools', '', '--strict-mcp-config',
                                '--mcp-config', '{"mcpServers":{}}', '--no-session-persistence',
                                '--json-schema', json.dumps(TR_SCHEMA), '--output-format', 'json'],
                               input=json.dumps(payload, ensure_ascii=False), capture_output=True, text=True,
                               encoding='utf-8', cwd=td, env=env, timeout=600,
                               creationflags=getattr(__import__('subprocess'), 'CREATE_NO_WINDOW', 0))
        d = json.loads(r.stdout)
        if d.get('is_error'):
            raise RuntimeError(str(d.get('result'))[:200])
        u = d.get('usage', {})
        _log_usage({'ts': datetime.now(KST).strftime('%Y-%m-%dT%H:%M:%S'), 'tag': tag, 'backend': 'subscription',
                    'model': ','.join(d.get('modelUsage', {}).keys()), 'n': len(batch),
                    'in': u.get('input_tokens', 0), 'out': u.get('output_tokens', 0),
                    'cache_read': u.get('cache_read_input_tokens', 0), 'cache_write': u.get('cache_creation_input_tokens', 0),
                    'usd': 0.0, 'notional_usd': round(d.get('total_cost_usd', 0), 5)})
        return (d.get('structured_output') or json.loads(d['result']))['results']

    def via_api(batch):
        if not api_key() or within_api_budget() is False:
            raise RuntimeError('API 사용 불가(키 없음 또는 일일 예산 초과)')
        client = _client()
        payload = [{'i': k, 'text': t[:TEXT_CHARS]} for k, t in enumerate(batch)]
        resp = client.messages.create(model=MODEL, max_tokens=8000, thinking={'type': 'disabled'},
                                      system=[{'type': 'text', 'text': system, 'cache_control': {'type': 'ephemeral'}}],
                                      messages=[{'role': 'user', 'content': '다음 항목을 번역하세요.\n' + json.dumps(payload, ensure_ascii=False)}],
                                      output_config={'format': {'type': 'json_schema', 'schema': TR_SCHEMA}})
        u = resp.usage
        _log_usage({'ts': datetime.now(KST).strftime('%Y-%m-%dT%H:%M:%S'), 'tag': tag + ':api', 'model': MODEL, 'n': len(batch),
                    'in': u.input_tokens, 'out': u.output_tokens, 'cache_read': getattr(u, 'cache_read_input_tokens', 0) or 0,
                    'cache_write': getattr(u, 'cache_creation_input_tokens', 0) or 0, 'usd': round(_cost(MODEL, u), 5)})
        return json.loads(next(b.text for b in resp.content if b.type == 'text'))['results']

    for s0 in range(0, len(texts), TR_BATCH):
        batch = texts[s0:s0 + TR_BATCH]
        res = None
        if state['cli_fail'] < 2:
            try:
                res = via_cli(batch)
                state['cli_fail'] = 0
            except Exception:  # noqa
                state['cli_fail'] += 1
        if res is None:
            try:
                res = via_api(batch)
            except Exception:  # noqa
                res = []
        for r in res:
            if 0 <= r['i'] < len(batch) and r.get('ko', '').strip():
                out[s0 + r['i']] = r['ko'].strip()
    return out
