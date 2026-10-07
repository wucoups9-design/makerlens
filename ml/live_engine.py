"""Resident CPU models for sampled camera frames. No image files are written."""
import base64
import hashlib
import time
import cv2
import numpy as np
import torch
from ultralytics import YOLO
from run import EXPECTED, extract_boxes, draw_frame, resize_frame


class LiveEngine:
    def __init__(self, goggles, gloves):
        torch.set_num_threads(2)
        self.models = {}
        for name, path in [('goggles', goggles), ('gloves', gloves)]:
            model = YOLO(str(path))
            if [model.names[i] for i in range(len(model.names))] != EXPECTED[name]:
                raise ValueError('Unexpected model classes')
            self.models[name] = model
        # Warm up once, rather than reloading Python and both models on every frame.
        self(np.zeros((480, 640, 3), dtype=np.uint8), 'both')

    def __call__(self, rgb, mode):
        started = time.perf_counter()
        frame = resize_frame(cv2.cvtColor(np.array(rgb), cv2.COLOR_RGB2BGR), 960)
        detections = []
        for name, model in self.models.items():
            if mode == 'both' or mode == name:
                detections.extend(extract_boxes(model.predict(frame, device='cpu', imgsz=640,
                    conf=.4, verbose=False)[0], name))
        ok, preview = cv2.imencode('.jpg', draw_frame(frame, detections, 'Camera sample'),
                                  [cv2.IMWRITE_JPEG_QUALITY, 75])
        if not ok: raise ValueError('Cannot encode result')
        return {'image': 'data:image/jpeg;base64,' + base64.b64encode(preview).decode(),
                'detections': detections, 'seconds': round(time.perf_counter()-started, 3)}
