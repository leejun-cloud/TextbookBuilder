#!/usr/bin/env python3
"""교재 삽화 생성기 — 프롬프트 명세(JSON) → 이미지 파일.

렌더러와 같은 철학으로 **제공자(provider)를 추상화**했다. 키가 있는 제공자를 골라 쓰고,
없으면 무엇이 필요한지 명확히 알려 준다(조용히 실패하지 않는다).

    images.json ─→ [provider: openai | gemini | placeholder] ─→ assets/*.png ─→ Typst

## 캐릭터 일관성 (120과를 만들 때 가장 중요)

같은 아이 얼굴이 과마다 달라지면 교재가 아니라 짜깁기가 된다. 그래서 두 단계로 만든다.

  1) `--kind character` 로 캐릭터 세트를 **한 번** 만든다 (남아/여아 × 포즈 여러 개).
  2) 과별 장면은 그 캐릭터 파일을 `reference`로 물려 만든다(제공자가 지원하면 edits API 사용).

## 사용법

    # 1) 명세 뼈대 만들기
    python3 scripts/gen_illustrations.py --init projects/<id>/lessons/01/images/images.json

    # 2) 무엇을 쓸 수 있는지
    python3 scripts/gen_illustrations.py --check

    # 3) 생성 (이미 있는 파일은 건너뜀. --force로 다시)
    python3 scripts/gen_illustrations.py projects/<id>/lessons/01/images/images.json
    python3 scripts/gen_illustrations.py <명세> --provider placeholder   # 키 없이 조판 시험용
    python3 scripts/gen_illustrations.py <명세> --only hero,seq-1 --force
"""
from __future__ import annotations

import argparse
import base64
import json
import math
import os
import struct
import sys
import time
import urllib.error
import urllib.request
import zlib

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 모든 프롬프트 앞에 붙는 공통 스타일 — 교재 전체의 그림 톤을 하나로 묶는다.
DEFAULT_STYLE = (
    "children's Bible textbook illustration, soft watercolor with clean line art, "
    "gentle pastel palette, round friendly faces, bright warm expressions, "
    "simple uncluttered composition, flat white or very light single-color background. "
    "No text, no letters, no numbers anywhere in the image. "
    "Not scary, no blood, no dark or frightening imagery."
)

ASPECT_SIZES = {          # aspect → OpenAI size
    '1:1': '1024x1024',
    '3:2': '1536x1024',
    '2:3': '1024x1536',
    '4:3': '1536x1024',
    '16:9': '1536x1024',
}


# ---------------------------------------------------------------- 제공자

class Provider:
    name = 'base'

    def available(self):
        return False, '구현되지 않았다'

    def generate(self, prompt, out_path, aspect='1:1', quality='medium',
                 references=(), timeout=300):
        raise NotImplementedError


class OpenAIProvider(Provider):
    """gpt-image-1. 참조 이미지가 있으면 /images/edits 를 써 캐릭터를 유지한다."""
    name = 'openai'
    GEN = 'https://api.openai.com/v1/images/generations'
    EDIT = 'https://api.openai.com/v1/images/edits'

    def __init__(self, model='gpt-image-1'):
        self.model = model
        self.key = os.environ.get('OPENAI_API_KEY', '')

    def available(self):
        if not self.key:
            return False, 'OPENAI_API_KEY가 없다'
        if not self.key.startswith('sk-'):
            return False, (f'OPENAI_API_KEY가 OpenAI 키 형식이 아니다(앞자리 {self.key[:3]}…). '
                           'platform.openai.com에서 발급한 sk-… 키가 필요하다')
        return True, f'{self.model}'

    def generate(self, prompt, out_path, aspect='1:1', quality='medium',
                 references=(), timeout=300):
        size = ASPECT_SIZES.get(aspect, '1024x1024')
        if references:
            data, ctype = _multipart({
                'model': self.model, 'prompt': prompt, 'size': size,
                'quality': quality, 'input_fidelity': 'high', 'n': '1',
            }, [('image[]', p) for p in references])
            req = urllib.request.Request(self.EDIT, data=data, headers={
                'Authorization': f'Bearer {self.key}', 'Content-Type': ctype})
        else:
            body = {'model': self.model, 'prompt': prompt, 'size': size,
                    'quality': quality, 'n': 1}
            req = urllib.request.Request(self.GEN, data=json.dumps(body).encode(), headers={
                'Authorization': f'Bearer {self.key}', 'Content-Type': 'application/json'})
        r = json.loads(urllib.request.urlopen(req, timeout=timeout).read())
        b64 = r['data'][0]['b64_json']
        with open(out_path, 'wb') as f:
            f.write(base64.b64decode(b64))
        return r.get('usage', {})


class GeminiProvider(Provider):
    """Google Gemini 이미지 생성. 참조 이미지를 프롬프트에 함께 넣어 캐릭터를 유지한다."""
    name = 'gemini'

    def __init__(self, model='gemini-2.5-flash-image'):
        self.model = model
        self.key = os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY') or ''

    def available(self):
        if not self.key:
            return False, 'GEMINI_API_KEY(또는 GOOGLE_API_KEY)가 없다'
        return True, f'{self.model}'

    def generate(self, prompt, out_path, aspect='1:1', quality='medium',
                 references=(), timeout=300):
        url = (f'https://generativelanguage.googleapis.com/v1beta/models/'
               f'{self.model}:generateContent')
        parts = [{'text': prompt}]
        for p in references:
            with open(p, 'rb') as f:
                parts.append({'inline_data': {
                    'mime_type': 'image/png' if p.endswith('.png') else 'image/jpeg',
                    'data': base64.b64encode(f.read()).decode()}})
        body = {'contents': [{'parts': parts}]}
        req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={
            'x-goog-api-key': self.key, 'Content-Type': 'application/json'})
        r = json.loads(urllib.request.urlopen(req, timeout=timeout).read())
        for cand in r.get('candidates', []):
            for part in cand.get('content', {}).get('parts', []):
                blob = part.get('inline_data') or part.get('inlineData')
                if blob and blob.get('data'):
                    with open(out_path, 'wb') as f:
                        f.write(base64.b64decode(blob['data']))
                    return {}
        raise RuntimeError(f'응답에 이미지가 없다: {json.dumps(r, ensure_ascii=False)[:300]}')


class PlaceholderProvider(Provider):
    """키 없이 조판을 시험할 때 쓰는 자리표시자. 비율만 맞춘 옅은 색 판을 만든다."""
    name = 'placeholder'

    def available(self):
        return True, '자리표시자(그림 아님)'

    def generate(self, prompt, out_path, aspect='1:1', quality='medium',
                 references=(), timeout=300):
        w, h = {'1:1': (900, 900), '3:2': (900, 600), '2:3': (600, 900),
                '4:3': (900, 675), '16:9': (960, 540)}.get(aspect, (900, 900))
        seed = sum(ord(ch) for ch in os.path.basename(out_path))
        base = [(214, 232, 252), (250, 236, 196), (226, 214, 246),
                (200, 226, 214), (250, 222, 236)][seed % 5]
        rows = []
        for y in range(h):
            row = bytearray([0])
            for x in range(w):
                edge = x < w * .04 or x > w * .96 or y < h * .05 or y > h * .95
                row += bytes((238, 240, 244) if edge else base)
            rows.append(bytes(row))
        raw = b''.join(rows)

        def chunk(t, d):
            return struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)

        with open(out_path, 'wb') as f:
            f.write(b'\x89PNG\r\n\x1a\n'
                    + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0))
                    + chunk(b'IDAT', zlib.compress(raw, 6))
                    + chunk(b'IEND', b''))
        return {}


PROVIDERS = {p.name: p for p in (OpenAIProvider(), GeminiProvider(), PlaceholderProvider())}


def _multipart(fields, files):
    """OpenAI edits용 multipart/form-data 조립(외부 의존성 없이)."""
    boundary = '----textbuilder' + str(int(time.time() * 1000))
    out = bytearray()
    for k, v in fields.items():
        out += f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
    for name, path in files:
        fn = os.path.basename(path)
        ctype = 'image/png' if fn.lower().endswith('.png') else 'image/jpeg'
        out += (f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"; '
                f'filename="{fn}"\r\nContent-Type: {ctype}\r\n\r\n').encode()
        with open(path, 'rb') as f:
            out += f.read()
        out += b'\r\n'
    out += f'--{boundary}--\r\n'.encode()
    return bytes(out), f'multipart/form-data; boundary={boundary}'


# ---------------------------------------------------------------- 명세

INIT_TEMPLATE = {
    "style": DEFAULT_STYLE,
    "out_dir": "../assets",
    "characters": {
        "_설명": "과 전체에서 재사용하는 캐릭터. 한 번만 만들고 이후 과에서 reference로 물린다.",
        "boy": "assets/characters/boy-smile.png",
        "girl": "assets/characters/girl-think.png"
    },
    "images": [
        {"id": "hero", "file": "hero.png", "aspect": "3:2", "quality": "medium",
         "prompt": "장면을 여기에 적는다. 예: 제자들이 예루살렘 다락방에 모여 기도하는 모습.",
         "reference": []},
        {"id": "seq-1", "file": "seq-1.png", "aspect": "4:3", "quality": "low",
         "prompt": "순서 그림 1컷.", "reference": ["boy"]}
    ]
}


def cmd_init(path):
    os.makedirs(os.path.dirname(os.path.abspath(path)) or '.', exist_ok=True)
    if os.path.isfile(path):
        print(f'이미 있다: {path}')
        return 1
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(INIT_TEMPLATE, f, ensure_ascii=False, indent=2)
    print(f'명세 뼈대를 만들었다: {path}\n프롬프트를 채운 뒤 다시 실행하라.')
    return 0


def cmd_check():
    print('삽화 제공자:')
    for name, p in PROVIDERS.items():
        ok, why = p.available()
        print(f'  {"✓" if ok else "✗"} {name:12} {why}')
    print('\n키 설정 방법')
    print('  OpenAI  : export OPENAI_API_KEY=sk-…      (platform.openai.com)')
    print('  Gemini  : export GEMINI_API_KEY=…         (aistudio.google.com)')
    print('\n주의: 현재 OPENAI_API_KEY에 다른 서비스(예: Fireworks fw_…) 키가 들어 있으면')
    print('      OpenAI 이미지 API 인증이 실패한다. 이미지용 키를 따로 두라.')
    return 0


def main():
    ap = argparse.ArgumentParser(description='교재 삽화 생성기')
    ap.add_argument('spec', nargs='?', help='images.json 명세 경로')
    ap.add_argument('--provider', default='', help='openai | gemini | placeholder (기본: 쓸 수 있는 것)')
    ap.add_argument('--only', default='', help='특정 id만 (쉼표 구분)')
    ap.add_argument('--force', action='store_true', help='이미 있는 파일도 다시 만든다')
    ap.add_argument('--init', default='', help='명세 뼈대를 만든다')
    ap.add_argument('--check', action='store_true', help='제공자 상태만 확인')
    ap.add_argument('--timeout', type=int, default=300)
    a = ap.parse_args()

    if a.init:
        return cmd_init(a.init)
    if a.check or not a.spec:
        return cmd_check()

    with open(a.spec, encoding='utf-8') as f:
        spec = json.load(f)
    spec_dir = os.path.dirname(os.path.abspath(a.spec))
    out_dir = os.path.abspath(os.path.join(spec_dir, spec.get('out_dir', '.')))
    os.makedirs(out_dir, exist_ok=True)

    # 제공자 결정
    if a.provider:
        if a.provider not in PROVIDERS:
            print(f'모르는 제공자: {a.provider} (쓸 수 있는 것: {", ".join(PROVIDERS)})', file=sys.stderr)
            return 1
        provider = PROVIDERS[a.provider]
        ok, why = provider.available()
        if not ok:
            print(f'{a.provider}를 쓸 수 없다: {why}', file=sys.stderr)
            return 1
    else:
        provider = None
        for name in ('openai', 'gemini'):
            ok, _why = PROVIDERS[name].available()
            if ok:
                provider = PROVIDERS[name]
                break
        if provider is None:
            print('쓸 수 있는 이미지 제공자가 없다.\n', file=sys.stderr)
            cmd_check()
            print('\n조판만 시험하려면: --provider placeholder', file=sys.stderr)
            return 1
    print(f'제공자: {provider.name} ({provider.available()[1]})')

    style = spec.get('style', DEFAULT_STYLE)
    chars = {k: v for k, v in (spec.get('characters') or {}).items() if not k.startswith('_')}
    keep = {x.strip() for x in a.only.split(',') if x.strip()}

    made, skipped, failed = 0, 0, 0
    for item in spec.get('images', []):
        iid = item.get('id') or item.get('file', '?')
        if keep and iid not in keep:
            continue
        out_path = os.path.join(out_dir, item.get('file', f'{iid}.png'))
        if os.path.isfile(out_path) and not a.force:
            print(f'  건너뜀 {iid} (이미 있다)')
            skipped += 1
            continue

        refs = []
        for r in item.get('reference', []) or []:
            rp = chars.get(r, r)
            rp = rp if os.path.isabs(rp) else os.path.join(spec_dir, rp)
            rp = os.path.abspath(rp)
            if os.path.isfile(rp):
                refs.append(rp)
            else:
                print(f'  경고 {iid}: 참조 이미지 없음 → {rp}')

        prompt = f'{style}\n\n{item.get("prompt", "")}'.strip()
        t0 = time.time()
        try:
            usage = provider.generate(
                prompt, out_path, aspect=item.get('aspect', '1:1'),
                quality=item.get('quality', 'medium'), references=refs, timeout=a.timeout)
            kb = os.path.getsize(out_path) // 1024
            extra = f' · 참조 {len(refs)}장' if refs else ''
            print(f'  만듦 {iid} → {os.path.relpath(out_path, REPO)} ({kb}KB, {time.time()-t0:.1f}초){extra}')
            if usage:
                print(f'       usage {json.dumps(usage, ensure_ascii=False)}')
            made += 1
        except urllib.error.HTTPError as e:
            print(f'  실패 {iid}: HTTP {e.code} {e.read().decode()[:200]}', file=sys.stderr)
            failed += 1
        except Exception as e:
            print(f'  실패 {iid}: {type(e).__name__} {e}', file=sys.stderr)
            failed += 1

    print(f'\n만듦 {made} · 건너뜀 {skipped} · 실패 {failed}')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
