# CONSISTENCY.md — 一致性校验

> **改动任一 skill 之前先读本文件，改完跑第五节。**

## 为什么需要它

10 个 skill 共享一批定义：证据格式、结论优先、门禁 ID、产物名、QS 编号、汇报必答序列。这些定义**只能有一处真相，其余全是引用**。

改一处不改其余 = 同一套规则出现两个版本，门禁当场失效。

## 一、共享不变量

| # | 不变量 | 唯一真相在 | 谁必须遵守 |
|---|---|---|---|
| I-1 | 证据只有三种形态 | `x-quality`「证据格式」 | 全部 skill 引用，**不许重新定义** |
| I-2 | 结论优先 | `x-quality`「结论优先」 | 全部 skill 引用，**不许重新定义** |
| I-3 | 门禁只有 G0–G6，共 7 道 | `x-workflow`「门禁」 | 只许引用，不许新增或改名 |
| I-4 | 产物只有 `00-brief` … `06-release`，共 7 个 | `x-workflow`「交接物契约」 | 不许改名、不许合并 |
| I-5 | QS 只有 14 条 | `x-quality`「规则」 | 只许引用编号，不许改含义 |
| I-6 | skill 名 = 目录名 = frontmatter `name` | 各自 | 全部 |
| I-7 | `description` 以 `Use when` 开头 | 各自 | 全部 |
| I-8 | 代码围栏配对 | — | 全部 |
| I-9 | `x-quality` 不许引用任何角色名，含 `developer` / `reviewer` / `tester` 这类英文角色词 | — | `x-quality` |
| I-10 | `metadata.maturity` 只有 `probed` / `beta` 两个值；标 `beta` 的集合必须与 README「已知的待验证项」里那句声明**完全相等**（多一个少一个都算错） | 各自 | 全部 |
| I-11 | 验收标准编号只有 `AC-n`，由 `00-brief.md` 定义 | `x-workflow`「交接物契约」 | `x-workflow` / `x-test` / `scripts/gate-check.py` |
| I-12 | `x-ask` 是通用工具：不许引用任何角色名、产物名、门禁 ID | — | `x-ask` |
| I-13 | `x-report` 是通用工具：不许引用任何角色名、产物名、门禁 ID；**汇报必答序列只在 `x-report` 定义**，其他 skill 只许引用，不许自己列结构模板（`SCQA` / `PREP` / `STAR` / 金字塔） | `x-report`「判断入口」 | 全部 skill 引用，**不许重新定义** |

## 二、依赖方向（单向，不许反向）

| 引用者 | 允许引用 |
|---|---|
| `x-workflow` | 6 个角色 + `x-quality` + `x-ask` |
| 6 个角色 | `x-quality` + 自己的上下游产物 |
| `x-quality` | **任何角色都不许引用** |
| `x-ask` | 只许引用 `x-quality` |
| `x-report` | 只许引用 `x-quality` |

理由：`x-quality` 是尺子。尺子一旦认识某个角色，就不能被别的角色用。

同一条理由适用于 `x-ask`：它是通用工具。工具一旦知道自己在哪条链路里、产物叫什么、门禁编号是几，就只能在那条链路里用，而且链路一改名它就断。

`x-report` 同理：它按「读者要做的决定」查表，不按场景名，也不认识角色和产物——否则换一个团队、换一套产物命名，就得重写一遍。

角色之间也不许互相引用职责（"这个交给 x-secure 判断"可以，"x-secure 应该做 X"不行）。

## 三、改动影响矩阵

改之前先查这张表，改完按表复查。

| 你改了 | 必须复查 |
|---|---|
| 证据格式 | 全部 skill 文件；`x-quality` 的「禁止三种写法」；README 设计取舍 |
| 结论优先 | 全部 skill 文件（`x-explore` / `x-secure` / `x-release` 有具体落点） |
| 门禁 ID 或条件 | `x-workflow` 门禁表 + 6 个角色各自的「门禁 Gx」节 + README 链路图 |
| 产物名或数量 | `x-workflow` 契约表 + 各角色「输入 / 输出」+ README 产物树 + 实际 `.engineering/` 目录 |
| QS 编号或条数 | `x-quality` 规则 + `x-build` 硬约束 + `x-workflow` G3 + `x-quality` 复核示例 + README 结构行 |
| skill 改名 | 目录名 + frontmatter `name` + 全仓库交叉引用 + README 树 + 第二节依赖矩阵 |
| 新增 skill | 职责是否与第四节的「独占职责」重叠 + 是否进链路图 + 是否占产物编号 + frontmatter 是否有 `metadata.maturity` |
| `maturity` 标注 | 该 skill 的 frontmatter + README 结构树 + README「已知的待验证项」+ 第五节校验 |
| 汇报必答序列 | `x-report` 判断入口表 + 5 个引用它的角色 skill + README 调用关系图 + 第五节校验 |
| 呈现规则（矩阵） | `x-report`「呈现：矩阵」+ `x-release` / `x-secure` 的表格指针 + README 结构树 |
| 验收标准编号（`AC-n`） | `x-workflow` 交接物契约 + `x-test` 输出格式 + `scripts/gate-check.py` 的 G4 判据 + `scripts/selftest-gate-check.sh` 的 fixture |
| 角色边界 | 上下游的「输入 / 输出」是否还对得上 |

## 四、职责边界（不许重叠）

| skill | 独占职责 | 明确不做 |
|---|---|---|
| `x-workflow` | 定级、派角色、判定门禁放行或打回 | 不写代码、不做设计、不审查代码 |
| `x-quality` | 质量判据、证据格式、结论优先格式 | 不管流程、不管架构、不管安全 |
| `x-explore` | 报告现状：入口、调用链、契约、惯例、风险面、未知 | 不提方案、不改文件、不读全仓库 |
| `x-design` | 选方案、定接缝、列失败模式、写不建清单、留 ADR | 不写实现（签名 ≤5 行）、不做"以后可能需要"的扩展 |
| `x-build` | 垂直切片 TDD、逐条自检 QS | 不给自己签 G3、不顺手重构、不改测试迁就实现 |
| `x-test` | 验收映射、边界与错误路径、贴输出 | 不写实现、不改断言迁就实现、不用覆盖率当结论 |
| `x-secure` | 信任边界、入口枚举、按可达性定级、攻击路径 | 不报无路径的"可能存在风险"、不对线上做破坏性验证 |
| `x-release` | 影响面、放大效应、信号、发布策略、回滚、runbook | 不用"部署步骤"代替回滚、不用"观察一下"代替阈值 |
| `x-ask` | 把模糊输入问成四问答案（要什么 / 怎么算完 / 不做什么 / 多大），答不上的标 `未验证` | 不查事实、不设计方案、不判规模、不写产物文件 |
| `x-report` | 按读者要做的决定定必答序列，缺一问即未完成 | 不定义证据格式、不判质量、不代替产物文件 |

**新增 skill 前先对照**：它要做的事是否已被某一行的「独占职责」覆盖？是 → 不该新增 skill，应该是那个 skill 的一条规则。

## 五、可跑的校验

在仓库根目录执行。**有输出 = 有问题，无输出 = 通过。**

```bash
python3 - <<'PY'
import os, re, sys
names = sorted(d for d in os.listdir('.') if d.startswith('x-') and os.path.isdir(d))
bad = ['\u8d4c', '\u70c2', '\u88f8', '\u5751', '\u4eea\u5f0f', '\u8868\u6f14', '\u5e9f\u8bdd', '\u626f', '\u778e']
fail = []
for d in names:
    s = open(f'{d}/SKILL.md', encoding='utf-8').read()
    fm = s.split('---\n')[1]
    m = dict(re.findall(r'^(name|description):\s*(.+)$', fm, re.M))
    if m.get('name') != d:                       fail.append(f'{d}: I-6 name 与目录名不一致')
    if not m.get('description', '').startswith('Use when'):
        fail.append(f'{d}: I-7 description 不以 Use when 开头')
    mt = re.search(r'^  maturity: *(\w+)$', fm, re.M)
    if not mt or mt.group(1) not in ('probed', 'beta'):
        fail.append(f'{d}: I-10 maturity 缺失或不是 probed/beta')
    if s.count(chr(96)*3) % 2:                       fail.append(f'{d}: I-8 代码围栏不配对')
    if d != 'x-quality' and '\u8bc1\u636e\u683c\u5f0f' not in s:
        fail.append(f'{d}: I-1 未引用证据格式')
    if d != 'x-quality' and '## \u8bc1\u636e\u683c\u5f0f' in s:
        fail.append(f'{d}: I-1 重复定义证据格式')
    if d != 'x-quality' and '## \u7ed3\u8bba\u4f18\u5148' in s:
        fail.append(f'{d}: I-2 重复定义结论优先')
    hit = [w for w in bad if w in s]
    if hit:                                      fail.append(f'{d}: 禁用措辞 {hit}')
q = open('x-quality/SKILL.md', encoding='utf-8').read()
if len(re.findall(r'### QS-\d+', q)) != 14:      fail.append('I-5 QS 条数不是 14')
w = open('x-workflow/SKILL.md', encoding='utf-8').read()
if sorted(set(re.findall(r'\bG[0-6]\b', w))) != [f'G{i}' for i in range(7)]:
    fail.append('I-3 门禁不是 G0..G6 共 7 道')
for a in ('00-brief', '01-explore', '02-design', '03-impl', '04-test', '05-security', '06-release'):
    if a not in w:                               fail.append(f'I-4 缺产物 {a}.md')
for d in names:
    if d == 'x-quality':
        s = open(f'{d}/SKILL.md', encoding='utf-8').read()
        for o in names:
            if o != 'x-quality' and o in s:      fail.append(f'I-9 x-quality 引用了 {o}')
        for w in sorted(set(re.findall(r'\b(?:developer|reviewer|tester|architect|explorer|sre)\b', s, re.I))):
            fail.append(f'I-9 x-quality 引用了角色词 {w.lower()}')
a = open('x-ask/SKILL.md', encoding='utf-8').read()
for o in names:
    if o not in ('x-quality', 'x-ask') and o in a:
        fail.append(f'I-12 x-ask 引用了角色 {o}')
for x in ('00-brief', '01-explore', '02-design', '03-impl', '04-test', '05-security', '06-release'):
    if x in a:                                   fail.append(f'I-12 x-ask 引用了产物 {x}')
gb = sorted(set(re.findall(r'\bG[0-6]\b', a)))
if gb:                                           fail.append(f'I-12 x-ask 引用了门禁 {gb}')
rp = open('x-report/SKILL.md', encoding='utf-8').read()
for o in names:
    if o not in ('x-quality', 'x-report') and o in rp:
        fail.append(f'I-13 x-report 引用了 {o}')
for d in names:
    if d == 'x-report':                          continue
    t = open(f'{d}/SKILL.md', encoding='utf-8').read()
    hit = sorted(set(re.findall(r'\b(?:SCQA|PREP|STAR|MECE)\b', t)))
    if '\u91d1\u5b57\u5854' in t:                hit.append('\u91d1\u5b57\u5854')
    if hit:                                      fail.append(f'I-13 {d} 重复定义汇报结构 {hit}')
r = open('README.md', encoding='utf-8').read()
pend = r.split('## \u5df2\u77e5\u7684\u5f85\u9a8c\u8bc1\u9879')[-1]
decl = re.search(r'\u6807 `beta` \u7684\u5c31\u662f (.+?)\uff0c', pend)
declared = set(re.findall(r'x-[a-z-]+', decl.group(1))) if decl else set()
actual = set()
for d in names:
    fm = open(f'{d}/SKILL.md', encoding='utf-8').read().split('---\n')[1]
    if re.search(r'^  maturity: beta$', fm, re.M):
        actual.add(d)
if declared != actual:
    fail.append(f'README: I-10 beta 集合不一致 README={sorted(declared)} 实际={sorted(actual)}')
nq = len(re.findall(r'### QS-\d+', q))
for d in names:
    if f'{d}/' not in r:                         fail.append(f'README: 结构树缺 {d}/')
    line = [l for l in r.splitlines() if f'{d}/' in l and l.strip()[:3] in ('├──', '└──')]
    if line:
        fm = open(f'{d}/SKILL.md', encoding='utf-8').read().split('---\n')[1]
        if ('beta' in line[0]) != bool(re.search(r'^  maturity: beta$', fm, re.M)):
            fail.append(f'README: 结构树 {d} 的 beta 标注与 frontmatter 不一致')
m = re.search(r'QS-01\.\.QS-(\d+)', r)
if not m or int(m.group(1)) != nq:               fail.append(f'README: QS 条数与 x-quality({nq}) 不一致')
for a in ('00-brief', '01-explore', '02-design', '03-impl', '04-test', '05-security', '06-release'):
    if a not in r:                               fail.append(f'README: 缺产物 {a}.md')
m = re.search(r'(\d+) 道门禁', r)
if not m or int(m.group(1)) != 7:                fail.append('README: 门禁数与 x-workflow 不一致')
print('\n'.join(fail) if fail else 'RESULT: PASS')
sys.exit(1 if fail else 0)
PY
```

词表用 unicode 转义写，避免本文件自己被扫出来。新增禁用措辞时按同样方式加。

## 六、什么时候不用读全文

只改错别字，或只改某个 skill 内部的措辞、不触及第一节的共享定义 → 直接跑第五节就够。

只要动了共享定义，就必须按第三节逐行复查。
