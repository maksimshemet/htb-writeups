#!/usr/bin/env bash
# Unified tmux logging helper (called from hooks/keybinding in tmux.conf).
#   start <session_id> <pane_id>   on session-created: sweep orphans + log first pane
#   pane  <session_id> <pane_id>   on new window/split: log that pane
#   close <session_id>             on session-closed: archive + remove that session's dir
#   endkill <session_id>           keybinding: flush + archive + kill session (works for last one)
#   sweep                          archive dirs whose session is no longer alive
base="${TMUX_LOGDIR:-$HOME/pentest-logs}"
mkdir -p "$base/.index"

sid_digits() { printf '%s' "$1" | tr -cd '0-9'; }

dir_for() {  # look up (or create) the log dir for a session id
  local sid="$1" idx name ts dir
  idx="$base/.index/$(sid_digits "$sid")"
  if [ -f "$idx" ]; then cat "$idx"; return; fi
  name="$(tmux display-message -p -t "$sid" '#{session_name}' 2>/dev/null)"; : "${name:=session}"
  ts="$(date +%Y%m%d-%H%M%S)"
  dir="$base/${name}_${ts}"
  mkdir -p "$dir"
  printf '%s\n' "$dir" > "$idx"
  printf '%s\n' "$sid" > "$dir/.sid"
  printf '%s\n' "$dir"
}

start_pane() {
  local sid="$1" pane="$2" dir win pidx file
  dir="$(dir_for "$sid")"
  [ "$(tmux display-message -p -t "$pane" '#{pane_pipe}' 2>/dev/null)" = "1" ] && return 0
  read -r win pidx <<EOF
$(tmux display-message -p -t "$pane" '#{window_index} #{pane_index}' 2>/dev/null)
EOF
  file="$dir/w${win}p${pidx}_$(date +%H%M%S).log"
  printf '\n==== log start %s | pane=%s ====\n' "$(date '+%F %T %Z')" "$pane" >> "$file"
  if command -v ts >/dev/null 2>&1; then
    tmux pipe-pane -t "$pane" -o "ts '[%Y-%m-%d %H:%M:%.S] ' >> '$file'"
  else
    tmux pipe-pane -t "$pane" -o "cat >> '$file'"
  fi
}

archive_dir() {
  local dir="$1" base_name
  [ -d "$dir" ] || return 0
  base_name="$(basename "$dir")"
  tar czf "${dir}.tar.gz" -C "$base" "$base_name" 2>/dev/null && rm -rf "$dir"
}

close_session() {
  local sid="$1" idx dir
  idx="$base/.index/$(sid_digits "$sid")"
  [ -f "$idx" ] || return 0
  dir="$(cat "$idx")"
  archive_dir "$dir"
  rm -f "$idx"
}

sweep_orphans() {
  local alive idx dir sid
  alive=" $(tmux list-sessions -F '#{session_id}' 2>/dev/null | tr '\n' ' ') "
  for idx in "$base"/.index/*; do
    [ -e "$idx" ] || continue
    dir="$(cat "$idx")"
    sid="$(cat "$dir/.sid" 2>/dev/null)"
    if [ -n "$sid" ] && printf '%s' "$alive" | grep -qF " $sid "; then
      continue   # session still alive
    fi
    archive_dir "$dir"; rm -f "$idx"
  done
}

endkill() {
  local sid="$1" p
  for p in $(tmux list-panes -s -t "$sid" -F '#{pane_id}' 2>/dev/null); do
    tmux pipe-pane -t "$p"   # toggle logging off → flush & close file
  done
  close_session "$sid"
  tmux kill-session -t "$sid" 2>/dev/null
}

case "${1:-}" in
  start)   sweep_orphans; start_pane "$2" "$3" ;;
  pane)    start_pane "$2" "$3" ;;
  close)   close_session "$2" ;;
  endkill) endkill "$2" ;;
  sweep)   sweep_orphans ;;
  *) echo "usage: $0 {start|pane|close|endkill|sweep} ..." >&2; exit 2 ;;
esac
