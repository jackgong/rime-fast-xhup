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

    # ── 简码 ──────────────────────────────────────────────────────────
    # 一简/二简是日常输入的主路径，不是锦上添花：没有它每个字都要打满四码。
    #
    # 来源优先级：
    #   1. 使用者自己在 Mac 上按 Ctrl+t 定下来的那套（真实肌肉记忆）
    #      —— 若该词条已从词库进来，则**提权**而非跳过（否则 pin 等于白按）
    #   2. 其余码位按权重自动补，且限定类型：
    #      一简只取单字、二简只取单字或二字词（四字词放在二简位没有意义）
    MINE, AUTO1, AUTO2 = 99999999, 20000000, 10000000

    idx = {}                                  # (text, code) -> rows 下标
    for i, (t, c, _w) in enumerate(rows):
        idx[(t, c)] = i
    short = []
    nmine = nboost = 0

    def claim(code, text, weight):
        """加一条简码；若该 (词,码) 已存在则提权。"""
        nonlocal nboost
        k = (text, code)
        if k in idx:                          # 已在词库里 → 提权
            t, c, w = rows[idx[k]]
            if weight > w:
                rows[idx[k]] = (t, c, weight)
                nboost += 1
            return True
        if k in seen:
            return False
        seen.add(k)
        short.append((text, code, weight))
        return True

    def read_pins():
        pin = os.path.join(ROOT, 'lua/pin_word_record.lua')
        if not os.path.exists(pin):
            return
        src = io.open(pin, encoding='utf-8').read()
        for m in re.finditer(r'\["([^"]+)"\]\s*=\s*\{([^}]*)\}', src):
            code = m.group(1)
            if not re.fullmatch(r'[a-z]{1,4}', code):
                continue                       # 跳过 ; / 之类的标点键
            for i, t in enumerate(re.findall(r'"([^"]*)"', m.group(2))):
                if t:
                    yield code, t, MINE - i

    def read_custom_phrase():
        cph = os.path.join(ROOT, 'custom_phrase.txt')
        if not os.path.exists(cph):
            return
        for line in io.open(cph, encoding='utf-8'):
            if line.startswith('#'):
                continue
            parts = line.rstrip('\n').split('\t')
            if '<br>' in parts[0]:
                continue          # <br>→换行 靠 lua/flypy_fixed.lua，移动端无 lua
            if len(parts) >= 2 and re.fullmatch(r'[a-z]{1,4}', parts[1]):
                # 保留 custom_phrase 里的相对顺序：同码多词时（如 of = →/->）
                # 第三列权重决定先后，拉平会让手机上的候选顺序变得不确定
                w = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 1
                yield parts[1], parts[0], MINE - 1000 + w

    for code, text, w in list(read_pins()) + list(read_custom_phrase()):
        if claim(code, text, w):
            nmine += 1

    # 自动补：按类型限定，只填没被占用的码位
    taken = {c for _, c, _ in short} | {c for _, c, _ in rows if len(c) < 4}
    best = {}
    for t, c, w in rows:
        if len(c) != 4:
            continue
        n_ch = len(t)
        for n, ok in ((1, n_ch == 1), (2, n_ch <= 2)):
            if not ok:
                continue
            pre = c[:n]
            if pre in taken:
                continue
            if pre not in best or w > best[pre][1]:
                best[pre] = (t, w)
    nauto = 0
    for pre, (t, _w) in best.items():
        if claim(pre, t, AUTO1 if len(pre) == 1 else AUTO2):
            nauto += 1

    # ── 英文自造词 ────────────────────────────────────────────────────
    # 手机上打的英文基本都是技术专有名词（Datadog / ghostty / kubectl），
    # 恰恰是通用英文词表里没有、只有自造词库里才有的。所以并这一份就够。
    #
    # 代价实测：英文长词让 18 个中文四码码位变成「可延长」而失去自动上屏，
    # 占 82967 个码位的 0.02% —— 因为音形码遵循双拼拼写规律，英文不遵循，
    # 四字母前缀几乎不重叠。可以忽略。
    EN_W = 15000000            # 高于自动补简码(1000万)，低于自建简码(1亿)
    enc = os.path.join(ROOT, 'en_dicts/en_custom.dict.yaml')
    nen = 0
    if os.path.exists(enc):
        for line in io.open(enc, encoding='utf-8'):
            m = re.match(r'^(\S+)\t(\S+)\t(\d+)\s*$', line)
            if not m:
                continue
            text, code = m.group(1), m.group(2).lower()
            if not re.fullmatch(r'[a-z]+', code):
                continue           # 跳过含 / 之类的码，speller 里没有这些键
            if claim(code, text, EN_W):
                nen += 1
    print('  英文自造词 %d 条（源自 en_dicts/en_custom.dict.yaml）' % nen)

    rows.extend(short)
    print('  简码：自建 %d 条（其中提权 %d）+ 自动补 %d 条' % (nmine, nboost, nauto))

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
