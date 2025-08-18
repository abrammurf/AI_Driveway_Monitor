from pathlib import Path
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib
from collections import defaultdict
import time
import os
import numpy as np
import cv2
import hailo

from hailo_apps.hailo_app_python.core.common.buffer_utils import get_caps_from_pad, get_numpy_from_buffer
from hailo_apps.hailo_app_python.core.gstreamer.gstreamer_app import app_callback_class
from hailo_apps.hailo_app_python.apps.detection.detection_pipeline import GStreamerDetectionApp

# -----------------------------------------------------------------------------------------------
# User-defined class to be used in the callback function
# -----------------------------------------------------------------------------------------------
# Inheritance from the app_callback_class
class user_app_callback_class(app_callback_class):
    def __init__(self):
        super().__init__()
        self.confidence_threshold = 0.4
        # self.vehicle_classes = ["car", "bus", "truck"]
        self.vehicle_classes = ["person"]
        self.vehicles = {}
        self.next_vehicle_id = 0
        self.vehicle_history = defaultdict(list)
        self.max_disappeared = 30*10

    def update_tracking(self, current_vehicles):
        # Mark all existing vehicles as disappeared initially
        for vehicle_id in self.vehicles:
            self.vehicles[vehicle_id]["disappeared"] += 1
        
        # Update or add new vehicles
        for box in current_vehicles:
            matched = False
            for vehicle_id, vehicle_info in self.vehicles.items():
                if self.calculate_overlap(box, vehicle_info["box"]) > 0.3:
                    self.vehicles[vehicle_id]["box"] = box
                    self.vehicles[vehicle_id]["disappeared"] = 0
                    self.vehicle_history[vehicle_id].append(time.time())
                    print(self.vehicle_history)
                    matched = True
                    break
            
            if not matched:
                print("Vehicle Arriving")
                self.vehicles[self.next_vehicle_id] = {
                    "box": box,
                    "disappeared": 0
                }
                self.vehicle_history[self.next_vehicle_id].append(time.time())
                self.next_vehicle_id += 1
        
        # Remove vehicles that have disappeared for too long
        for vehicle_id in list(self.vehicles.keys()):
            if self.vehicles[vehicle_id]["disappeared"] > self.max_disappeared:
                print("Vehicle Leaving")
                del self.vehicles[vehicle_id]
    
    # Calculate IoU between two boxes (Intersection over Union)
    def calculate_overlap(self, box1, box2):
        x1, y1, w1, h1 = box1
        x2, y2, w2, h2 = box2
        
        # Calculate intersection
        x_left = max(x1, x2)
        y_top = max(y1, y2)
        x_right = min(x1 + w1, x2 + w2)
        y_bottom = min(y1 + h1, y2 + h2)
        
        if x_right < x_left or y_bottom < y_top:
            return 0.0
        
        intersection = (x_right - x_left) * (y_bottom - y_top)
        
        # Calculate union
        area1 = w1 * h1
        area2 = w2 * h2
        union = area1 + area2 - intersection
        
        return intersection / union if union > 0 else 0
    
    # Get vehicle status based on time present
    
    def get_vehicle_status(self, vehicle_id):
        if vehicle_id not in self.vehicle_history:
            return "Unknown"
        
        timestamps = self.vehicle_history[vehicle_id]
        if len(timestamps) < 2:
            return "Arriving"
        
        time_present = timestamps[-1] - timestamps[0]
        if time_present < 3:
            return "Arriving"
        else:
            return "Present"

# -----------------------------------------------------------------------------------------------
# User-defined callback function
# -----------------------------------------------------------------------------------------------

# This is the callback function that will be called when data is available from the pipeline
def app_callback(pad, info, user_data):
    # Get the GstBuffer from the probe info
    buffer = info.get_buffer()
    # Check if the buffer is valid
    if buffer is None:
        return Gst.PadProbeReturn.OK

    # Using the user_data to count the number of frames
    user_data.increment()
    # string_to_print = f"Frame count: {user_data.get_count()}\n"

    # Get the caps from the pad
    format, width, height = get_caps_from_pad(pad)

    # If the user_data.use_frame is set to True, we can get the video frame from the buffer
    frame = None
    if user_data.use_frame and format is not None and width is not None and height is not None:
        # Get video frame
        frame = get_numpy_from_buffer(buffer, format, width, height)

    # Get the detections from the buffer
    roi = hailo.get_roi_from_buffer(buffer)
    detections = roi.get_objects_typed(hailo.HAILO_DETECTION)
    
    
    
    
    current_vehicles = []
        
    for detection in detections:
        label = detection.get_label()
        confidence = detection.get_confidence()
        
        if confidence > user_data.confidence_threshold and label == "person":
            # Get bounding box
            bbox = detection.get_bbox()
            
            # Get coordinates
            x_min = bbox.xmin()
            y_min = bbox.ymin()
            box_width = bbox.width()
            box_height = bbox.height()
            
            x_max = x_min + box_width
            y_max = y_min + box_height
            current_vehicles.append((int(x_min), int(y_min), int(box_width), int(box_height)))
        
    # Update tracking
    user_data.update_tracking(current_vehicles)
    
    # Draw results
    for vehicle_id, vehicle_info in user_data.vehicles.items():
        if vehicle_info["disappeared"] == 0:
            x, y, w, h = vehicle_info["box"]
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                
            # Add status text
            status = user_data.get_vehicle_status(vehicle_id)
            cv2.putText(frame, f"ID: {vehicle_id} ({status})", 
            (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            print(vehicle_id)
            print(status)
                
    if user_data.use_frame:
        # Note: using imshow will not work here, as the callback function is not running in the main thread
        # Let's print the detection count to the frame
        cv2.putText(frame, f"Detections: {detection_count}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        # Example of how to use the new_variable and new_function from the user_data
        # Let's print the new_variable and the result of the new_function to the frame
        cv2.putText(frame, f"{user_data.new_function()} {user_data.new_variable}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        # Convert the frame to BGR
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        user_data.set_frame(frame)

# print(string_to_print)
    return Gst.PadProbeReturn.OK

if __name__ == "__main__":
    project_root = Path(__file__).resolve().parent.parent
    env_file     = project_root / ".env"
    env_path_str = str(env_file)
    os.environ["HAILO_ENV_FILE"] = env_path_str
    # Create an instance of the user app callback class
    user_data = user_app_callback_class()
    app = GStreamerDetectionApp(app_callback, user_data)
    app.run()



