# _dB Canvas

A small, portable local web app for composing Instagram photos, videos, and mixed-media carousels. The browser is the GUI; Python, Pillow, and FFmpeg handle local file rendering. Nothing is uploaded to a remote service. No account, Node build, or database is required.

## Start on macOS

1. Place this folder in `_dB Ops/Software Dev/db-canvas`.
2. Install Python 3.11+ if needed. For video, install FFmpeg including ffprobe (`brew install ffmpeg` if you use Homebrew).
3. Double-click `Launch.command`. On first launch it creates a local virtual environment and installs Pillow from requirements.txt. Internet is needed for that first dependency installation.
4. The editor opens in your default browser. Keep the Terminal window running; Ctrl+C stops the app. If macOS does not execute the launcher, run `bash Launch.command` from Terminal in this folder.

On Windows, install Python 3.11+ and FFmpeg, then use `Launch.bat`. On Linux, use `bash Launch.command` or the manual commands below. After setup, the app works offline.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python server.py
```

To use a chosen port without opening a browser: `python server.py --no-browser --port 8765`.

## Workflow

- Import photos/videos or drop them into the page. The media library is separate from placed frames.
- Drag an asset onto the canvas, click its plus button, or choose **Arrange all media**. Automatic layouts use media-library order: Seamless, Frames, or Full bleed. They are starting compositions, not an AI assessment of your strongest photos.
- Drag frames across slide boundaries; resize the lower-right handle. Use the inspector for precise position, size, border, fit, or crop focus. Click **Apply frame changes** after changing inspector values.
- Add simple location stickers/text. Layer order, duplicate, delete, Undo, and Redo are supported. Library order is the import order; layer front/back controls stacking, not the scene sequence. Move frames on the continuous canvas to change their place in the sequence.
- Video frames support in/out points, looping the selected trim, and export volume. The browser preview is silent. If a source codec is unsupported by your browser, a poster image remains available; FFmpeg can still render supported source files.
- Select a scene in the bottom strip to set its duration. Reel and Story safe-area lines are approximate visual guides.
- **Save project** downloads a ZIP containing the layout and original assets. **Open project** reopens that ZIP. Unsaved edits are in browser memory and do not survive closing/reloading; save before leaving.
- **Export** renders in the background, downloads a ZIP, and also keeps the files in this folder's `workspace/exports` directory. Export does not overwrite an earlier export.

## Reusable presets and branding

Use **Saved presets → Use preset** to start from a saved design. Enter a lowercase name such as `lut-bakery-demo` and click **Save new preset** to store the current canvas, media, logos, text styling, and scene durations. Presets persist under `workspace/presets`, with their own copies of the assets. Loading one creates an editable project; editing it does not change the saved preset. Save a new preset name for a variation. Existing names are protected from accidental overwriting.

Select a frame and choose **Replace selected media…** to swap in a new photo or video while keeping its position, dimensions, fit, crop focus, and border. Enable **Replace all uses of this media** to update repeated artwork such as a logo. New videos start at zero and use their full source duration; the scene duration stays editable in the timeline. **Fill slide** covers the slide with a proportional crop; **Fit slide** shows the complete media at its original aspect ratio. Set the canvas background to black for landscape clips.

Import a transparent logo, size and position it on one slide, and choose **Use as watermark on all slides**. The app repeats its size and relative position. Reapplying updates the matching watermark set without duplicating it.

Text is editable in the inspector: choose a font, size, color, letter spacing, opacity, and whether to show a light background. **Minimal step label** adds a smaller step number and fine divider; edit the number and title separately. These labels are rendered by the same typography engine in the browser and export, including video overlays. No external label-image generation is needed. Font settings are saved; fonts use installed system files (Gill Sans and Baskerville on macOS, with a Helvetica/Arial/DejaVu fallback on other systems). Font files are not redistributed.

Presets and their media are local and excluded from Git. To back up or move a design, load its preset and use **Save project** for a portable ZIP. Keep the `workspace/presets` folder when cleaning other working files.

## Formats and outputs

| Project | Output |
| --- | --- |
| Carousel | 1–20 numbered slides; JPEG for still compositions, H.264/AAC MP4 for slides containing video |
| Single post | One JPEG or MP4 |
| Reel | Scenes combined into one H.264/AAC MP4 |
| Stories | One H.264/AAC MP4 per scene |

Optional background audio converts every scene to video. Soundtrack playback continues across scene offsets. A short soundtrack repeats; a trimmed clip can loop, or its final video frame is held while its audio ends. Multiple enabled clip soundtracks are mixed and limited. Frame rate is 30 fps. All slides share a common canvas size. A video crossing boundaries is rendered into each intersected slide, but Instagram does not synchronize playback across swipes.

Presets: 4:5, 1:1, 3:4, 1.91:1, 16:9, and 9:16. Custom even dimensions from 160–3840 px are supported. Presets are editor choices, not a promise that every combination is accepted by every Instagram publishing method. Native-app and API limits differ; verify the upload method you use. Use 4:5 for conservative mixed-feed layouts and 9:16 for full-screen Reels/Stories. Instagram help pages were rate limited during research, so changing duration/account-specific restrictions are not hard-coded as definitive limits.

`cover.jpg` is an optional still cover, not an additional carousel slide. `export.json` records slide order and dimensions.

## Local files and portability

Move the app folder to another computer, install its runtime dependencies, and reopen a saved project ZIP. Media uploaded into the GUI is copied under `workspace/media`; export and opened-project working copies are also retained under `workspace`. Delete that directory only after saving the projects and exports you want to keep. It is not included in the distributable app archive.

The app listens only on 127.0.0.1, on a random available port by default. A per-run token protects its local API. It is not designed for cloud hosting or multiuser access.

## Scope

This version handles static compositions, video composition/trim, mixed-media exports, and scene sequencing. It is not a full nonlinear video editor: no animated keyframes, transitions, speech transcription, caption generation, color grading, live broadcasting, licensed music library, publishing API, or native Instagram interactive stickers. Add Instagram-native features when posting. Large video compositions can take time to render and use temporary disk space.

## Verify

```sh
python -m unittest discover -s tests -v
```

Tests exercise continuous-image seams, project portability, moving video with source audio, scene concatenation with soundtrack, and protection of existing exports. Browser workflow tests are recorded in VALIDATION.md.
