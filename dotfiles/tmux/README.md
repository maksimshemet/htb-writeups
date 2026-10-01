# tmux config — pentest / OSCP setup

My tmux setup for HTB/OSCP work. The headline feature is **automatic per-pane session logging with
archive-on-close**: the moment any window or pane opens, its full transcript starts writing to
`~/pentest-logs/` with per-line timecodes — no manual toggle — and when the session ends its logs
are tar.gz'd and the raw files removed.

| File | Purpose |
|------|---------|
| [`tmux.conf`](tmux.conf) | The config → copy to `~/.tmux.conf` |
| [`tmux-log.sh`](tmux-log.sh) | Logging + archive helper the hooks/keybind call → copy to `~/.tmux/tmux-log.sh` |

## Prefix

Remapped to **`Alt-a`** (not the default `Ctrl-b`). All tmux keys are "prefix then key" — e.g. a
split is `Alt-a` then `|`. Press `Alt-a` twice to send a literal `Alt-a` to the shell. Change it in
`tmux.conf` under the `# ── Prefix ──` block.

## Install (Kali)

```bash
sudo apt install -y moreutils xclip          # ts (timecodes) + clipboard
mkdir -p ~/.tmux ~/pentest-logs
cp tmux.conf        ~/.tmux.conf
cp tmux-log.sh      ~/.tmux/tmux-log.sh
chmod +x            ~/.tmux/tmux-log.sh

# plugins (optional — for the on-demand tmux-logging keys)
git clone https://github.com/tmux-plugins/tpm ~/.tmux/plugins/tpm

# engage it — hooks only apply to NEW panes, so start fresh
tmux kill-server 2>/dev/null
tmux            # inside: prefix + I to install plugins
```

## How the logging works

- Hooks in `tmux.conf` run `tmux-log.sh` against each new pane and on session close.
- Each **session gets its own directory** `~/pentest-logs/<session>_<date>-<time>/`, and every pane
  `pipe-pane`s to its own file inside it:

  ```
  ~/pentest-logs/boxA_20261001-104540/
                 ├─ w0p0_104540.log      ← window 0, pane 0
                 ├─ w1p0_104540.log      ← window 1, pane 0
                 └─ .sid                 ← tmux session id (for the sweep)
  ```

- With `moreutils` installed, every line is prefixed `[2026-10-01 10:45:40.123456]`. Without it,
  the log is captured raw and a one-line warning is written at the top.
- **One file per pane** on purpose — concurrent panes writing to a shared file corrupt each other.
  Search across a box's logs with `grep -r ~/pentest-logs`.
- Set `TMUX_LOGDIR` to log somewhere else (default `~/pentest-logs`).

## Archive on session end

When a session ends, its directory is tar.gz'd to `~/pentest-logs/<session>_<date>-<time>.tar.gz`
and the raw directory is removed. Two triggers make this reliable:

- **`session-closed` hook** — archives a session the instant it closes. tmux does *not* run this
  hook for the **last** session (the server exits first), so…
- **sweep on `session-created`** — each time a session starts, any leftover log dir whose session
  is no longer alive gets archived. This mops up the previous run's last session automatically.

So the only gap is: the very last session's logs stay as a raw dir until you next start tmux, then
they're archived. To archive-and-close immediately instead:

- **`prefix` + `E`** — flush, archive this session's logs, and kill the session (works even when
  it's the only one). Confirms first.

Manually sweep orphans anytime: `~/.tmux/tmux-log.sh sweep`.

### Reading the logs

Logs are raw (ANSI colour codes included, same as `script`). Strip them when reading/grepping:

```bash
export LC_ALL=C
sed 's/\x1b\[[0-9;?]*[a-zA-Z]//g; s/\r/\n/g' <logfile>
```

## Notes

- **Fresh session required.** Hooks fire only for panes created after the config loads; reloading
  into a running session won't retroactively log existing panes. `tmux kill-server` first.
- **Clipboard.** The mouse-drag copy bindings use `xclip` (X11, e.g. Kali Xfce). On a Wayland
  desktop, replace `xclip -selection clipboard -in` with `wl-copy`. Or hold **Shift** while
  dragging to use the terminal's native selection instead of tmux.
- **Complements `script -T`.** Keep using a per-box `script -T` timed capture for replay/speed
  review; this is the always-on, every-pane backstop.
- Tested against tmux 3.7c. The same setup is mirrored in my Obsidian vault's tmux cheat sheet.
