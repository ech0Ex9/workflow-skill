#!/usr/bin/env bash
# selftest-gate-check.sh — 证明 gate-check.py 在对的产物上放行、错的产物上拦住。
#
# 每个用例都把 gate-check.py 当子进程真跑一遍，只读它的真实退出码（以及
# 放行时的 RESULT: PASS 行），不做任何模拟或内联判定。
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CHECKER="$HERE/gate-check.py"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

if [ ! -f "$CHECKER" ]; then
  echo "SELFTEST: FAIL"
  echo "找不到 $CHECKER"
  exit 1
fi

# ---------- 夹具：一份完整、正确的 .engineering/<change-id>/ ----------

write_brief() {
  cat > "$1/00-brief.md" <<'EOF'
produced-by: s-00
## 目标
给订单接口加超时，作用在报价调用上。

## 验收标准
- AC-1 Given 上游 3s 无响应 When 下单 Then 返回 504 并写日志
- AC-2 Given 上游正常 When 下单 Then 返回 200

## 不做什么
- 不做重试，不做熔断，不改接口契约

## 分级
L2 跨模块
EOF
}

write_explore() {
  cat > "$1/01-explore.md" <<'EOF'
produced-by: s-01
## 现状
- 入口 src/order.py:42 → resp = fetch_quote()

## 未知
- UNKNOWN: 上游 p99 延迟
EOF
}

# $2 = 「不建清单」正文；传空串即可造出「空清单」用例。
write_design() {
  cat > "$1/02-design.md" <<EOF
produced-by: s-02
## 约束复述
3 秒内失败返回 504，接口契约不变。

## 方案对比
| 方案 | 做法 | 成本 | 可逆性 | 新概念数 | 淘汰理由 |
|---|---|---|---|---|---|
| A 调用点加超时 | 给 fetch_quote 传 timeout | 0.5 天 | 高 | 0 | - |
| B 新建超时网关 | 抽一层网关 | 5 天 | 中 | 3 | 新概念多，收益相同 |

## 决策
选 A：新概念最少，能达成同一结果。

## 不建清单
$2

## 测试接缝
| 接缝 | 能抓到 | 抓不到 |
|---|---|---|
| fetch_quote 调用 | 超时路径 | 上游真实延迟分布 |
EOF
}

write_impl() {
  cat > "$1/03-impl.md" <<'EOF'
produced-by: s-03
## 改动
- src/order.py:42 传 timeout=3

## 自检
- pytest -q → 12 passed（exit 0）
EOF
}

# $2 = 「验收标准映射」段落里的表格数据行。
write_test() {
  cat > "$1/04-test.md" <<EOF
produced-by: s-04
## 验收标准映射
| AC 编号 | 用例 | 结果 |
|---|---|---|
$2

## 边界与错误路径
| 场景 | 用例 | 结果 |
|---|---|---|
| 上游 2.9s | test_edge_ok | passed |
| 上游 3.1s | test_edge_timeout | passed |

## 证据
- 命令 → 输出：pytest -q → 14 passed（exit 0）

## 未覆盖与风险
- 上游慢抖动：未覆盖，风险低
EOF
}

write_security() {
  cat > "$1/05-security.md" <<'EOF'
produced-by: s-05
## 信任边界
- 报价服务返回的金额：不可信输入

## 发现
- 无攻击路径，note：超时日志里带订单号
EOF
}

# $2/$3 = 信号两张表的数据行（不含首尾竖线），$4 = 「回滚」正文。
write_release() {
  cat > "$1/06-release.md" <<EOF
produced-by: s-06
## 影响面
| 路径 | 流量比例 | 受影响用户 | 外部依赖 |
|---|---|---|---|
| /order | 100% | 全部 | 报价服务 |

## 信号
| 类型 | 指标 / 日志 | 阈值 | 观察窗口 |
|---|---|---|---|
| $2 |
| $3 |

## 回滚
$4

## Runbook
- 错误率超过阈值就按上面的回滚步骤执行
EOF
}

GOOD_SIGNAL_NORMAL='证明正常 | timeout_log 计数 | > 0 次/分钟 | 5 分钟'
GOOD_SIGNAL_BAD='证明异常 | 错误率 | > 1% | 5 分钟'
GOOD_ROLLBACK='- 步骤：执行 deploy rollback --to-version v1.2.3
- 回滚后验证：curl -s /healthz → 200
- 数据影响：无'

# 改写某份产物的 produced-by 行；$2 省略或为空 = 删掉该行（造「缺头部」用例）。
rewrite_produced_by() {
  local file="$1"
  local session_id="${2:-}"
  {
    if [ -n "$session_id" ]; then
      printf 'produced-by: %s\n' "$session_id"
    fi
    grep -v '^produced-by:' "$file" || true
  } > "$file.tmp"
  mv "$file.tmp" "$file"
}

BASE="$TMP/base"
DEMO="$BASE/.engineering/demo"
mkdir -p "$DEMO"
write_brief "$DEMO"
write_explore "$DEMO"
write_design "$DEMO" '- 不做：重试层　理由：本次只解决挂起
- 不做：可配置超时　理由：单一调用点无需配置'
write_impl "$DEMO"
write_test "$DEMO" '| AC-1 | test_timeout | passed |
| AC-2 | test_ok | passed |'
write_security "$DEMO"
write_release "$DEMO" "$GOOD_SIGNAL_NORMAL" "$GOOD_SIGNAL_BAD" "$GOOD_ROLLBACK"

# ---------- 用例执行 ----------

FAILED=0

# run_case <用例名> <期望退出码> <change-dir> [输出里必须出现的字面量]
run_case() {
  local name="$1"
  local expect="$2"
  local dir="$3"
  local must=""
  local got=0
  local out=""

  if [ "$#" -ge 4 ]; then
    must="$4"
  fi

  out="$(python3 "$CHECKER" "$dir" 2>&1)" || got=$?

  local bad=0
  if [ "$got" -ne "$expect" ]; then
    bad=1
  elif [ "$expect" -eq 0 ] && ! printf '%s\n' "$out" | grep -qx 'RESULT: PASS'; then
    bad=1
  elif [ "$expect" -ne 0 ] && ! printf '%s\n' "$out" | grep -q '^FAIL '; then
    bad=1
  fi

  if [ "$bad" -eq 0 ] && [ -n "$must" ] && ! printf '%s\n' "$out" | grep -qF -- "$must"; then
    bad=1
  fi

  if [ "$bad" -eq 0 ]; then
    echo "CASE $name: expect=$expect got=$got PASS"
  else
    echo "CASE $name: expect=$expect got=$got FAIL"
    printf '%s\n' "$out" | sed 's/^/    /'
    FAILED=1
  fi
}

# 1. 完整正确的产物 → 放行
C1="$TMP/c1"
cp -R "$BASE" "$C1"
run_case valid 0 "$C1/.engineering/demo"

# 2. 不建清单为空 → G2 拦
C2="$TMP/c2"
cp -R "$BASE" "$C2"
write_design "$C2/.engineering/demo" ""
run_case no-nonbuild 1 "$C2/.engineering/demo"

# 3. 测试漏掉 AC-2 → G4 拦
C3="$TMP/c3"
cp -R "$BASE" "$C3"
write_test "$C3/.engineering/demo" '| AC-1 | test_timeout | passed |'
run_case missing-ac 1 "$C3/.engineering/demo"

# 4. 回滚只写「观察一下」→ G6 拦
C4="$TMP/c4"
cp -R "$BASE" "$C4"
write_release "$C4/.engineering/demo" "$GOOD_SIGNAL_NORMAL" "$GOOD_SIGNAL_BAD" '- 观察一下'
run_case vague-rollback 1 "$C4/.engineering/demo"

# 5. 删掉 01-explore.md 但留着 02-design.md → 时序拦
C5="$TMP/c5"
cp -R "$BASE" "$C5"
rm -f "$C5/.engineering/demo/01-explore.md"
run_case order-broken 1 "$C5/.engineering/demo"

# 6. 测试里写禁用措辞 → WORD 拦
C6="$TMP/c6"
cp -R "$BASE" "$C6"
printf '%s\n' '- 结论：基本通过' >> "$C6/.engineering/demo/04-test.md"
run_case banned-word 1 "$C6/.engineering/demo"

# 7. 信号没有任何数值阈值 → G6 拦
C7="$TMP/c7"
cp -R "$BASE" "$C7"
write_release "$C7/.engineering/demo" '证明正常 | 服务存活 | 无 | 无' '证明异常 | CPU | 无 | 无' "$GOOD_ROLLBACK"
run_case no-signal-threshold 1 "$C7/.engineering/demo"

# 8. 04-test.md 删掉 produced-by 行 → 头部契约（首行声明）拦
C8="$TMP/c8"
cp -R "$BASE" "$C8"
rewrite_produced_by "$C8/.engineering/demo/04-test.md"
run_case no-produced-by 1 "$C8/.engineering/demo" 'FAIL PRODUCED-BY: 04-test.md'

# 9. 02/03 共用同一个 session id → 头部契约（三份互不相同）拦
C9="$TMP/c9"
cp -R "$BASE" "$C9"
rewrite_produced_by "$C9/.engineering/demo/03-impl.md" s-02
run_case dup-produced-by 1 "$C9/.engineering/demo" 'FAIL PRODUCED-BY: 01/02/03'

# ---------- 汇总 ----------

if [ "$FAILED" -eq 0 ]; then
  echo "SELFTEST: PASS"
  exit 0
fi

echo "SELFTEST: FAIL"
exit 1
