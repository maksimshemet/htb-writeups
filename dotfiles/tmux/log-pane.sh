#!/usr/bin/env bash
# Start a timestamped transcript for the tmux pane given as $1 (a #{pane_id}).
# Called from tmux hooks in tmux.conf; idempotent (skips a pane already logging).
#
# Logs to $TMUX_LOGDIR (default ~/pentest-logs), one file per pane:
#   <date>-<time>_<session>_w<window>p<pane>.log
# Per-line [timestamp] prefixes need moreutils (`ts`); without it, logs raw.
pane="${1:?pane id required}"
logdir="${TMUX_LOGDIR:-$HOME/pentest-logs}"
mkdir -p "$logdir"

# already piping? don't double-log
[ "$(tmux display-message -p -t "$pane" '#{pane_pipe}')" = "1" ] && exit 0

read -r sess win pidx <<EOF
$(tmux display-message -p -t "$pane" '#{session_name} #{window_index} #{pane_index}')
EOF
file="$logdir/$(date +%Y%m%d-%H%M%S)_${sess}_w${win}p${pidx}.log"

printf '\n==== tmux log start %s | session=%s window=%s pane=%s ====\n' \
  "$(date '+%F %T %Z')" "$sess" "$win" "$pidx" >> "$file"

if command -v ts >/dev/null 2>&1; then
  tmux pipe-pane -t "$pane" -o "ts '[%Y-%m-%d %H:%M:%.S] ' >> '$file'"
else
  printf '[warn] install moreutils for per-line timecodes (sudo apt install moreutils)\n' >> "$file"
  tmux pipe-pane -t "$pane" -o "cat >> '$file'"
fi
