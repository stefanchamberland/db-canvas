# _dB Canvas — Project Context

## Goal
Build a simple, portable local web app for designing Instagram photo, video, and mixed-media posts. It should feel like a minimal SCRL-style editor.

Owner: Stef / Decibel Peak.
Mac project location: `_dB Ops/Software Dev/db-canvas`.
Confirm the absolute path before editing.

## Current implementation
- Vanilla HTML/CSS/JavaScript GUI: `index.html`
- Local Python HTTP server: `server.py`
- Pillow + FFmpeg rendering/export engine: `engine.py`
- Python dependency: Pillow (`requirements.txt`)
- FFmpeg and ffprobe required for video.
- No Node build, cloud service, account, or publishing integration.
- Media stays local.

Launch from the project directory:
    bash Launch.command

This opens the browser. Keep Terminal running.
A separate `_dB Canvas.app` shortcut launches the same command.

## Features implemented
- Continuous canvas with visible slide boundaries.
- Photo/video import and drag-and-drop placement.
- Move and resize frames across slide boundaries.
- Frame borders, background color, contain/cover fitting, crop focus.
- Simple location stickers/text.
- Layer ordering, duplicate/delete, undo/redo.
- Automatic starting layouts: Seamless, Frames, Full bleed.
- Video trim in/out, loop, export volume.
- Scene durations and silent browser video preview.
- Optional soundtrack.
- Portable project ZIP save/reopen, including original assets.

## Formats and exports
- Carousel: up to 20 numbered JPEG/MP4 slides.
- Single post: one JPEG or MP4.
- Reel: scenes combined into one MP4.
- Stories: separate scene MP4s.
- Presets: 4:5, 1:1, 3:4, 1.91:1, 16:9, 9:16.
- Custom even dimensions supported.
- Video exports: H.264/AAC, 30 fps.
- Soundtrack converts all slides to MP4.
- Export includes optional cover.jpg and export.json.
- Outputs also remain under workspace/exports.

## Design preferences
- Minimal, photography-first layouts.
- Warm neutral backgrounds and simple photo frames.
- Location labels per section, not every image.
- Preserve original photo proportions where practical.
- Let strong photos span multiple slides.
- Mix large anchor images with smaller supporting frames.
- Original reference carousel: Atlantic Canada travel photographs.
- Moon spread across two slides; bridge finale across three.
- Halifax/Charlottetown skyline photos: 16:9, upper-half placement.
- Basilica should dominate its section; spire is a small complement.
- Current GUI uses charcoal panels and muted green accents.

## Important limitations
- Automatic layouts are deterministic starting points, not AI art direction.
- Instagram does not synchronize videos across carousel swipes.
- Browser preview is silent; audio mixing happens during export.
- Unsupported browser video codecs may show only a poster.
- No transitions/keyframes, automatic captions, licensed music,
  interactive Instagram stickers, or direct publishing.
- Unsaved edits are in browser memory; save a project ZIP before leaving.
- Instagram limits vary by publishing method; avoid treating every
  available canvas preset as universally accepted.

## Validation
- Eight Python tests passed for rendering/export, continuous seams,
  portable projects, real video/audio, Reel concatenation, and HTTP workflows.
- Node interface logic smoke test passed.
- Python compilation and JavaScript syntax checks passed.
- Full visual browser testing and native Mac launcher testing were NOT
  completed in the original environment.
- See VALIDATION.md for details.

Run checks:
    python -m unittest discover -s tests -v
    node tests/test_ui.js

Node is only needed for the optional interface logic test.

## Next steps
Run the app on Stef’s Mac and test the actual browser experience with
real photos/videos. Fix observed usability/export issues before adding
complexity. Keep launching, editing, saving, and exporting simple.

The original build environment could not access the actual Mac folder;
Stef downloaded and extracted the project there manually. Work from the
local installed files, preserving existing workspace data and projects.

## Test-media composition — 2026-11-07
- Test assets are in `test media/`, numbered 0–4 plus `ref.jpg`.
- Created five-slide 1080×1350 composition in `workspace/test-runs/20261107-170307/`.
- Starts with `0 - Final.jpg`; #1 uses original photo with ref.jpg as a bottom-right picture-in-picture; #2 uses the landscape MOV instead of its PNG; #3 and #4 follow.
- Preserved all source aspect ratios with contain fitting and neutral margins. Video uses its full 9.765 seconds.
- Editable portable ZIP: `test-media-project.zip`; export ZIP: `test-media-export.zip`; visual overview: `preview.jpg`. Export names are 01–05 (source numbering is 0–4).
- Real silent MOV exposed FFmpeg input/output option ordering bug. Fixed engine.py so silent audio input precedes -map; added silent-video regression test.
- Nine Python tests and Node UI logic checks passed on Mac. Real media exported as four JPEGs + one 1080×1350 H.264/AAC MP4; decoded motion and source aspect ratios checked; portable project reload passed. Preview visually inspected. Native browser interaction still not tested.


## Revised branded composition — 2026-11-07
- Latest project: `workspace/test-runs/20261107-171018/`. ZIPs: `decibel-peak-project.zip` and `decibel-peak-export.zip`; overview: `preview.jpg`.
- Uses updated `0 - Final.jpg`, full-bleed 4:5 photos (proportional crop, no stretching), reference PIP at top left on #1, and small 78px Decibel Peak circle logos at bottom right on every slide.
- #0 has no step label; #1–4 labeled Original, LUT Bakery, LUT, Edit.
- #2 retains the full landscape MOV over a full-bleed final-photo background to avoid cropping its interface or adding blank margins.
- Added transparent image support to engine rendering, video overlay tiles, HTTP posters and browser canvas backgrounds. Transparent logo no longer gets a square backing.
- Ten Python tests and UI logic checks passed. Revised export, portable reload, decoded video motion, and transparent logo corners in MP4 checked. Overview visually inspected; browser interaction remains untested.


## Minimal label revision — 2026-11-07
- Latest deliverables: `workspace/test-runs/20261107-171536/` (`decibel-peak-project.zip`, `decibel-peak-export.zip`, `preview.jpg`, `label-detail.jpg`).
- #2 now uses black background instead of the final-photo background.
- Removed white label boxes. Labels use Gill Sans Regular, 25px uppercase with 3px tracking, smaller muted step numbers, thin vertical divider, warm off-white translucent lettering at bottom left. #0 remains unlabeled.
- Typography is stored as transparent PNG overlays for consistent font appearance across machines; labels move/resize as image layers rather than editable text. Original numbered text labels remain in previous project versions.
- Revised preview visually checked, exports completed, project reload passed, and actual MP4 black background checked. No application code changed in this revision.


## Git repository — 2026-11-07
- Local Git initialized on `main`; origin: `https://github.com/stefanchamberland/db-canvas.git`.
- `.gitignore` excludes test media, workspace outputs/projects, ZIPs, Python environments/caches, local credentials/settings, and OS metadata. Existing media and exports remain on disk.
- App code, tests, documentation, project memory, icons, and portable Mac launcher bundle are tracked.
- Validation notes updated with the latest Mac test results.


## Presets and native typography — 2026-11-07
- Added Saved presets UI with disk-backed save/list/load APIs. Presets copy media to `workspace/presets/<name>` and survive restarts/source-file removal. Duplicate names are protected; edits affect the working project, not the preset.
- Saved approved layout as `workspace/presets/lut-bakery-demo/project.dbcanvas` with 15 layers. Original raster labels replaced by editable native text using Gill Sans, 25px, tracking 3, warm off-white at 225/255 opacity, smaller numbered steps/dividers, no text backgrounds. Layout/media/logos/PIP retained.
- Added native text family, tracking, opacity, background, step formatting, and frame naming. Browser uses shared server text renderer for export parity. System fonts remain system dependencies; families/settings are saved, font files are not redistributed.
- Added selected-media replacement (optionally all matching uses), Fill/Fit slide actions, and apply selected logo as watermark on all slides.
- Eleven Python tests and extended Node UI checks passed, covering persistent presets with original source removed, duplicate/path rejection, styled previews, typography undo/redo, fit/fill, and watermark reuse.
- Native Chrome check successfully loaded lut-bakery-demo and verified editable Gill Sans/step/spacing/opacity controls. Server started at http://127.0.0.1:8765 for this session (keep running to use the open editor).
- User’s approved old deliverables remain under `workspace/test-runs/20261107-171536`.
- Fresh five-slide export from the native-text preset passed. Approved artwork matches exactly outside label regions; decoded MP4 typography matched expected rendering within compression tolerance, and video background was verified black.
