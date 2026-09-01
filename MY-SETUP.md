# 我的装机与维护手册

> 本文件是 fork 独有的（上游 `boomker/rime-fast-xhup` 没有此文件），
> 因此 `git pull upstream` **永远不会**在这里产生冲突。
>
> **为什么这么配**（需求来源、设计取舍、踩过的坑）见 Obsidian vault：
> `04-技术/输入法/输入法痛点清单.md`。本文件只讲**怎么重建**。

## 仓库结构

| 路径 | 仓库 | 可见性 | 内容 |
|---|---|---|---|
| `~/Library/Rime/` | `jackgong/rime-fast-xhup` | public | 方案配置 + 手动词表 |
| `~/Library/Rime/sync/` | `jackgong/rime-userdb`（待建） | **private** | 自动调频学习成果 |
| `~/Library/Rime/installation.yaml` | 不进任何仓库 | — | 每台机器独有 |

`sync/` 在外层的 `.gitignore` 里，所以它是一个**嵌套的独立仓库**，两者互不干扰。

## 新机器装机

```bash
# 1. 输入法本体（.pkg 需要 sudo 密码，必须自己在终端跑）
brew install --cask squirrel

# 2. 配置
git clone --recursive git@github.com:jackgong/rime-fast-xhup.git ~/Library/Rime

# 3. 学习成果（private）
git clone git@github.com:jackgong/rime-userdb.git ~/Library/Rime/sync

# 4. 改这台机器的标识（重要：别和其他机器重名）
#    编辑 installation.yaml → installation_id: "mbp-2028" 之类
```

然后：

1. 系统设置 → 键盘 → 文字输入/输入法 → 编辑… → **+** → 简体中文 → **鼠须管**
   （找不到就注销重登一次）
2. 切到鼠须管 → 菜单栏图标 → **重新部署**（首次约 1–2 分钟，97 万英文词条要建索引）
3. 菜单 → **同步用户数据** → Rime 自动合并各机器的 `*.userdb.txt` 到本地 userdb

### SSH 说明

本机用 host 别名隔离个人/工作账号（`~/.ssh/config`）：

```
Host github-personal
    HostName github.com
    User git
    IdentityFile ~/.ssh/id_ed25519_jackgong
    IdentitiesOnly yes
```

新机器如果只有个人账号的 key，直接用 `git@github.com:` 即可，不需要别名。

## 日常维护

### 拉上游更新

```bash
git pull upstream main
```

以下文件会冲突，**永远保留自己的版本**：

```bash
git checkout --ours custom_phrase.txt default.custom.yaml flypy_xhfast.custom.yaml \
                    lua/pin_word_record.lua lua/cold_word_records/
git add -A && git commit
```

`upstream` 的 push 地址已被设为 `DISABLED_no_push_to_upstream`，不会误推。

### 提交自己的改动

```bash
git add -A && git commit -m "config: ..." && git push
```

`sync/` 要单独提交（它是独立仓库）：

```bash
cd sync && git add -A && git commit -m "sync userdb" && git push
```

## 我的配置做了什么

`flypy_xhfast.custom.yaml`：

```yaml
# 默认注解类型：形码（原为声调）
- options: [mask_hint, tone_hint, comment_off]
  reset: 0

# 直接辅码（无引导符）：绩=jisr / 歌=ged / 解=jpd
speller/+:
  algebra/+:
    - derive|/||
```

`default.custom.yaml`：`flypy_xhfast` 提到 `schema_list` 首位（原默认是英文方案 `easy_en`）。

### 词表分工（重要，别写错地方）

```
码是自然的（本来就会那么敲）  → Ctrl+t          → lua/pin_word_record.lua
码是自己发明的（缩写、标点）  → custom_phrase.txt（改完需重新部署）
其余                          → 交给自动调频，不管 → *.userdb/（不进 git，靠 sync/）
```

**关键区别**：`Ctrl+t` 只能**重排当前输入码下已有的候选**；
`custom_phrase` 能把**任意词绑到任意码**（例：`od`→`、`、`hs`→双线核算）。

### 常用快捷键

| 键 | 作用 |
|---|---|
| `Ctrl+t` | 候选置顶（立即生效，不需部署） |
| `Ctrl+j` | 降频到第 4 位 |
| `Ctrl+x` | 隐藏候选 |
| `Ctrl+d` | 强制删词 |
| `Ctrl+n` | 切换注释类型（形码 / 声调 / 无） |
| `Ctrl+g` | 中英方案互切 |
| `Ctrl+q` / `8` | 简拼优先 |
| `Tab` / `Shift+Tab` | 音节间移动光标（配合直接辅码可逐字收窄，见下） |
| `9` / `0` | 以词定字，上屏首字 / 末字 |

**逐字收窄**（本方案最关键的用法）：

```
xkma  →  Tab（光标移到 xk 后）  →  敲 k  ⇒ xkk ma ⇒ 出「形码」
```

## 待发的上游 PR（草稿已存，未提交）

分支 **`docs/direct-aux-code-tradeoff`**（在 fork 上，基于 upstream/main，仅 11 行文档改动）

内容：给 README 与 `flypy_xhfast.custom.yaml` 补充 `derive|/||`（直接辅码）的实际取舍
—— 原文只写"新手不推荐"，未说明代价。本机实测的结论（三码会成为多音节词前缀、
`uuruf` 被切为 `uur|uf`、abbrev 降权无效）写进了文档。

**为什么没发**：等 issue #137 有回应再说。作者若对 issue 都不回，PR 大概也会沉；
那这份改动留在自己 fork 里一样有用。

开 PR 的链接：
https://github.com/jackgong/rime-fast-xhup/pull/new/docs/direct-aux-code-tradeoff

---

## 已知未解决

- **候选注释只显示形码**，想显示"音码~形码"完整码需改 `lua/flypy_switcher.lua`
  的 `use_mask` 分支（约 364 行）。`translator/comment_format` 在此**无效**
  （辅码注释由 lua filter 渲染，不走 yaml）。
- **云拼音**：Rime 无原生支持。词库外的长词改用 `` ` `` 造词解决。
- **额外挂载的 table_translator 候选不出现** —— 已向上游提 issue：
  [boomker/rime-fast-xhup#137](https://github.com/boomker/rime-fast-xhup/issues/137)

  两条独立路径（`.dict.yaml` + 载体 schema / `stabledb` 文本表）都编译加载成功、
  候选一个不出；换挂载位置（`@after last` → `@after 6`）也无差别。
  疑为方案的 filter 链（`lua/cand_selector.lua`）重建候选列表所致，未定位。

  **影响**：想给方案追加自定义 translator 走不通。本仓库的 `aux3.txt` 与
  `tools/gen_aux3.py` 就是为此准备的三码单字表，目前**未接线**——
  若 issue 有解，启用 `table_translator@aux3` 并关掉 `speller` 里的 `derive|/||` 即可；
  若上游确认是设计使然，则 `aux3.txt` 可删（`tools/gen_aux3.py` 一条命令能重新生成）。
