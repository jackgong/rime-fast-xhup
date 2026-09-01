#!/usr/bin/env python3
"""从 cn_dicts/flypy_chars.dict.yaml 生成三码单字表 flypy_aux3.dict.yaml。

三码 = 音码2 + 形码首位1。上游更新字表后重新跑一次即可。

为什么单独成表而不用 speller/algebra：见生成文件头部注释。
"""
import io, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'cn_dicts/flypy_chars.dict.yaml')
OUT = os.path.join(ROOT, 'aux3.txt')

HEADER = '''# Rime dictionary
# encoding: utf-8
#
# 三码单字表（音码2 + 形码首位1），由 cn_dicts/flypy_chars.dict.yaml 自动生成
#
# 为什么单独成表而不用 speller/algebra:
#   三码走 algebra 会成为多音节词的合法前缀，破坏切分——
#   打「输入法」(uu ru fa) 时 uur 被解析为「uu + 形码首位 r」→ 舒/俞/倏，词被打断。
#   根因不是权重（abbrev 降权也没用），而是 uur|uf 是"完整解析"、uu|ru|f 需要预测缺失码，
#   引擎天然偏向前者。
# 独立 table_translator 只对原始输入码查表，不参与音节切分，因此两者彻底解耦：
#   输入恰好 3 码 → 命中本表；输入更长 → 本表无条目，主翻译器正常切分。
#
# 重新生成: python3 tools/gen_aux3.py

---
name: flypy_aux3
version: "1.0"
sort: by_weight
...

'''

def main():
    rows, seen, uniq = [], set(), []
    for line in io.open(SRC, encoding='utf-8'):
        m = re.match(r'^(\S+)\t(\w+)~(\w)(\w)\t(\d+)\s*$', line)
        if not m:
            continue
        ch, yin, x1, _x2, w = m.groups()
        rows.append((ch, yin + x1, int(w)))
    for ch, code, w in rows:
        if (ch, code) in seen:
            continue
        seen.add((ch, code))
        uniq.append((ch, code, w))
    uniq.sort(key=lambda r: (-r[2], r[1]))
    with io.open(OUT, 'w', encoding='utf-8') as f:
        f.write(HEADER)
        for ch, code, w in uniq:
            f.write('%s\t%s\t%d\n' % (ch, code, w))
    print('%s: %d 条（去重前 %d）' % (os.path.relpath(OUT, ROOT), len(uniq), len(rows)))

if __name__ == '__main__':
    sys.exit(main())
