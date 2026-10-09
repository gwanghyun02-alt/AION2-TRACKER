# -*- coding: utf-8 -*-
"""게임 유저 반응 감성 분류기 (게임 공통).

1단계: 사전(lexicon) 점수 — 한국어 커뮤니티 은어 + 영어
2단계: 사용자가 라벨링한 엑셀로 학습한 나이브 베이즈(NB)를 사전 점수에 섞는다.
       라벨이 쌓일수록 NB 비중이 커진다(최대 200건에서 100%).

사전은 아래 POS/NEG 에 단어 한 줄 추가로 넓힐 수 있다. 가중치는 0.5~3.
긴 표현이 먼저 매칭되고, 매칭된 구간은 짧은 표현이 다시 잡지 않는다
(예: '재미없' 이 잡히면 그 안의 '재미' 는 무시).
"""
import math
import re
from collections import Counter

POS = {
    # 한국어
    '갓겜': 3, '갓게임': 3, '띵작': 3, '명작': 2.5, '꿀잼': 3, '존잼': 3, '개꿀잼': 3, '핵꿀잼': 3,
    '재밌': 2, '재미있': 2, '재밋': 2, '잼있': 2, '재미남': 2, '재미나': 2,
    '좋다': 1.5, '좋네': 1.5, '좋음': 1.5, '좋아': 1.5, '좋은': 1, '좋았': 1.5, '좋겠': 0.5, '좋던': 1,
    '최고': 2, '최고다': 2.5, '혜자': 2.5, '개혜자': 3, '만족': 2, '대만족': 3,
    '기대': 1, '기대됨': 1.5, '기대된': 1.5, '설렌': 1.5, '감사': 1.5, '고맙': 1.5, '고마워': 1.5,
    '훌륭': 2, '잘했': 2, '잘함': 1.5, '잘만들': 2, '잘 만들': 2, '예쁘': 1.5, '이쁘': 1.5, '예쁨': 1.5, '이쁨': 1.5,
    '귀엽': 1.5, '귀여': 1.5, '멋지': 1.5, '멋있': 1.5, '간지': 1, '할만': 1.5, '할 만': 1.5, '할만함': 2,
    '추천': 1.5, '개꿀': 2, '꿀이': 1, '개이득': 2, '이득': 1, '칭찬': 1.5, '개선': 1, '개선됨': 2, '개선됐': 2,
    '대박': 1.5, '굿': 1.5, '굳굳': 1.5, 'ㅅㅌㅊ': 1.5, '상타치': 1.5, '사랑': 1, '행복': 1.5, '편하': 1, '편해': 1,
    '편리': 1, '쾌적': 2, '혜택': 1, '무난': 0.5, '괜찮': 1, '살아났': 2, '부활': 1.5, '흥하': 2, '흥했': 2, '흥겜': 2.5,
    '갓패치': 3, '갓업뎃': 3, '갓운영': 3, '역시': 0.5, '극호': 2, '호평': 2, '복귀': 1, '돌아왔': 1, '정상화': 1.5,
    '떡상': 1.5, '상한가': 1, '흥할': 1.5, '든든': 1, '신난': 1.5, '신나': 1.5, '즐겁': 2, '즐거': 2, '재밌다': 2.5, '맛있': 1, '깔끔': 1,
    # 영어
    'love': 2, 'loving': 2, 'great': 2, 'awesome': 2, 'amazing': 2, 'fun': 1.5, 'enjoy': 2, 'enjoying': 2,
    'nice': 1, 'cool': 1, 'fantastic': 2.5, 'best': 1.5, 'excellent': 2.5, 'beautiful': 2, 'gorgeous': 2,
    'recommend': 1.5, 'worth it': 2, 'improved': 1.5, 'improvement': 1, 'thanks': 1, 'thank you': 1, 'glad': 1.5,
    'happy': 1.5, 'hype': 1.5, 'hyped': 2, 'excited': 1.5, 'cute': 1.5, 'good': 1, 'solid': 1, 'addicting': 1.5,
    'addictive': 1.5, 'masterpiece': 3, 'polished': 1.5, 'smooth': 1, 'generous': 2, 'f2p friendly': 2.5,
    'well done': 2, 'impressive': 2, 'favorite': 1.5, 'favourite': 1.5, 'gg': 0.5, 'pog': 1.5, 'w game': 2, 'goated': 2.5,
}

NEG = {
    # 한국어
    '망겜': -3, '망게임': -3, '망했': -2.5, '망함': -2.5, '망하': -2, '망할': -2, '좆망': -3, 'ㅈ망': -3, '폭망': -3,
    '노잼': -2.5, '핵노잼': -3, '재미없': -2.5, '재미 없': -2.5, '재미가 없': -2.5, '재미도 없': -2.5,
    '쓰레기': -2.5, '쓰렉': -2.5, '별로': -1.5, '실망': -2, '최악': -3, '짜증': -2, '화나': -2, '빡치': -2, '빡침': -2,
    '접는다': -2.5, '접음': -2.5, '접었': -2.5, '접을': -2, '접어야': -2, '접고': -1.5, '탈주': -2, '환불': -2,
    '버그': -1.5, '렉': -1.5, '랙': -1, '튕김': -2, '튕기': -2, '튕겨': -2, '서버터': -2.5, '서버 터': -2.5, '오류': -1.5,
    '먹통': -2, '대기열': -1, '창렬': -2.5, '사기': -1.5, '돈독': -2.5, '돈벌레': -2.5, '과금유도': -2.5, '과금 유도': -2.5,
    '개판': -2.5, '불만': -1.5, '억까': -0.5, '억지': -1, '밸붕': -2.5, '불편': -1.5, '피곤': -1.5, '지루': -2,
    '노답': -2.5, '답없': -2.5, '거지같': -2.5, '개같': -2, '좆같': -2.5, 'ㅈ같': -2.5, '똥겜': -3, '구리': -1.5,
    '구림': -1.5, '구려': -1.5, '작업장': -1.5, '매크로': -1, '하락': -1, '이탈': -1.5, '안좋': -1.5, '안 좋': -1.5,
    '좋지않': -1.5, '좋지 않': -1.5, '시발': -0.7, '씨발': -0.7, 'ㅅㅂ': -0.7, '병신': -1, 'ㅂㅅ': -1, 'ㅉㅉ': -1.5,
    '한숨': -1.5, '에휴': -1.5, '에효': -1.5, '하아': -1, 'ㅠㅠ': -0.5, 'ㅜㅜ': -0.5, '역겹': -2.5, '역겨': -2.5,
    '극혐': -2.5, '혐오': -2, '양심': -1, '날먹': -1.5, '뇌절': -2, '삽질': -1.5, '호구': -1.5, '배신': -2,
    '현자타임': -1.5, '현타': -1.5, '손절': -2, '틀딱': -1, '분탕': -1, '불공평': -2, '차별': -1.5, '너프': -1,
    '하향': -0.7, '죽었': -1.5, '죽은겜': -3, '고인물': -0.5, '숙제': -1, '노가다': -1, '피로도': -1.5,
    '스트레스': -1.5, '답답': -1.5, '어이없': -2, '황당': -1.5, '미쳤': -0.5, '개빡': -2, '쌉': -0.3, '버린': -1,
    '포기': -1.5, '후회': -2, '사장': -1, '섭종': -2.5, '서비스 종료': -2, '개악': -3, '개망': -3, '망한': -2, '떡락': -1.5, '하한가': -1, '폐급': -1.5, '나락': -2, '역대급 패치': 0,
    # 영어
    'bad': -1.5, 'worst': -3, 'trash': -2.5, 'garbage': -2.5, 'hate': -2, 'boring': -2, 'p2w': -2.5,
    'pay to win': -2.5, 'pay-to-win': -2.5, 'scam': -2.5, 'greedy': -2.5, 'greed': -2, 'cash grab': -3, 'cashgrab': -3,
    'bug': -1, 'bugs': -1, 'buggy': -2, 'broken': -2, 'lag': -1.5, 'laggy': -2, 'crash': -1.5, 'crashes': -1.5,
    'crashing': -2, 'dead game': -3, 'dying': -0.7, 'game is dying': -3, 'miserable': -2, 'worried': -1, 'concerned': -1, 'quit': -2, 'quitting': -2.5, 'uninstall': -2.5, 'refund': -2,
    'disappointed': -2, 'disappointing': -2, 'awful': -2.5, 'terrible': -2.5, 'sucks': -2, 'suck': -1.5,
    'predatory': -3, 'unplayable': -3, 'bots': -1.5, 'botting': -2, 'botters': -2, 'rip off': -2.5, 'ripoff': -2.5,
    'overpriced': -2.5, 'pricey': -1.5, 'expensive': -1.5, 'annoying': -2, 'frustrating': -2, 'frustrated': -2,
    'tedious': -1.5, 'grindy': -1, 'shit': -1, 'wtf': -1.5, 'ridiculous': -2, 'joke': -1, 'lazy': -2,
    'unfair': -2, 'mess': -1.5, 'disaster': -2.5, 'nerf': -0.7, 'nerfed': -1, 'cheaters': -2, 'hackers': -2,
    'whales': -0.7, 'pathetic': -2.5, 'cringe': -1.5, 'meh': -1, 'bored': -1.5, 'waste': -2, 'insane': -0.3,
}

# 2026-10-06 사용자 라벨·판단 이유(240건) 검토 후 보강 — 특정 게임이 아니라 MMO 커뮤니티 일반 표현만.
# 사용자 기준: '모바일 게임 같다/PC 이식 불량', '숙제·반복 피로', '스토리 부실 조롱', '돈 우선 운영'은 부정.
# 유저끼리의 욕설·과거 버그 질문·해결 팁은 게임 평가가 아니므로 중립 → 해당 단어 가중치를 낮춘다.
NEG.update({
    'mobile game': -1.5, 'mobile port': -2, 'poor port': -2.5, 'bad port': -2.5, 'mobile ui': -1.5,
    'chore': -1.5, 'second job': -2, '2nd job': -2, 'ruined': -2, 'soulless': -2, 'souless': -2,
    'outdated': -1.5, 'no future': -2.5, 'money first': -2.5, 'wasted': -1.5, 'waste of time': -2.5,
    'horrible': -2.5, 'worse': -1.2, 'pay-to-progress': -2.5, 'pay to progress': -2.5, 'pay2win': -2.5,
    'stupid': -1.5, 'nonsense': -1.5, 'crap': -1.5, 'dishonest': -2, 'unacceptable': -2, 'not worth': -2,
    'langweilig': -2, 'untragbar': -2, 'schlecht': -1.5, 'enttäuscht': -2,
    '모바일겜': -1.5, '모바일 게임': -1, '폰겜': -1.5, '불신': -1, '폐사': -2, '황폐': -2, '질려': -2, '질림': -2,
    '질린다': -2, '단점': -1.5, '빨간약': -1, '중국산': -1.5, '물어내': -1, '돈만': -2, '양산형': -2,
    # 가중치 하향(중립 오탐 원인): 유저 비방·과거 버그 질문·팁에 흔함
    '병신': -0.5, 'ㅂㅅ': -0.5, '사기': -0.7, '노가다': -0.5, 'bug': -0.5, 'bugs': -0.5, 'bad': -1.0,
})
POS.update({
    'i like': 1.5, 'way better': 2, 'feels better': 1.5, 'have fun': 1.5, 'having fun': 1.5,
    'not that expensive': 2, 'not expensive': 2, 'well made': 2, 'worth': 1,
    '건강': 1.5, '할만하': 2, '괜찮은데': 1, '나쁘지 않': 1.5,
})

# 사전을 손보면 이 값을 바꾼다 → 라벨 지문이 바뀌어 다음 실행에 과거 수집분 전체가 재계산된다
LEXICON_VERSION = '2026-10-09a'  # 이유 따옴표 추출 버그 수정(쉼표가 부정 표현으로 등록되던 문제)

# 영어 부정어: 뒤 3토큰 안의 감성어 부호를 뒤집는다
EN_NEGATORS = {'not', 'no', 'never', "don't", 'dont', "isn't", 'isnt', "wasn't", 'wasnt', "can't", 'cant',
               "doesn't", 'doesnt', "won't", 'wont', "aren't", 'arent', 'hardly', 'barely', "didn't", 'didnt'}

LEX = {**POS, **NEG}
LEX_SORTED = sorted(LEX.items(), key=lambda kv: -len(kv[0]))
USER_LEX = {}  # 사용자가 엑셀 '이유 설명'에 따옴표로 적은 표현 → 가중치(기본 사전보다 우선, 0이면 무시)


def set_user_lexicon(d):
    """엑셀 판단 이유에서 뽑은 표현을 사전에 덮어쓴다. 같은 표현이 기본 사전에 있으면 사용자 값이 이긴다."""
    global LEX_SORTED, USER_LEX
    USER_LEX = {k.lower(): float(v) for k, v in (d or {}).items() if k.strip()}
    LEX_SORTED = sorted({**LEX, **USER_LEX}.items(), key=lambda kv: -len(kv[0]))
_ASCII = re.compile(r'^[a-z0-9 \-]+$')


def lexicon_score(text):
    """(점수, 근거 리스트) 반환. 근거는 '단어(+1.5)' 형식."""
    t = (text or '').lower()
    taken = [False] * len(t)
    hits = []
    score = 0.0
    for term, w in LEX_SORTED:
        if w == 0 and term not in USER_LEX:
            continue
        start = 0
        while True:
            i = t.find(term, start)
            if i < 0:
                break
            j = i + len(term)
            start = j
            if any(taken[i:j]):
                continue
            if _ASCII.match(term):  # 영어는 단어 경계 필요
                if (i > 0 and t[i - 1].isalnum()) or (j < len(t) and t[j].isalnum()):
                    continue
                prev = re.findall(r"[a-z']+", t[max(0, i - 25):i])[-3:]
                if any(p in EN_NEGATORS for p in prev):
                    w2 = -w * 0.8
                    hits.append(f'not {term}({w2:+.1f})')
                    score += w2
                    for k in range(i, j):
                        taken[k] = True
                    continue
            for k in range(i, j):
                taken[k] = True
            if w == 0:  # 사용자가 '이 표현은 판단 근거 아님'으로 지정
                continue
            hits.append(f'{term}({w:+.1f}){"★" if term in USER_LEX else ""}')
            score += w
    return score, hits


# ---------------------------------------------------------------- 나이브 베이즈
LABELS = ('긍정', '중립', '부정')


def _features(text):
    t = (text or '').lower()
    t = re.sub(r'https?://\S+', ' ', t)
    feats = re.findall(r"[a-z']{2,}|[가-힣ㄱ-ㅎㅏ-ㅣ]+|\d+", t)
    out = list(feats)
    for w in feats:  # 한글은 교착어라 문자 2-gram 으로 어미 변화를 흡수
        if re.match(r'[가-힣ㄱ-ㅎ]', w) and len(w) >= 2:
            out += [w[k:k + 2] for k in range(len(w) - 1)]
    return out


class NaiveBayes:
    def __init__(self, samples):
        """samples: [(text, label)]"""
        self.n = len(samples)
        self.class_n = Counter(l for _, l in samples)
        self.word_n = {l: Counter() for l in LABELS}
        for text, l in samples:
            self.word_n[l].update(_features(text))
        self.vocab = set().union(*[set(c) for c in self.word_n.values()])
        self.total = {l: sum(self.word_n[l].values()) for l in LABELS}
        self.exact = {}
        for text, l in samples:
            self.exact[_norm(text)] = l

    @property
    def usable(self):
        return self.n >= 30 and self.class_n['긍정'] >= 5 and self.class_n['부정'] >= 5

    def proba(self, text):
        V = len(self.vocab) + 1
        logp = {}
        for l in LABELS:
            lp = math.log((self.class_n[l] + 1) / (self.n + 3))
            for f in _features(text):
                lp += math.log((self.word_n[l][f] + 1) / (self.total[l] + V))
            logp[l] = lp
        m = max(logp.values())
        ex = {l: math.exp(v - m) for l, v in logp.items()}
        s = sum(ex.values())
        return {l: ex[l] / s for l in LABELS}


def _norm(text):
    return re.sub(r'\s+', ' ', (text or '').strip().lower())[:500]


def classify(text, nb=None, use_exact=True):
    """반환: dict(label, score, hits, ambiguous, method[, conf]).
    nb: build_model() 의 Learner(또는 None). 학습 모델이 채택돼 있으면 그 3-class 확률로 판정하고,
    '애매함'도 모델 확신도로 정한다(가장 헷갈리는 글이 검토 엑셀로 가야 라벨 효과가 크다)."""
    score, hits = lexicon_score(text)
    if nb is not None and use_exact:
        lab = nb.exact.get(_norm(text))
        if lab:
            return {'label': lab, 'score': {'긍정': 3, '중립': 0, '부정': -3}[lab], 'hits': ['사용자 라벨 일치'],
                    'ambiguous': False, 'method': '라벨'}
    model = getattr(nb, 'model', None)
    if model is not None:
        p = model.proba(text)
        ranked = sorted(p.items(), key=lambda kv: -kv[1])
        label, top = ranked[0]
        margin = top - ranked[1][1]
        return {'label': label, 'score': round(score, 2), 'hits': hits, 'conf': round(top, 3),
                'ambiguous': bool(top < 0.6 or margin < 0.2), 'method': '학습(로지스틱)'}
    method = '사전'
    pos = any('(+' in h for h in hits)
    neg = any('(-' in h for h in hits)
    if score >= 1:
        label = '긍정'
    elif score <= -1:
        label = '부정'
    else:
        label = '중립'
    length = len((text or '').strip())
    ambiguous = (
        (pos and neg and abs(score) < 2.5)          # 긍·부정 신호가 섞임
        or (hits and abs(score) < 1)                 # 신호가 있으나 약함
        or (not hits and length >= 12)               # 할 말은 있는데 사전에 안 걸림
        or (abs(score) >= 1 and abs(score) < 1.5 and length >= 40)  # 긴 글에 약한 신호 하나
    )
    return {'label': label, 'score': round(score, 2), 'hits': hits, 'ambiguous': bool(ambiguous), 'method': method}


# ---------------------------------------------------------------- 학습기 (2026-10-06 교체)
# 나이브 베이즈는 문장 절반에서 |log(긍/부)| ≥ 3 으로 과신해 사용자가 '중립'이라 한 글을 긍·부정으로
# 밀어냈다(5-fold 정확도 사전만 62.5% → NB 섞으면 32.5%). 그래서
#  ① 단어·한글 2-gram·사전 점수를 함께 넣는 3-class 로지스틱 회귀(확률이 덜 과신)로 바꾸고
#  ② 라벨이 바뀔 때마다 교차검증으로 설정을 고르되 '사전만'보다 나을 때만 쓴다(학습이 성능을 깎지 못하게).
import random as _random

_LR_GRID = [  # (L2, 에폭, 클래스 균형)
    (0.003, 25, False), (0.01, 25, False), (0.03, 25, False),
    (0.003, 25, True), (0.01, 25, True),
]


def _lr_features(text):
    """희소 특징 {이름: 값}. 단어/2-gram 은 존재 여부(1), 사전은 수치."""
    f = {}
    for t in _features(text):
        f['w:' + t] = 1.0
    score, hits = lexicon_score(text)
    pos = sum(float(re.search(r'\(([-+]\d+\.\d)\)', h).group(1)) for h in hits if '(+' in h)
    neg = -sum(float(re.search(r'\(([-+]\d+\.\d)\)', h).group(1)) for h in hits if '(-' in h)
    f['lex:pos'] = min(pos, 6) / 3
    f['lex:neg'] = min(neg, 6) / 3
    f['lex:score'] = max(-6, min(6, score)) / 3
    f['lex:none'] = 0.0 if hits else 1.0
    n = len((text or '').strip())
    f['len:' + ('s' if n < 15 else 'm' if n < 60 else 'l')] = 1.0
    f['bias'] = 1.0
    return f


class LogReg:
    def __init__(self, l2=0.01, epochs=25, balanced=False, seed=7):
        self.l2, self.epochs, self.balanced, self.seed = l2, epochs, balanced, seed
        self.W = {c: {} for c in LABELS}

    def fit(self, samples):
        data = [(_lr_features(t), l) for t, l in samples if l in LABELS]
        cnt = Counter(l for _, l in data)
        cw = {c: (len(data) / (3 * cnt[c])) ** 0.5 if self.balanced and cnt[c] else 1.0 for c in LABELS}
        G = {c: {} for c in LABELS}  # AdaGrad 누적
        rnd = _random.Random(self.seed)
        for _ in range(self.epochs):
            rnd.shuffle(data)
            for f, y in data:
                p = self._proba_f(f)
                for c in LABELS:
                    g0 = (p[c] - (1.0 if c == y else 0.0)) * cw[y]
                    Wc, Gc = self.W[c], G[c]
                    for k, v in f.items():
                        g = g0 * v + self.l2 * Wc.get(k, 0.0)
                        Gc[k] = Gc.get(k, 0.0) + g * g
                        Wc[k] = Wc.get(k, 0.0) - 0.5 * g / (Gc[k] ** 0.5 + 1e-8)
        return self

    def _proba_f(self, f):
        z = {c: sum(self.W[c].get(k, 0.0) * v for k, v in f.items()) for c in LABELS}
        m = max(z.values())
        e = {c: math.exp(v - m) for c, v in z.items()}
        s = sum(e.values())
        return {c: e[c] / s for c in LABELS}

    def proba(self, text):
        return self._proba_f(_lr_features(text))


class Learner:
    """build_model() 이 돌려주는 학습 상태. kind: 'lexicon'(사전만) | 'logreg'."""

    def __init__(self, labeled, cached=None):
        self.n = len(labeled)
        self.class_n = Counter(r['label'] for r in labeled)
        self.exact = {_norm(r['text']): r['label'] for r in labeled}
        self.model = None
        self.kind = 'lexicon'
        self.cv = None
        if self.n < 30 or self.class_n['긍정'] < 5 or self.class_n['부정'] < 5:
            return
        self.cv = cached or select_model(labeled)
        best = self.cv.get('best')
        if best:
            l2, ep, bal = best
            self.model = LogReg(l2, ep, bal).fit([(r['text'], r['label']) for r in labeled])
            self.kind = 'logreg'

    @property
    def usable(self):
        return self.model is not None


def _cv_acc(rows, make, k=5):
    hit = 0
    for f in range(k):
        test = rows[f::k]
        train = [r for i, r in enumerate(rows) if i % k != f]
        m = make(train)
        for r in test:
            hit += classify(r['text'], m, use_exact=False)['label'] == r['label']
    return hit / len(rows) * 100


class _Fixed:
    def __init__(self, model):
        self.model, self.exact, self.usable = model, {}, model is not None


def select_model(labeled):
    """5-fold 로 사전만 vs 로지스틱 회귀 설정들을 비교해 가장 나은 것을 고른다.
    사전만보다 낫지 않으면 best=None(사전만 사용)."""
    rows = sorted(labeled, key=lambda r: str(r['id']))
    lex = _cv_acc(rows, lambda tr: None)
    trials = []
    for l2, ep, bal in _LR_GRID:
        acc = _cv_acc(rows, lambda tr, a=(l2, ep, bal): _Fixed(LogReg(*a).fit([(r['text'], r['label']) for r in tr])))
        trials.append(((l2, ep, bal), round(acc, 1)))
    cfg, acc = max(trials, key=lambda x: x[1])
    return {'n': len(rows), 'lexicon': round(lex, 1), 'model': acc if acc > lex else round(lex, 1),
            'logreg_best': acc, 'best': list(cfg) if acc > lex else None, 'trials': trials}


# ---------------------------------------------------------------- 주제(성격) 분류
TOPICS = [
    ('과금/BM', ['과금', '캐시', 'bm', '패스', '상점', '가격', '스킨', '결제', '현질', '돈', '유료', '패키지', '뽑기',
               'pay', 'p2w', 'price', 'pricey', 'shop', 'skin', 'cash', 'battle pass', '$', 'monetiz', 'whale']),
    ('버그/서버', ['버그', '렉', '서버', '튕', '오류', '점검', '접속', '대기열', 'bug', 'lag', 'server', 'crash',
                'queue', 'maintenance', 'disconnect', 'ping', 'error', 'login']),
    ('밸런스/직업', ['밸런스', '밸붕', '너프', '버프', '상향', '하향', '직업', '클래스', '사기캐', '딜량', 'class', 'nerf',
                 'buff', 'balance', 'build', 'dps', 'tank', 'healer']),
    ('작업장/핵', ['작업장', '매크로', '핵', '봇', '쌀먹', '어뷰', 'bot', 'hack', 'cheat', 'rmt', 'exploit']),
    ('운영/소통', ['운영', '엔씨', 'nc', '라방', '방송', '공지', '소통', '운영진', '디렉터', '사과', 'gm', 'dev',
                'ncsoft', 'communication', 'stream', 'announcement', 'apolog', 'roadmap']),
    ('콘텐츠/업데이트', ['업데이트', '업뎃', '패치', '레이드', '던전', '시즌', '신규', '이벤트', '보스', '퀘스트', '레벨',
                    'update', 'patch', 'raid', 'dungeon', 'season', 'event', 'boss', 'quest', 'content', 'leveling']),
    ('PvP/어비스', ['pvp', '쟁', '공성', '전장', 'siege', 'arena']),
    ('커마/외형', ['커마', '외형', '의상', '옷', '커스터마이징', '얼굴', 'outfit', 'costume', 'character creation',
                'slider', 'fashion', 'selfie', 'screenshot']),
]


def extend_topics(extra):
    """config.json 의 topic_extra(게임 고유 직업명·지역명 등)를 주제 키워드에 더한다."""
    for name, kws in (extra or {}).items():
        for i, (n, base) in enumerate(TOPICS):
            if n == name:
                TOPICS[i] = (n, base + [k.lower() for k in kws if k.lower() not in base])
                break
        else:
            TOPICS.append((name, [k.lower() for k in kws]))


def _kw_hit(k, t):
    if not re.match(r'^[a-z]+$', k):
        return k in t
    if len(k) <= 3:  # bot→both, nc→once 오매칭 방지: 단어 전체(+복수형)만
        return re.search(rf'\b{k}s?\b', t) is not None
    return re.search(rf'\b{k}', t) is not None


def topic_of(text):
    t = (text or '').lower()
    best, bn = '기타/잡담', 0
    for name, kws in TOPICS:
        n = sum(1 for k in kws if _kw_hit(k, t))
        if n > bn:
            best, bn = name, n
    return best
