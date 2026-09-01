#!/usr/bin/env python3
"""查某个自定义码位有没有冲突，再往 custom_phrase.txt 里加条目之前跑一下。

用法: python3 tools/check_code.py ai api sql
"""
import io, re, glob, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def build():
    chars, words = {}, {}
    for line in io.open(os.path.join(ROOT, 'cn_dicts/flypy_chars.dict.yaml'), encoding='utf-8'):
        m = re.match(r'^(\S+)\t(\w+)~(\w)(\w)\t(\d+)\s*$', line)
        if not m:
            continue
        ch, yin, x1, x2, w = m.groups()
        w = int(w)
        # 音码 / 三码(音+形首位) / 四码(音+完整形)
        for c in (yin, yin + x1, yin + x1 + x2):
            chars.setdefault(c, []).append((ch, w))
    for f in glob.glob(os.path.join(ROOT, 'cn_dicts/*.dict.yaml')):
        for line in io.open(f, encoding='utf-8'):
            m = re.match(r'^(\S+)\t([a-z ]+)\t(\d+)\s*$', line)
            if not m:
                continue
            t, c, w = m.groups()
            if len(t) > 1:
                words.setdefault(c.replace(' ', ''), []).append((t, int(w)))
    return chars, words

def main(argv):
    if not argv:
        print(__doc__)
        return 1
    chars, words = build()
    for c in argv:
        hits = sorted(chars.get(c, []) + words.get(c, []), key=lambda x: -x[1])[:5]
        if not hits:
            print('%-8s ✅ 空码位，零冲突' % c)
        else:
            top = hits[0][1]
            flag = '⚠️ 高频' if top >= 20 else '△ 低频' if top > 0 else '✅ 仅权重0'
            print('%-8s %s  %s' % (c, flag, '  '.join('%s(%d)' % h for h in hits)))
    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
