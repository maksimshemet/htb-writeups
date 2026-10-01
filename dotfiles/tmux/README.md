# tmux config — pentest / OSCP setup

My tmux setup for HTB/OSCP work. The headline feature is **automatic per-pane session logging**:
the moment any window or pane opens, its full transcript starts writing to `~/pentest-logs/` with
per-line timecodes — no manual toggle, so a box is never lost to "forgot to start logging."

| File | Purpose |
|------|---------|
| [`tmux.conf`](tmux.conf) | The config → copy to `~/.tmux.conf` |
| [`log-pane.sh`](log-pane.sh) | Logging helper the hooks call → copy to `~/.tmux/log-pane.sh` |

## Prefix

Remapped to **`Alt-a`** (not the default `Ctrl-b`). All tmux keys are "prefix then key" — e.g. a
split is `Alt-a` then `|`. Press `Alt-a` twice to send a literal `Alt-a` to the shell. Change it in
`tmux.conf` under the `# ── Prefix ──` block.

## Install (Kali)

```bash
sudo apt install -y moreutils xclip          # ts (timecodes) + clipboard
mkdir -p ~/.tmux ~/pentest-logs
cp tmux.conf        ~/.tmux.conf
cp log-pane.sh      ~/.tmux/log-pane.sh
chmod +x            ~/.tmux/log-pane.sh

# plugins (optional — for the on-demand tmux-logging keys)
git clone https://github.com/tmux-plugins/tpm ~/.tmux/plugins/tpm

# engage it — hooks only apply to NEW panes, so start fresh
tmux kill-server 2>/dev/null
tmux            # inside: prefix + I to install plugins
```

## How the logging works

- Three hooks in `tmux.conf` (`session-created`, `after-new-window`, `after-split-window`) run
  `log-pane.sh` against each new pane.
- The script `pipe-pane`s that pane to its own file in `~/pentest-logs/`:

  ```
  ~/pentest-logs/20261001-102858_main_w1p0.log
                 └date──┘ └time┘ │sess│ └win/pane┘
  ```

- With `moreutils` installed, every line is prefixed `[2026-10-01 10:28:58.123456]`. Without it,
  the log is still captured raw and a one-line warning is written at the top.
- **One file per pane** on purpose — concurrent panes writing to a shared file corrupt each other.
  Search across a box's logs with `grep -r ~/pentest-logs`.
- Set `TMUX_LOGDIR` to log somewhere else.

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
