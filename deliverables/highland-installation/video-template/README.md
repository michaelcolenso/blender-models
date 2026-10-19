# Highland installation: reusable video template

[View the ten-frame storyboard](storyboard.png) · [Watch the two-second motion sample](motion-sample.mp4) · [Installation still](installation-preview.png)

The first shared video recipe reuses the Highland studio model's exterior,
shared distribution and **Unit B / 106** installation scenes. It preserves the
90-second construction sequence and provides editable full-frame titles,
projected labels, a system legend and the existing narrated soundtrack.

These files are previews: the storyboard uses 960×540 imagery at 16 samples;
the silent motion sample uses 640×360 imagery at 8 samples and six rendered
frames per second, repeated into a 24 fps MP4. It contains 12 native model frames
and 48 delivered frames. No optical-flow interpolation is used.

The full native film has not been rendered. Production presets render every
frame at 1920×1080/24 fps or 3840×2160/24 fps. Start with the four-frame production
quality-test recipe on a configured GPU worker before scheduling all 2,160 frames.

[Video brief](../../../render/videos/highland-installation.json) · [Quality-test brief](../../../render/videos/highland-installation-quality-test.json) · [Workflow and commands](../../../render/VIDEO-WORKFLOW.md) · [Validation](validation.json)

The source model file remains unchanged. All physical installation geometry is
assumed; exterior context does not locate the pilot at a particular facade
opening. Testing and service transfer depict proposed work, not field results.
This template is separate from the earlier Unit A / 107 water study.

Validation covered 16 automated tests, Actions workflow lint, exact frame sets,
image dimensions and hashes, two-shot narrated audio assembly, and rebuilding
graphics from compatible cached image plates. The storyboard and a decoded
sample frame were inspected for visible content, readable titles and notices.
The complete production animation, GPU performance and temporal noise remain
to be reviewed. The two saved plans record the exact inputs for these previews.
