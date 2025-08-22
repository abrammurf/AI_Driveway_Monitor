# AI Driveway Monitoring System

**AI Car Tracker on Raspberry Pi 5 + HAILO AI Hat**

---

## About The Project

This repository contains a **real‑time car tracker** built for **Raspberry Pi 5** with the **HAILO AI Hat**. It uses the official `hailo_apps` GStreamer detection pipeline to perform edge inference and draws tracked bounding boxes with OpenCV. Objects are tracked across frames using lightweight IOU matching with simple persistence logic ("Arriving" vs "Present").

### Key Features

* 🚀 **Edge inference** via HAILO’s GStreamer pipeline (`GStreamerDetectionApp`).
* 🧠 **Class filtering** (default: `person`) and confidence thresholding.
* 🔁 **Simple tracker** with IOU-based matching and disappearance timeouts.
* 🖼️ **On-frame overlays** for ID & status using OpenCV.
* 🧰 Easily adjustable parameters: `confidence_threshold`, `vehicle_classes`, `max_disappeared`.

> **Note**: The code references a `.env` file (exported via `HAILO_ENV_FILE`) for HAILO runtime configuration.

---

## Built With

* Python 3.10+ (Pi OS 64-bit)
* GStreamer 1.0
* OpenCV (cv2)
* NumPy
* HAILO SDK / `hailo_apps` (GStreamer pipeline & buffer utils)
* PyGObject (`gi`)

---

## Getting Started

These instructions help you run the tracker on a Raspberry Pi 5 with the HAILO AI Hat. Exact installation commands for HAILO components vary by SDK version—follow your HAILO release notes and then return here.

### Prerequisites

1. **Raspberry Pi 5** running 64‑bit Raspberry Pi OS.
2. **HAILO AI Hat** properly installed and recognized by the OS.
3. **HAILO SDK / Runtime** and **`hailo_apps`** installed on the Pi (includes GStreamer plugins and Python bindings used here).
4. **System dependencies** (examples):

   * GStreamer 1.0 base + dev packages
   * Python development headers and pip
   * OpenCV (`opencv-python`), NumPy
   * PyGObject (`python3-gi`)

### Installation

```bash
# 1) Update system
sudo apt update && sudo apt upgrade -y

# 2) (Recommended) Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3) Install Python packages
pip install --upgrade pip wheel
pip install numpy opencv-python PyGObject
# HAILO python packages are typically installed by the SDK; verify import works later

# 4) Clone your repo (replace with your actual repo URL)
git clone <YOUR_REPO_URL>.git
cd <YOUR_REPO_NAME>

# 5) Prepare a .env file for HAILO runtime settings
cp .env.example .env   # if you have one; otherwise create .env as needed

# 6) Export path to the .env at runtime is handled by the script
```

> ⚠️ If `import hailo` or `from hailo_apps...` fails, re‑install or source your HAILO SDK environment as described in the HAILO documentation for your release.

---

## Configuration

Most runtime behavior is governed by attributes in `user_app_callback_class`:

* `confidence_threshold` *(float, default 0.4)*: Minimum detection confidence to consider.
* `vehicle_classes` *(list\[str], default ********************`["person"]`********************)*: Detected label names to track. You can switch back to cars/bus/truck by editing this list.
* `max_disappeared` *(frames, default ********************`30*10`********************)*: How many frames an object can go undetected before being declared "left" and removed.

The script expects a `.env` file at the project root. At startup it sets:

```bash
export HAILO_ENV_FILE=<project_root>/.env
```

Populate your `.env` with whatever your pipeline/runtime requires (paths, model artifacts, camera selection, etc.).

---

## Usage

Run the application directly:

```bash
python path/to/driveway_monitor.py
```

On startup, the app:

1. Loads environment from `.env` via `HAILO_ENV_FILE`.
2. Creates `user_app_callback_class()` for per‑frame logic and tracking.
3. Launches the HAILO GStreamer detection pipeline via `GStreamerDetectionApp`.
4. In the frame callback, filters detections by label & confidence, updates tracks, then overlays IDs and status with OpenCV.

### Expected Runtime Behavior

* New objects trigger `"Vehicle Arriving"` log (label kept for historical reasons; tracking is class‑agnostic).
* When a track persists, status flips to **Present**.
* Objects that disappear for longer than `max_disappeared` are removed with `"Vehicle Leaving"` log.

### Switching Target Classes

Change this line in `__init__` of `user_app_callback_class`:

```python
self.vehicle_classes = ["person"]  # e.g., switch to ["car", "bus", "truck"]
```

Ensure your HAILO model’s label set includes the class names you choose.

---

## Troubleshooting

* **`NameError: name 'detection_count' is not defined`**

  * In the overlay section, the code references `detection_count` but does not define it. Replace with `len(detections)` or remove that overlay line.

* **`AttributeError: 'user_app_callback_class' object has no attribute 'new_variable'/'new_function'`**

  * The overlay includes `user_data.new_function()` and `user_data.new_variable` as examples. Remove or implement these members.

* **No camera / no frames**

  * Confirm your source (CSI/USB) is configured in the HAILO GStreamer pipeline that `GStreamerDetectionApp` launches. Ensure the camera is detected by the OS and HAILO pipeline configuration.

* \*\*Imports fail for ****`hailo`**** or \*\***`hailo_apps`**

  * Re‑source your HAILO SDK environment and verify installation instructions for your SDK version.

* **High CPU or low FPS**

  * Reduce overlay work, raise `confidence_threshold`, or prune classes. Ensure GPU/accelerator offload is active per HAILO SDK.

---

## Contributing

Contributions are what make the open source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## License

Distributed under the MIT License. See `LICENSE` for more information.

---

## Contact

Project Maintainer – *Abram Murphy*
Email: *[abrammurphy22@gmail.com](mailto:abrammurphy22@gmail.com)*
Project Link: *\<YOUR\_REPO\_URL>*

---

## Acknowledgments

* HAILO SDK & `hailo_apps` examples
* GStreamer & PyGObject
* OpenCV
* Inspired by the awesome **Best‑README‑Template** by *othneildrew*
