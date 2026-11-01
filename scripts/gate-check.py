#!/usr/bin/env python3
"""gate-check.py — 把 x-workflow 的文字门禁变成可执行检查。

用法: python3 scripts/gate-check.py <change-dir>

<change-dir> 是 .engineering/<change-id>/，内含 00-brief.md … 06-release.md。
退出码: 0 = 全部门禁通过（只打印 RESULT: PASS），1 = 有 FAIL 行，2 = 参数错误。

只依赖 Python 3 标准库，macOS 自带 python3 可直接跑。
"""

import os
import re
import sys

# 交接物契约：文件名固定，不许改名、不许合并（见 x-workflow「交接物契约」）。
ARTIFACTS = (
    "00-brief.md",
    "01-explore.md",
    "02-design.md",
    "03-impl.md",
    "04-test.md",
    "05-security.md",
    "06-release.md",
)

AC_RE = re.compile(r"AC-\d+")
HEADING_RE = re.compile(r"^##[ \t]+(.*)$")
SEP_CELL_RE = re.compile(r":?-+:?")

# 交接物头部契约（见 x-workflow「自审不算」）：每份产物首行写
# `produced-by: <session-id>`，且 01/02/03 的 id 互不相同。
# 行首不留空白、id 不含空白，才是可机器比对的写法。
PRODUCED_BY_RE = re.compile(r"^produced-by:\s*(\S+)\s*$")

# 01/02/03 必须由不同上下文产出，三份 id 两两不同。
PRODUCED_BY_TRIO = ("01-explore.md", "02-design.md", "03-impl.md")

# 四个禁用措辞，用 unicode 转义书写：扫描逻辑拿到真值，本文件本身又不会被
# 自己的禁用措辞规则命中（与 CONSISTENCY.md 第五节的写法保持一致）。
BANNED_PHRASES = (
    "\u57fa\u672c\u901a\u8fc7",
    "\u5927\u4f53\u6ca1\u95ee\u9898",
    "\u5e94\u8be5\u53ef\u4ee5",
    "\u5dee\u4e0d\u591a",
)

# G6「信号」判据：同一行里既有数字、又有下列任一标记，才算给出了阈值。
SIGNAL_MARKS = ("%", "次", "ms", "s", "分钟", "阈值", "<", ">", "<=", ">=")

# G6「回滚」判据里「像话」的字样：出现任意一个就认为写了可执行内容。
# 这是刻意保守的启发式 —— 只拦「观察一下」这类空话，不判断回滚步骤对不对
# （判断正确性需要读语义，静态脚本做不到）。宁可少报，不许假装能判对错。
ROLLBACK_TOKENS = (
    "分", "秒", "时", "版", "%", "次", "回", "退",
    "flag", "switch", "命令",
)


def read_text(path):
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        return handle.read()


def section_body(text, heading):
    """返回 `## <heading>` 的正文；该标题不存在时返回 None。

    正文 = 标题行之后、下一个 `## ` 标题之前的所有行。
    标题两侧空白（含行尾多余空格）先 strip 再精确比较；`###` 不算分节，
    因此小节内部的 `###` 会留在正文里。同名标题出现多次时取第一处。
    """
    lines = text.splitlines()
    target = heading.strip()
    start = None
    for index, line in enumerate(lines):
        match = HEADING_RE.match(line)
        if match and match.group(1).strip() == target:
            start = index + 1
            break
    if start is None:
        return None

    body = []
    for line in lines[start:]:
        if HEADING_RE.match(line):
            break
        body.append(line)
    return "\n".join(body)


def content_lines(body):
    """正文里的有效行：去掉空行与 # 开头的标题行。"""
    return [
        line.strip()
        for line in (body or "").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


def bullet_items(body):
    """正文里的 `- ` / `* ` 条目；前缀之后为空的不算条目。"""
    items = []
    for line in (body or "").splitlines():
        stripped = line.strip()
        if stripped.startswith("- ") or stripped.startswith("* "):
            text = stripped[2:].strip()
            if text:
                items.append(text)
    return items


def is_separator_row(row):
    """表格分隔行，如 `|---|:---:|`。"""
    cells = [cell.strip() for cell in row.strip().strip("|").split("|")]
    return bool(cells) and all(SEP_CELL_RE.fullmatch(cell) for cell in cells)


def table_data_rows(body):
    """表格数据行：以 `|` 开头，去掉分隔行，再丢掉第一行（表头）。"""
    rows = [
        line.strip()
        for line in (body or "").splitlines()
        if line.strip().startswith("|")
    ]
    rows = [row for row in rows if not is_separator_row(row)]
    return rows[1:] if rows else []


def first_content_line(text):
    """首个非空行（跳过空行与只有空白的行）；整篇没有内容时返回 None。"""
    for line in text.splitlines():
        if line.strip():
            return line
    return None


def produced_by_id(text):
    """取首行里的 session-id；首行不合头部契约或文件为空时返回 None。"""
    line = first_content_line(text)
    if line is None:
        return None
    match = PRODUCED_BY_RE.match(line)
    return match.group(1) if match else None


def check_produced_by(texts, present):
    """产物的 produced-by 头部契约：首行必须声明，01/02/03 三份 id 互不相同。

    只比对「同一行内」的 id 字符串，不判断 id 是否真是不同会话 —— 判断真假
    需要会话账本，静态脚本做不到。
    """
    fails = []
    ids = {}
    for name in ARTIFACTS:
        if not present[name]:
            continue
        session_id = produced_by_id(texts[name])
        if session_id is None:
            fails.append(
                "FAIL PRODUCED-BY: {0} 首行不是 produced-by: <session-id>".format(name)
            )
        else:
            ids[name] = session_id

    # 三份都在、且都认出了 id 才比对；缺 id 的那份已按上一条报过，不再连带报重号。
    if all(present[name] for name in PRODUCED_BY_TRIO):
        if all(name in ids for name in PRODUCED_BY_TRIO):
            counts = {}
            order = []
            for name in PRODUCED_BY_TRIO:
                session_id = ids[name]
                if session_id not in counts:
                    counts[session_id] = 0
                    order.append(session_id)
                counts[session_id] += 1
            for session_id in order:
                if counts[session_id] > 1:
                    fails.append(
                        "FAIL PRODUCED-BY: 01/02/03 的 produced-by 相同（{0}）".format(
                            session_id
                        )
                    )
    return fails


def check_order(present):
    """G0 之前先看时序：下一环产物存在，上一环产物就必须在。"""
    fails = []

    if not present["00-brief.md"]:
        if any(present[name] for name in ARTIFACTS if name != "00-brief.md"):
            fails.append("FAIL ORDER: 00-brief.md 缺失（目录中已有其他产物）")

    rules = (
        ("01-explore.md", "00-brief.md"),
        ("02-design.md", "01-explore.md"),
        ("03-impl.md", "02-design.md"),
        ("04-test.md", "03-impl.md"),
        ("05-security.md", "03-impl.md"),
        ("06-release.md", "03-impl.md"),
    )
    for dependent, required in rules:
        if present[dependent] and not present[required]:
            fails.append(
                "FAIL ORDER: {0} 存在但缺 {1}".format(dependent, required)
            )
    return fails


def check_g0(brief):
    """G0：brief 的四节必须齐，且至少写了一条 AC 编号。"""
    fails = []
    for heading in ("目标", "验收标准", "不做什么", "分级"):
        if section_body(brief, heading) is None:
            fails.append("FAIL G0: 00-brief.md 缺 ## {0}".format(heading))
    if not AC_RE.search(brief):
        fails.append("FAIL G0: 00-brief.md 未出现验收标准编号 AC-<数字>")
    return fails


def check_g2(design):
    """G2：不建清单非空；方案 ≥2 个；决策有正文。"""
    fails = []

    body = section_body(design, "不建清单")
    if body is None:
        fails.append("FAIL G2: 02-design.md 缺 ## 不建清单")
    elif not bullet_items(body):
        fails.append("FAIL G2: 02-design.md ## 不建清单 为空（至少 1 条 - 条目）")

    body = section_body(design, "方案对比")
    if body is None:
        fails.append("FAIL G2: 02-design.md 缺 ## 方案对比")
    else:
        # 表格与条目两种写法都收，取其中较多的那个作为方案数。
        count = max(len(table_data_rows(body)), len(bullet_items(body)))
        if count < 2:
            fails.append(
                "FAIL G2: 02-design.md ## 方案对比 只有 {0} 个方案"
                "（至少 2 个：表格数据行或 - 条目）".format(count)
            )

    body = section_body(design, "决策")
    if body is None:
        fails.append("FAIL G2: 02-design.md 缺 ## 决策")
    elif not content_lines(body):
        fails.append("FAIL G2: 02-design.md ## 决策 为空")
    return fails


def check_g4(brief, test):
    """G4：brief 里每条 AC 都要在 04-test.md 出现，缺一条报一条。"""
    fails = []
    ids = sorted(set(AC_RE.findall(brief)), key=lambda item: int(item[3:]))
    for ac_id in ids:
        if ac_id not in test:
            fails.append("FAIL G4: 04-test.md 未覆盖 {0}".format(ac_id))
    return fails


def check_g6(release):
    """G6：回滚有可执行内容且不说空话；信号有带数值的阈值行。"""
    fails = []

    body = section_body(release, "回滚")
    if body is None:
        fails.append("FAIL G6: 06-release.md 缺 ## 回滚")
    else:
        lines = content_lines(body)
        if not lines:
            fails.append("FAIL G6: 06-release.md ## 回滚 为空")
        else:
            flat = re.sub(r"\s+", "", body.lower())
            has_token = any(token in flat for token in ROLLBACK_TOKENS)
            if len(flat) < 4 or not has_token:
                fails.append(
                    "FAIL G6: 06-release.md ## 回滚 只有空话"
                    "（写命令、版本号或开关，并写回滚后验证）"
                )

    body = section_body(release, "信号")
    if body is None:
        fails.append("FAIL G6: 06-release.md 缺 ## 信号")
    else:
        hit = any(
            re.search(r"\d", line) and any(mark in line for mark in SIGNAL_MARKS)
            for line in body.splitlines()
        )
        if not hit:
            fails.append("FAIL G6: 06-release.md ## 信号 没有带数值的阈值行")
    return fails


def check_words(texts):
    """禁用措辞：命中一处报一行，带文件名和命中的措辞。"""
    fails = []
    for name in ARTIFACTS:
        text = texts.get(name)
        if text is None:
            continue
        for phrase in BANNED_PHRASES:
            for _ in range(text.count(phrase)):
                fails.append('FAIL WORD: {0} 出现 "{1}"'.format(name, phrase))
    return fails


def main(argv):
    if len(argv) != 2:
        print("FAIL ARGS: 用法 python3 scripts/gate-check.py <change-dir>")
        return 2

    change_dir = argv[1]
    if not os.path.isdir(change_dir):
        print("FAIL ARGS: 目录不存在")
        return 2

    texts = {}
    present = {}
    for name in ARTIFACTS:
        path = os.path.join(change_dir, name)
        present[name] = os.path.isfile(path)
        if present[name]:
            texts[name] = read_text(path)

    fails = []
    fails += check_order(present)
    fails += check_produced_by(texts, present)
    if present["00-brief.md"]:
        fails += check_g0(texts["00-brief.md"])
    if present["02-design.md"]:
        fails += check_g2(texts["02-design.md"])
    if present["00-brief.md"] and present["04-test.md"]:
        fails += check_g4(texts["00-brief.md"], texts["04-test.md"])
    if present["06-release.md"]:
        fails += check_g6(texts["06-release.md"])
    fails += check_words(texts)

    if fails:
        for line in fails:
            print(line)
        return 1

    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
