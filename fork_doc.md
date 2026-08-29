# Fork intent — Print / Print Preview engine fix

## Start here (handoff summary)

**What this is:** a personal fork of [retext-project/retext](https://github.com/retext-project/retext),
maintained at [tkchan007/retext](https://github.com/tkchan007/retext) (GitHub account
tkchan007), cloned locally at `~/dev/retext`. `origin` = the fork, `upstream` =
the real project. Built to fix broken Print/Print Preview rendering, then grew
into a small print-layout feature set (see below).

**How to run it** (points Python at this checkout instead of the system-installed
`retext` package):
```bash
PYTHONPATH=~/dev/retext python3 -m ReText [optional-file-to-open]
```
If an instance is already running, a new launch just hands the file to it
instead of loading fresh code — kill the existing PID first (`pgrep -af
"python3 -m ReText"`, then `kill <pid>`, **not** `pkill -f "python3 -m
ReText"`, which matches its own wrapping shell command and kills the wrong
thing) before relaunching after any code change.

**To run this in place of the system-installed `retext` package** (so the
normal `retext` command, and GUI launchers/"Open With", use this checkout):
```bash
./install/setup-user-launcher.sh
```
Installs a `~/.local/bin/retext` wrapper (ahead of `/usr/bin/retext` on
`PATH`) plus a user-level `.desktop` file that shadows the system one --
both user-level only, no sudo, safe to re-run after moving the checkout.
**Leave the system `retext` apt package installed** even though it becomes
unused: this fork doesn't vendor PyQt6/WebEngine/the `markups` library, it
reuses the system copies that the `retext` package pulled in as
dependencies. Confirmed via `apt-get remove -s retext` that those
dependencies are marked "no longer required" the moment the package is
removed -- a later `apt autoremove` would then silently take them (and
this fork) down with it. On a machine that's never had `retext` installed,
run `sudo apt install retext` first (for the dependencies), *then* the
setup script above.

**After running the setup script, verify `~/.local/bin` is actually on
`PATH` in a real new terminal** (not just a login shell) before assuming
`retext` resolves to this fork:
```bash
grep "local/bin" ~/.bashrc
```
Ubuntu's default `~/.profile` adds `~/.local/bin` to `PATH`, but `~/.profile`
is only sourced by *login* shells -- most terminal windows start plain
interactive shells that source `~/.bashrc` instead, which does **not**
have the same logic by default. Hit this exact issue during setup: `retext`
silently resolved to the system package in a normal new terminal despite
the wrapper being installed correctly, with no error to indicate why. If
the grep above comes back empty, append this to `~/.bashrc`:
```bash
if [ -d "$HOME/.local/bin" ] ; then
    PATH="$HOME/.local/bin:$PATH"
fi
```

**One-time setup needed on a fresh checkout/session:** WebEngine rendering
(everything below depends on it) is off by default and there's no config
file yet on a fresh profile. Turn it on via **Edit > Use WebEngine (Chromium)
renderer**, then close and reopen any already-open file (the preview widget
type is decided once, at tab-creation time).

**Status as of last session:** all of the below is implemented and the user
confirmed it works — print/print-preview rendering fixed, and the print
preset system (margins + font) tested with multiple presets, switching
correctly between them. Nothing currently broken/pending investigation.

**What's deliberately not built yet** (see bottom sections for why, and why
retrofitting each is expected to be cheap when the time comes):
- Page size per preset (Letter/A4/A3/ANSI B/etc.) — user wants this, plumbing
  already confirmed to exist (`getPageSizeByName()`), just not wired to
  presets yet.
- Poster-size / large-format output — raised as a "would be valuable"
  aside, not scoped or designed yet. Two different possible features:
  genuinely oversized page dimensions vs. tiling one layout across
  multiple sheets.
- Drag-to-resize visual margin editor — current UI uses plain numeric
  spin-boxes; dragging is a pure UI layer on the same stored values,
  deferred as a follow-up polish pass.
- Not upstreamed anywhere, not intended to be without revisiting the `lp`/
  CUPS-only assumption (see "Known limitation" below) — this is a personal
  fork for one Linux machine.

**Everything below this point is the detailed design rationale/history** —
read it if you need to understand *why* something works the way it does,
not just *what* to do next.

---

This is a personal fork of [retext-project/retext](https://github.com/retext-project/retext),
maintained at [tkchan007/retext](https://github.com/tkchan007/retext), created to fix a
specific bug: **Print** and **Print Preview** render incorrectly compared to the live
preview pane and **Export to PDF**.

## The bug

ReText has two independent HTML rendering paths:

- The live preview pane and **Export to PDF** (`savePdf()`, when
  `globalSettings.useWebEngine` is true) render through `QWebEngineView` /
  `QWebEnginePage.printToPdf()` — a full Chromium-based renderer. This renders
  correctly.
- **Print** (`printFile()`) and **Print Preview** (`printPreview()`) always build a
  `QTextDocument` from the converted HTML (via `getDocumentForPrint()` /
  `textDocument()`) and call `document.print(printer)`, regardless of
  `globalSettings.useWebEngine`. `QTextDocument` only supports a limited HTML/CSS
  subset and mis-renders this content — observed symptom: the document's title
  (first `<h1>`) and intro paragraph disappear, replaced by a large blank gap at
  the top of the first page.

Confirmed via source inspection (`window.py`) and by reproducing the converted HTML
directly through the `markups` library — the HTML/CSS generation itself is correct;
the divergence is purely in which Qt rendering path `printFile()`/`printPreview()`
use versus `savePdf()`.

## Why not just point Print/Preview at `QWebEngineView.print()` directly

`QWebEngineView.print(printer)` exists (confirmed present in the installed
PyQt6 6.10.2 / Qt 6.10.2) and would fix direct Print on its own. But if Print and
Print Preview each independently re-render the page (one via `.print()`, the other
via a separate `printToPdf()`-then-view call), nothing guarantees the two stay in
sync — different QPrinter/QPageLayout state, timing, etc. could make "what you
previewed" diverge from "what actually printed."

Native Qt `QPrintPreviewDialog` also can't be wired to WebEngine at all:
`QPrintPreviewDialog` requires a synchronous `paintRequested` callback, and
WebEngine's printing is inherently asynchronous (a separate Chromium process
under the hood). This is a Qt architecture limitation, not a ReText bug — no
fork can make native Print Preview + WebEngine cooperate directly.

## The fix: single render path, shared by both actions

Both **Print** and **Print Preview** now render to the *same* temporary PDF via
the already-correct `QWebEngineView.page().printToPdf()` path (the same one
`savePdf()` uses), then:

- **Print Preview** opens that temp PDF in the system's default PDF viewer.
- **Print** hands that *same* PDF file straight to CUPS via `lp -d <printer>
  <copies> <path>`, using the printer/copy-count chosen in the native
  `QPrintDialog` — rather than re-rendering anything.

Because both actions consume one generated file, "what you previewed" and
"what gets printed" are guaranteed identical by construction, not by hoping two
separate renders happen to agree.

The old `QTextDocument`-based path is kept as a fallback for the case where
`globalSettings.useWebEngine` is false (WebEngine not installed/available) —
matching the existing precedent already established in `savePdf()`, so
behavior doesn't regress for that configuration.

## Known limitation of this approach

`lp` is a CUPS command — this fix assumes a CUPS-based Linux (or macOS)
environment. It is not portable to Windows as-is. Since this fork is scoped
to a personal Linux setup, that's an acceptable trade-off here; it would need
revisiting before proposing this upstream.

## Status

- [x] Forked to tkchan007/retext, cloned to `~/dev/retext`
- [x] Implement shared `renderPreviewToPdf()` helper
- [x] Rewrite `printFile()` to use the shared helper + `lp`
- [x] Rewrite `printPreview()` to use the shared helper + open-in-viewer
- [x] Manual test: print and preview the same worksheet, confirm title/spacing
      render correctly and match each other -- **confirmed working**

## Follow-up bug found during testing: blank Print Preview

First real test showed a blank page. Root cause: `previewBox` (the shared
live-preview WebEngine widget the original `renderPreviewToPdf()` rendered
from) is populated *asynchronously* — a 500ms debounce timer plus a separate
conversion subprocess — and may never be populated at all if the live
preview pane has never been shown for a tab (a fresh tab defaults to
`previewState=PreviewDisabled`, under which `triggerPreviewUpdate()` is a
no-op). Calling `printToPdf()` on an unpopulated page produces a real, valid,
but empty PDF.

Fixed by decoupling the print pipeline from `previewBox` entirely:
`renderHtmlToPdf()` now renders fresh HTML (from the already-synchronous
`getDocumentForExport()`) into a private, invisible `QWebEnginePage` created
just for that render, waiting on `loadFinished` before calling
`printToPdf()`. No dependency on the live preview's state or timing at all.
`savePdf()` (Export to PDF) was also switched onto this same path, since it
had the identical latent bug (and had never actually been exercised before,
see below).

## Follow-up: `useWebEngine` defaults to false

Discovered while debugging the blank-preview bug: `globalSettings.useWebEngine`
defaults to `False` in stock ReText, and is only ever turned on by explicitly
checking Edit > "Use WebEngine (Chromium) renderer" (or having a config file
that already has it saved true). With no config file, WebEngine rendering
was never active for this install — meaning the live preview pane, and
`savePdf()`'s WebEngine branch, had *also* never actually been exercised
before this fork's work started, despite the original bug report only being
about Print/Print Preview. Toggling that setting is required before any of
this fork's fixes have anything to act on.

## Feature: per-document print font (compact printing)

Requested as a follow-up: a way to make printed/exported output more compact
(smaller font) to fit more on a page, independent of the live preview's own
font setting.

Initial version added a single global `printFont` setting + `Edit > Change
print font`, injecting a `font-family`/`font-size` override into `<head>`
via `buildPrintHtml()` (CSS override, not a `QTextDocument` font — this
whole pipeline is WebEngine-only). Confirmed via source inspection that
nothing in the generated HTML/stylesheet sets an explicit body font, so a
plain `html, body { font-family: ...; font-size: ...pt }` override
reliably takes effect without fighting existing CSS.

This was superseded by the preset system below before shipping as a
standalone feature — see `ReText/printpresets.py` history is this file, not
git history, since presets replaced the single global setting outright.

## Feature: named print layout presets (margins + print font)

Requested as a bigger follow-up: rather than one global margin/font setting,
support any number of named, independently-editable presets (e.g. one for a
tall skinny worksheet, another for a dense reference doc), switchable
per-print-job, addable over time with no cap.

**Storage** (`ReText/printpresets.py`): one small JSON file per preset,
under `<config dir>/print-presets/`, filename = a generated id (not the
name, so renaming never requires a rename-on-disk). Schema:
```json
{"name": str, "unit": "in", "marginTop": float, "marginBottom": float,
 "marginLeft": float, "marginRight": float, "printFont": str}
```
`printFont` is a `QFont.toString()` descriptor, `""` meaning no override.
`unit` is always `"in"` for now (only unit supported); deliberately present
in the schema so adding `"mm"` later doesn't require a migration.
`pageSize` is deliberately **not** in this schema yet (see below).

**Active preset**: tracked via `globalSettings.activePrintPresetId` (a
preset's generated id, or `''` meaning "no custom preset -- use built-in
`DEFAULT_PRESET`", which reproduces ReText's original hardcoded margins of
20mm/20mm/13mm/20mm, converted to inches).

**UI** (`ReText/printpresetdialog.py`, `PrintPresetDialog`, opened via
`Edit > Print layout presets...`): a list of presets (with the built-in
default always pinned as the first, non-editable row) alongside a form for
margins (4 spin-boxes, inches) and print font (a button opening the same
`QFontDialog` pattern as the old single-setting version). Selecting a row
in the list immediately makes it the active preset; editing its fields only
takes effect on Save. New/Rename/Delete round out preset management.

**Rendering** (`window.py`): `getActivePrintPreset()` loads the active
preset (or falls back to `DEFAULT_PRESET` if none is set or the file is
gone). `buildPrintHtml()` reads its `printFont`; `renderHtmlToPdf()` reads
its four margins directly as `QPageLayout.Unit.Inch` (no mm conversion
needed, since presets are already stored in inches).

### Deferred: page size per preset

Discussed and deliberately deferred, not because it's hard -- confirmed via
`getPageSizeByName()` (already in `window.py`, mapping name strings onto
`QPageSize.PageSizeId`, which already covers Letter/A4/A3/Legal/ANSI B-E/ISO
B-series) that the underlying plumbing already exists. Adding it later is
purely additive: one more optional key in the preset schema (missing =
fall back to `globalSettings.paperSize`, so old presets keep working
unmodified), one more dropdown in the dialog, one line changed in
`renderHtmlToPdf()`. No retrofit cost was found to justify doing it now.

Also noted for whenever page size lands: real interest in poster-size
output (hang-on-a-wall large format), which is really two distinct
features to consider then -- genuinely oversized page dimensions (for
sending to a large-format print service), and/or a "poster mode" that tiles
one big layout across multiple standard sheets to tape together.

### Deferred: drag-to-resize visual margin editor

Requested, then deliberately deferred in favor of plain numeric spin-boxes
for this first version, since the drag interaction is a pure UI layer over
the same four stored values -- it doesn't touch the preset data model or
storage at all, so it can be added later without redoing anything here.
