"""Small deterministic tests; no model weights or participant data required."""
import sys
import unittest
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evaluate import iou, match, dataset_root
from vision import resize_frame, extract_boxes


class PipelineTests(unittest.TestCase):
    def test_iou(self):
        self.assertEqual(iou([0, 0, 10, 10], [0, 0, 10, 10]), 1)
        self.assertEqual(iou([0, 0, 10, 10], [10, 10, 20, 20]), 0)
        self.assertAlmostEqual(iou([0, 0, 10, 10], [5, 0, 15, 10]), 1 / 3)

    def test_match_once(self):
        gt = [{'class_id': 0, 'xyxy': [0, 0, 10, 10]}]
        predictions = [{'class_id': 0, 'xyxy': [0, 0, 10, 10], 'confidence': c}
                       for c in (.9, .7)]
        matched, fp, fn = match(gt, predictions)
        self.assertEqual((len(matched), fp, fn), (1, [1], []))

    def test_wrong_class(self):
        gt = [{'class_id': 0, 'xyxy': [0, 0, 10, 10]}]
        pred = [{'class_id': 1, 'xyxy': [0, 0, 10, 10], 'confidence': .9}]
        self.assertEqual(match(gt, pred), ([], [0], [0]))

    def test_empty(self):
        self.assertEqual(match([], []), ([], [], []))

    def test_resize_even(self):
        self.assertEqual(resize_frame(np.zeros((1920, 1080, 3), np.uint8), 960).shape, (960, 540, 3))
        self.assertEqual(resize_frame(np.zeros((501, 333, 3), np.uint8), 960).shape, (500, 332, 3))

    def test_dataset_root(self):
        config = Path('/tmp/example/data.yaml')
        self.assertEqual(dataset_root(config, {}), Path('/tmp/example').resolve())
        self.assertEqual(dataset_root(config, {'path': 'dataset'}), Path('/tmp/example/dataset').resolve())
        self.assertEqual(dataset_root(config, {'path': '/tmp/private-data'}), Path('/tmp/private-data'))

    def test_no_boxes(self):
        class Result:
            boxes = None
        self.assertEqual(extract_boxes(Result(), 'goggles'), [])


if __name__ == '__main__':
    unittest.main()
