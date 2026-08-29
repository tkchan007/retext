#!/bin/sh
# Sets up this checkout to run in place of the system-installed `retext`
# package, for the current user only -- no sudo, nothing system-owned is
# touched. Safe to re-run any time (e.g. after moving the checkout).
#
# What it does:
#   1. Installs a ~/.local/bin/retext wrapper that runs THIS checkout
#      (via PYTHONPATH) instead of the system package.
#   2. Installs a user-level .desktop file that shadows the system one,
#      so GUI launchers / "Open With" / file associations use it too.
#
# What it deliberately does NOT do: install the retext apt package or its
# dependencies (PyQt6, WebEngine, the markups library, etc.) -- this fork
# reuses those from the system rather than vendoring them. On a machine
# that has never had `retext` installed, run this FIRST:
#   sudo apt install retext
# then run this script. See fork_doc.md for why the system package should
# be left installed even though it's unused -- removing it risks an
# `apt autoremove` later silently taking its (still-needed) dependencies
# down with it.

set -e

repoRoot=$(cd "$(dirname "$0")/.." && pwd)

if ! python3 -c "import markups" >/dev/null 2>&1; then
    echo "warning: the 'markups' Python module isn't importable yet." >&2
    echo "Run 'sudo apt install retext' first to pull in this fork's" >&2
    echo "runtime dependencies (PyQt6, WebEngine, markups, etc.), then" >&2
    echo "re-run this script." >&2
fi

mkdir -p "$HOME/.local/bin"
wrapperPath="$HOME/.local/bin/retext"
cat > "$wrapperPath" <<EOF
#!/bin/sh
# Launches the ReText fork checked out at $repoRoot
# instead of the system-installed retext package.
exec env PYTHONPATH="$repoRoot" python3 -m ReText "\$@"
EOF
chmod +x "$wrapperPath"
echo "Installed $wrapperPath"

mkdir -p "$HOME/.local/share/applications"
desktopPath="$HOME/.local/share/applications/me.mitya57.ReText.desktop"
cat > "$desktopPath" <<EOF
[Desktop Entry]
Version=1.0
Name=ReText
Comment=Simple text editor for Markdown and reStructuredText (personal fork)
Categories=Office;WordProcessor;
Exec=$wrapperPath %F
Type=Application
Icon=retext
StartupWMClass=ReText
MimeType=text/markdown;text/x-rst;
Keywords=Text;Editor;Markdown;reStructuredText;
EOF
echo "Installed $desktopPath"

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$HOME/.local/share/applications" >/dev/null 2>&1 || true
fi

case ":$PATH:" in
    *":$HOME/.local/bin:"*)
        echo "Done -- open a new terminal (or 'source ~/.profile') and run: retext"
        ;;
    *)
        echo "Done. Note: ~/.local/bin isn't on PATH in this shell yet --"
        echo "open a NEW terminal (Ubuntu's default ~/.profile adds it" \
             "automatically once the directory exists) and run: retext"
        ;;
esac
