#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

BIN_SRC="$REPO_DIR/bin"
SHELL_SRC="$REPO_DIR/shell"
SYSTEMD_USER_SRC="$REPO_DIR/systemd-user"

LOCAL_BIN="$HOME/.local/bin"
BASH_ALIASES="$HOME/.bash_aliases"
SYSTEMD_USER_DIR="$HOME/.config/systemd/user"

echo "[*] stupid_scripts installer"
echo "[*] repo: $REPO_DIR"

mkdir -p "$LOCAL_BIN"
mkdir -p "$SYSTEMD_USER_DIR"

echo "[*] linking scripts into ~/.local/bin"

if [ -d "$BIN_SRC" ]; then
  for f in "$BIN_SRC"/*; do
    [ -f "$f" ] || continue

    chmod +x "$f"

    name="$(basename "$f")"
    target="$LOCAL_BIN/$name"

    if [ -e "$target" ] && [ ! -L "$target" ]; then
      backup="$target.bak.$(date +%Y%m%d_%H%M%S)"
      echo "[!] $target exists and is not a symlink; backing up to $backup"
      mv "$target" "$backup"
    fi

    ln -sf "$f" "$target"
    echo "    linked $target -> $f"
  done
else
  echo "[!] no bin/ directory found"
fi

echo "[*] restoring ~/.bash_aliases"

if [ -f "$SHELL_SRC/bash_aliases" ]; then
  if [ -e "$BASH_ALIASES" ] && [ ! -L "$BASH_ALIASES" ]; then
    backup="$BASH_ALIASES.bak.$(date +%Y%m%d_%H%M%S)"
    echo "[!] ~/.bash_aliases exists and is not a symlink; backing up to $backup"
    mv "$BASH_ALIASES" "$backup"
  fi

  ln -sf "$SHELL_SRC/bash_aliases" "$BASH_ALIASES"
  echo "    linked $BASH_ALIASES -> $SHELL_SRC/bash_aliases"
else
  echo "[!] no shell/bash_aliases found"
fi

echo "[*] checking ~/.local/bin PATH"

case ":$PATH:" in
  *":$HOME/.local/bin:"*)
    echo "    ~/.local/bin is already in current PATH"
    ;;
  *)
    echo "[!] ~/.local/bin is not in current PATH"
    echo "    Add this to ~/.bashrc or ~/.profile:"
    echo '    export PATH="$HOME/.local/bin:$PATH"'
    ;;
esac

echo "[*] linking user systemd units, if any"

if [ -d "$SYSTEMD_USER_SRC" ]; then
  for f in "$SYSTEMD_USER_SRC"/*; do
    [ -f "$f" ] || continue

    name="$(basename "$f")"
    target="$SYSTEMD_USER_DIR/$name"

    if [ -e "$target" ] && [ ! -L "$target" ]; then
      backup="$target.bak.$(date +%Y%m%d_%H%M%S)"
      echo "[!] $target exists and is not a symlink; backing up to $backup"
      mv "$target" "$backup"
    fi

    ln -sf "$f" "$target"
    echo "    linked $target -> $f"
  done

  systemctl --user daemon-reload || true
else
  echo "    no systemd-user/ directory found"
fi

echo "[*] verification"

echo "    ~/.local/bin:"
ls -l "$LOCAL_BIN" | grep "$REPO_DIR" || true

echo
echo "    ~/.bash_aliases:"
ls -l "$BASH_ALIASES" || true

echo
echo "[*] done"
echo
echo "Next steps:"
echo "  source ~/.bashrc"
echo "  command -v toggle-audio"
echo "  command -v gnome-status-line"
