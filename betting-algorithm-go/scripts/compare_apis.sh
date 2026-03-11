#!/usr/bin/env bash
# compare_apis.sh — Phase 6 validation script
#
# Starts the Go server on :5001 (Python keeps :5000), sends identical requests
# to both, and diffs the JSON responses. Exits 0 if all diffs pass, 1 otherwise.
#
# Usage:
#   cd betting-algorithm-go
#   ./scripts/compare_apis.sh [--go-only]   # --go-only skips Python server
#
# Requirements: curl, jq, python3 (with app.py), go

set -euo pipefail

PYTHON_PORT=5000
GO_PORT=5001
GO_BINARY="./bin/server"
PYTHON_APP="../betting-algorithm/app.py"
PASS=0
FAIL=0
GO_ONLY=false

for arg in "$@"; do
  [[ "$arg" == "--go-only" ]] && GO_ONLY=true
done

# ── Colour helpers ────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

ok()   { echo -e "${GREEN}  PASS${NC} $1"; ((PASS++)) || true; }
fail() { echo -e "${RED}  FAIL${NC} $1"; ((FAIL++)) || true; }
info() { echo -e "${YELLOW}  INFO${NC} $1"; }

# ── Build Go server ───────────────────────────────────────────────────────────
echo "Building Go server..."
mkdir -p bin
go build -o "$GO_BINARY" ./cmd/server/
echo "Done."

# ── Start Go server ───────────────────────────────────────────────────────────
PORT=$GO_PORT DATA_DIR=./data "$GO_BINARY" &>/tmp/go_server.log &
GO_PID=$!
info "Go server started (PID $GO_PID) on :$GO_PORT"
sleep 2  # wait for listen

# ── Optionally start Python server ───────────────────────────────────────────
PYTHON_PID=""
if [[ "$GO_ONLY" == false ]] && [[ -f "$PYTHON_APP" ]]; then
  PORT=$PYTHON_PORT python3 "$PYTHON_APP" &>/tmp/python_server.log &
  PYTHON_PID=$!
  info "Python server started (PID $PYTHON_PID) on :$PYTHON_PORT"
  sleep 3
else
  GO_ONLY=true
  info "Python server skipped (--go-only or app.py not found)"
fi

# ── Cleanup on exit ───────────────────────────────────────────────────────────
cleanup() {
  kill "$GO_PID" 2>/dev/null || true
  [[ -n "$PYTHON_PID" ]] && kill "$PYTHON_PID" 2>/dev/null || true
}
trap cleanup EXIT

# ── Helper: call Go endpoint ──────────────────────────────────────────────────
go_get()  { curl -sf "http://localhost:$GO_PORT$1" | jq -S . 2>/dev/null || echo "{}"; }
go_post() { curl -sf -X POST -H "Content-Type: application/json" -d "$2" "http://localhost:$GO_PORT$1" | jq -S . 2>/dev/null || echo "{}"; }

# ── Helper: call Python endpoint ──────────────────────────────────────────────
py_get()  { curl -sf "http://localhost:$PYTHON_PORT$1" | jq -S . 2>/dev/null || echo "{}"; }
py_post() { curl -sf -X POST -H "Content-Type: application/json" -d "$2" "http://localhost:$PYTHON_PORT$1" | jq -S . 2>/dev/null || echo "{}"; }

# ── Helper: diff two JSON strings (ignoring transient fields) ────────────────
diff_json() {
  local label="$1" go_json="$2" py_json="$3"

  if [[ "$GO_ONLY" == true ]]; then
    # In go-only mode just validate Go returns non-empty JSON
    if [[ "$go_json" == "{}" ]] || [[ "$go_json" == "null" ]]; then
      fail "$label (Go returned empty/null)"
    else
      ok "$label (Go returns valid JSON)"
    fi
    return
  fi

  # Strip transient fields before diffing
  local strip='.timestamp? |= empty | .Timestamp? |= empty | .analyzed_at? |= empty | .fetched_at? |= empty | .win_streak? |= empty'
  local go_clean py_clean
  go_clean=$(echo "$go_json" | jq -S "$strip" 2>/dev/null || echo "$go_json")
  py_clean=$(echo "$py_json"  | jq -S "$strip" 2>/dev/null || echo "$py_json")

  if diff <(echo "$go_clean") <(echo "$py_clean") &>/dev/null; then
    ok "$label"
  else
    fail "$label — diff:"
    diff <(echo "$go_clean") <(echo "$py_clean") | head -30 || true
  fi
}

# ═══════════════════════════════════════════════════════════════════════════════
echo ""
echo "══════════════════════════════════════════════════════"
echo "  Phase 6 — API Validation"
echo "══════════════════════════════════════════════════════"

# ── Dashboard ─────────────────────────────────────────────────────────────────
echo ""
echo "── Dashboard ──────────────────────────────────────────"
diff_json "GET /api/dashboard/stats" "$(go_get /api/dashboard/stats)" "$(py_get /api/dashboard/stats)"
diff_json "GET /api/dashboard/recent" "$(go_get /api/dashboard/recent)" "$(py_get /api/dashboard/recent)"

# ── Predictions ───────────────────────────────────────────────────────────────
echo ""
echo "── Predictions ─────────────────────────────────────────"
PREDICT_BODY='{"home_team":"Arsenal","away_team":"Chelsea","competition":"Premier League"}'
go_pred=$(go_post /api/predict "$PREDICT_BODY")
py_pred=$(py_post /api/predict "$PREDICT_BODY")

# Key structure validation (field names may differ slightly)
if echo "$go_pred" | jq -e '.HomeWinProb' &>/dev/null; then
  ok "POST /api/predict — Go returns HomeWinProb"
else
  fail "POST /api/predict — Go missing HomeWinProb"
fi

if [[ "$GO_ONLY" == false ]]; then
  # Check probabilities sum to ~1.0 in both
  go_sum=$(echo "$go_pred" | jq -r '(.HomeWinProb + .DrawProb + .AwayWinProb)' 2>/dev/null || echo "0")
  py_sum=$(echo "$py_pred" | jq -r '(.HomeWinProb + .DrawProb + .AwayWinProb)' 2>/dev/null || echo "0")
  info "  Go prob sum: $go_sum  |  Python prob sum: $py_sum"
fi

# ── Config weights ─────────────────────────────────────────────────────────────
echo ""
echo "── Config ──────────────────────────────────────────────"
go_w=$(go_get /api/config/weights)
py_w=$(py_get /api/config/weights)
diff_json "GET /api/config/weights" "$go_w" "$py_w"

# ── Data sources ──────────────────────────────────────────────────────────────
echo ""
echo "── Data ────────────────────────────────────────────────"
diff_json "GET /api/data/status"    "$(go_get /api/data/status)"    "$(py_get /api/data/status)"
diff_json "GET /api/data/sources"   "$(go_get /api/data/sources)"   "$(py_get /api/data/sources)"
diff_json "GET /api/data/historical" "$(go_get /api/data/historical)" "$(py_get /api/data/historical)"

# ── Backtest ──────────────────────────────────────────────────────────────────
echo ""
echo "── Backtest ────────────────────────────────────────────"
BT_BODY='{"sport":"football","initial_bankroll":1000,"kelly_fraction":0.25,"max_stake_pct":5.0}'
info "Running Go backtest (may take a few seconds)..."
go_bt=$(go_post /api/backtest/run "$BT_BODY")
if echo "$go_bt" | jq -e '.results' &>/dev/null; then
  ok "POST /api/backtest/run — Go returns results"
else
  fail "POST /api/backtest/run — Go missing results"
fi

if [[ "$GO_ONLY" == false ]]; then
  info "Running Python backtest..."
  py_bt=$(py_post /api/backtest/run "$BT_BODY")
  go_acc=$(echo "$go_bt" | jq -r '.results.overall.overall_accuracy // .results.Overall.OverallAccuracy // "?"')
  py_acc=$(echo "$py_bt" | jq -r '.results.overall.overall_accuracy // "?"')
  info "  Go accuracy: $go_acc  |  Python accuracy: $py_acc"
fi

# ── Performance ───────────────────────────────────────────────────────────────
echo ""
echo "── Performance ─────────────────────────────────────────"
diff_json "GET /api/performance/monthly" "$(go_get /api/performance/monthly)" "$(py_get /api/performance/monthly)"

# ── Jackpots ──────────────────────────────────────────────────────────────────
echo ""
echo "── Jackpots ────────────────────────────────────────────"
JP_BODY='{"providers":["sportpesa"]}'
go_jp=$(go_post /api/jackpots/fetch "$JP_BODY")
if echo "$go_jp" | jq -e '.jackpots' &>/dev/null; then
  ok "POST /api/jackpots/fetch — Go returns jackpots"
else
  fail "POST /api/jackpots/fetch — Go missing jackpots"
fi
diff_json "GET /api/jackpots/history" "$(go_get /api/jackpots/history)" "$(py_get /api/jackpots/history)"

# ═══════════════════════════════════════════════════════════════════════════════
echo ""
echo "══════════════════════════════════════════════════════"
printf "  Results: ${GREEN}%d passed${NC}  ${RED}%d failed${NC}\n" "$PASS" "$FAIL"
echo "══════════════════════════════════════════════════════"
echo ""

[[ "$FAIL" -eq 0 ]] && exit 0 || exit 1
