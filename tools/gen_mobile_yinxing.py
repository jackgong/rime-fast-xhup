#!/usr/bin/env python3
"""生成纯小鹤音形（定长四码）词库，供 iOS 仓输入法（Hamster）使用。

数据源是本仓库的 cn_dicts/，所以字集与权重跟 Mac 上完全一致。
不依赖 lua —— Hamster 的方案规范要求少用 lua，且移动端 lua 未充分测试。

取码规则（小鹤音形官方，2026-09-01 查证）:
    单字        双拼2 + 鹤形2
    二字词      首字双拼2 + 末字双拼2
    三字词      前两字首码 + 末字双拼2
    四字以上    前三字首码 + 末字首码
  —— 全部都是四码，这是音形方案的设计：定长、重码接近零、少选字。

用法:
    python3 tools/gen_mobile_yinxing.py [权重阈值]      默认 5000

阈值权衡（词库 92.8 万条，全收会让四码空间重码爆炸）:
    ≥20000   4.6 万条   词少，常打的词可能要逐字打
    ≥5000   12.6 万条   默认，常用词覆盖够、重码适中
    ≥2000   19.2 万条   覆盖更全，但同码候选变多 = 手机上要多滑一下
"""
import io, os, re, sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHARS = os.path.join(ROOT, 'cn_dicts/flypy_chars.dict.yaml')
WORDS = os.path.join(ROOT, 'cn_dicts/flypy_base.dict.yaml')
OUT = os.path.join(ROOT, 'mobile/flypy_yinxing.dict.yaml')

def word_code(syls):
    """按小鹤音形规则给词取四码。"""
    n = len(syls)
    if n == 2:
        return syls[0] + syls[1]
    if n == 3:
        return syls[0][0] + syls[1][0] + syls[2]
    if n >= 4:
        return syls[0][0] + syls[1][0] + syls[2][0] + syls[-1][0]
    return None                      # 单音节走字表，不从词库取

def main(argv):
    thr = int(argv[0]) if argv else 5000
    rows, seen = [], set()

    # 单字：双拼 + 鹤形
    nchar = 0
    for line in io.open(CHARS, encoding='utf-8'):
        m = re.match(r'^(\S+)\t(\w{2})~(\w)(\w)\t(\d+)\s*$', line)
        if not m:
            continue
        ch, yin, x1, x2, w = m.groups()
        code = yin + x1 + x2
        if (ch, code) in seen:
            continue
        seen.add((ch, code))
        rows.append((ch, code, int(w)))
        nchar += 1

    # 词：按取码规则
    nword = 0
    for line in io.open(WORDS, encoding='utf-8'):
        m = re.match(r'^(\S+)\t([a-z ]+)\t(\d+)\s*$', line)
        if not m:
            continue
        text, codes, w = m.groups()
        if int(w) < thr:
            continue
        syls = codes.split()
        if any(len(s) != 2 for s in syls):
            continue
        code = word_code(syls)
        if not code or len(code) != 4:
            continue
        if (text, code) in seen:
            continue
        seen.add((text, code))
        rows.append((text, code, int(w)))
        nword += 1

    rows.sort(key=lambda r: (-r[2], r[1]))

    with io.open(OUT, 'w', encoding='utf-8') as f:
        f.write('''# Rime dictionary
# encoding: utf-8
#
# 小鹤音形（定长四码）—— 移动端专用，供 iOS 仓输入法 Hamster 使用
#
# 由 tools/gen_mobile_yinxing.py 从 cn_dicts/ 生成，请勿手工编辑。
# 重新生成: python3 tools/gen_mobile_yinxing.py [权重阈值]
#
# 与 Mac 上 flypy_xhfast 的关系:
#   Mac 版是「双拼为主 + 形码按需」，重码靠权重和 Ctrl+t 治 —— 手机上没这些键。
#   本方案是「定长四码音形」，重码从编码层面就压到接近零，目标是少选字。
#   两者共用同一份 cn_dicts/，所以字集与权重一致。

---
name: flypy_yinxing
version: "1.0"
sort: by_weight
...

''')
        for t, c, w in rows:
            f.write('%s\t%s\t%d\n' % (t, c, w))

    # 重码统计
    per = Counter(c for _, c, _ in rows)
    dist = Counter(per.values())
    print('权重阈值 %d' % thr)
    print('  单字 %d 条 / 词 %d 条 / 合计 %d 条' % (nchar, nword, len(rows)))
    print('  占用码位 %d 个（四码空间 456976）' % len(per))
    print('  文件 %.1f MB' % (os.path.getsize(OUT) / 1e6))
    print('\n  同码候选数分布:')
    for k in sorted(dist)[:8]:
        print('    %2d 个候选: %6d 个码位' % (k, dist[k]))
    many = sum(v for k, v in dist.items() if k > 8)
    if many:
        print('    >8 个候选: %6d 个码位' % many)
    uniq = dist.get(1, 0)
    print('\n  唯一候选（打满四码直接出，无需选字）: %.1f%%' % (100.0 * uniq / len(per)))

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
