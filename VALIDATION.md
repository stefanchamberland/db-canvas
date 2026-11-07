# Validation

Validated on macOS on 2026-11-07 (America/Toronto):

- Ten Python tests passed, including silent-video exports and transparent-logo compositing; the local HTTP workflow tests passed with loopback access enabled.
- Node.js interface logic checks passed.
- Real test media exported as four JPEG slides and one 1080×1350 MP4. Decoded motion, transparent logo compositing, black video background, and portable project reopening were checked. Composition previews were visually inspected.
- Fixed FFmpeg input ordering for silent clips and preserved PNG transparency in rendering, video overlays, browser previews, and HTTP posters.
- Full interactive browser testing and native launcher testing remain outstanding. Local test assets and generated deliverables are excluded from Git.

Validated in the Linux development runtime on 2026-11-06 (America/Toronto).

- Eight Python tests passed. They exercise real Pillow renders and FFmpeg video/audio exports, source continuity across seams, portable project save/move/reopen, Reel concatenation, no-overwrite export behavior, and the actual HTTP import → arrange → save → reopen → export path. The local API token, HTTP byte-range media delivery, and ZIP path validation were also exercised.
- Node.js interface logic smoke test passed with no third-party dependencies. It checks all referenced element IDs, text editing, frame settings, undo/redo, duplicate/delete, sparse per-scene duration data, pointer dragging, and media-ID deduplication. This is a small DOM adapter test, not a visual browser test.
- JavaScript syntax and Python compilation checks passed.
- The local server starts and serves the interface on loopback.

Not verified here: an actual graphical browser session, Safari-specific media behavior, launching the scripts on macOS/Windows, or posting the exported files through a real Instagram account. The browser needed for visual automation was not installed, and its attempted download failed in this environment. The macOS launcher and Windows launcher are provided as source scripts, not signed native installers.

Run Python tests with `python -m unittest discover -s tests -v`. Optionally run interface logic checks with `node tests/test_ui.js`; Node is not needed to use the app.
