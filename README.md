# AI Driveway Monitor

A lightweight Python app that runs a Hailo detection pipeline (via `hailo_apps`) and tracks cars across frames using simple IoU-based assignment. The app draws bounding boxes and a small status label (Arriving / Present) per tracked ID.

---

## Features

* **Real‑time detection** with Hailo (`hailo_apps.hailo_app_python` GStreamer pipeline).
* **Simple multi-object tracking** using Intersection-over-Union (IoU) matching + disappearance timeout.
* **Per‑ID status** (Arriving vs. Present) based on time observed.
* **Overlay rendering**: draws boxes and labels directly on frames in the callback.

---

## Requirements

* **Hardware**: Hailo-8/8L device (or compatible dev kit).
* **OS/Packages**:

  * Python 3.8+ (tested up to 3.11 in most environments)
  * GStreamer 1.16+ with dev headers (`gstreamer1.0`, `gstreamer1.0-plugins-*`, `gstreamer1.0-libav`)
  * OpenCV (`opencv-python`)
  * NumPy
  * PyGObject (`gi` / `pygobject` bindings)
  * HailoRT / Hailo Apps SDK with Python packages available:

    * `hailo`
    * `hailo_apps.hailo_app_python`

> Install methods vary by OS and Hailo SDK version. Follow your Hailo SDK docs to set up drivers, firmware, runtime, and the `hailo_apps` Python packages.

---

## Project Layout

```
repo/
├─ app/                      # Your app’s Python file (this file)
├─ .env                      # Hailo pipeline/config environment file (required)
└─ ...
```

---

## Setup

1. **Create & activate a virtual environment (recommended):**

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   python -m pip install --upgrade pip
   ```

2. **Install Python deps:**

   ```bash
   pip install numpy opencv-python pygobject
   # Hailo SDK/Apps install comes from Hailo’s installers; ensure `hailo` and `hailo_apps.hailo_app_python` import successfully.
   ```

3. **Install GStreamer (system):**

   * Linux (Debian/Ubuntu example):

     ```bash
     sudo apt-get update
     sudo apt-get install -y \
       gstreamer1.0-tools gstreamer1.0-plugins-base gstreamer1.0-plugins-good \
       gstreamer1.0-plugins-bad gstreamer1.0-plugins-ugly gstreamer1.0-libav \
       gir1.2-gstreamer-1.0
     ```
   * macOS (Homebrew example):

     ```bash
     brew install gstreamer gst-plugins-base gst-plugins-good gst-plugins-bad gst-libav pygobject3
     ```

4. **Create your ************`.env`************ file:**
   The app sets `HAILO_ENV_FILE` to the repo’s `.env`. This file should contain any environment variables or paths required by your Hailo pipeline/config (e.g., model HEF paths, pipeline YAMLs, source URIs). Example skeleton:

   ```dotenv
   # Example keys — replace with the ones your Hailo pipeline expects
   # HAILO_MODEL_HEF=/path/to/model.hef
   # HAILO_PIPELINE_CONFIG=/path/to/pipeline.yaml
   # VIDEO_SOURCE=/dev/video0
   ```

---

## Running

From the project root:

```bash
python app/your_script.py
```

On start, the code:

* Loads `.env` and exports `HAILO_ENV_FILE`.
* Constructs a `GStreamerDetectionApp` from `hailo_apps`.
* Registers a frame/detection callback (`app_callback`) and runs the pipeline.

Stop with `Ctrl+C`.

---

## How It Works

### Data Flow

1. `GStreamerDetectionApp` handles the GStreamer pipeline and invokes `app_callback` for each buffer.
2. In `app_callback`:

   * The current frame (as NumPy) is obtained via `get_numpy_from_buffer(...)` if `use_frame` is enabled.
   * Detections are read with `hailo.get_roi_from_buffer(buffer)` then `roi.get_objects_typed(hailo.HAILO_DETECTION)`.
   * We filter to label `"person"` above `confidence_threshold` and store bounding boxes as `(x, y, w, h)`.
3. `user_app_callback_class.update_tracking(...)` performs IoU matching to maintain stable IDs and handles arrival/timeout logic.
4. Boxes and labels are drawn onto the frame; tracked ID status is derived from timestamps.

### Tracking Logic (brief)

* **Match**: For each new detection box, compute IoU vs. existing tracks; if IoU > 0.3, update that track, else start a new ID.
* **Disappear**: Every tick, increment a `disappeared` counter; if it exceeds `max_disappeared` frames, the track is removed.
* **Status**: If a track’s first-to-latest timestamp span is <3s, it’s **Arriving**; otherwise **Present**.

---

## Configuration Knobs

Inside `user_app_callback_class.__init__`:

* `self.confidence_threshold = 0.4` — detector confidence cutoff.
* `self.vehicle_classes = ["person"]` — which label(s) to track; switch to `["car", "bus", "truck"]` if your model supports them.
* `self.max_disappeared = 30*10` — frame-based patience before a track is dropped (adjust to your FPS).

In `app_callback` you can also:

* Control drawing (rectangles and `putText`).
* Convert color ordering before sending the frame onward (`RGB`→`BGR`).

> Note: `user_data.use_frame` must be **True** (it is provided by the base `app_callback_class`) to access and draw on frames. Ensure your pipeline sets/propagates frames accordingly.

---

## Known Issues / Fixes

* **`NameError: detection_count is not defined`**

  * The sample overlay draws `Detections: {detection_count}`, but `detection_count` isn’t defined. Replace with e.g. `len(detections)`:

    ```python
    cv2.putText(frame, f"Detections: {len(detections)}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    ```
* **No window appears**

  * The callback runs in a non-main thread; `cv2.imshow` is intentionally not used. The frame is passed back via `user_data.set_frame(frame)`; ensure your display/sink element in the GStreamer pipeline shows it (consult your pipeline config).
* **`user_data.use_frame`**\*\* is False\*\*

  * If frames are `None`, verify `use_frame` is enabled by the base class or set within your app; and confirm the pipeline includes a branch that makes frames available to the callback.
* **Wrong labels**

  * Make sure your Hailo model actually outputs the `person` class label string used in filtering. Label names can vary by model/package. Adjust the filter accordingly.

---

## Adapting for Vehicles (Cars/Buses/Trucks)

* Change `self.vehicle_classes` to your target labels and update the label check in the callback:

  ```python
  if confidence > user_data.confidence_threshold and label in user_data.vehicle_classes:
      ...
  ```
* Depending on your model, labels might be numeric IDs instead of strings; map them appropriately.

---

## Performance Tips

* Use a reasonable `max_disappeared` relative to your FPS and motion dynamics.
* If IDs flicker, raise the IoU threshold slightly (e.g., `>0.4`) and/or smooth boxes across frames.
* For crowded scenes, consider a stronger tracker (e.g., assignment with Hungarian algorithm + motion model) — this code aims to be simple and readable.

---

## Troubleshooting Checklist

* Hailo device recognized (`hailo` CLI tools work).
* `hailo_apps` imports succeed in your venv.
* GStreamer finds all required plugins; the pipeline file(s) referenced in `.env` exist.
* Camera/source path correct (e.g., `/dev/video0`), or network stream is reachable.

---

---

## Acknowledgments

* Built on top of Hailo’s `hailo_apps.hailo_app_python` GStreamer app scaffolding.
