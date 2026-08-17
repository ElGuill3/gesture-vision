from pathlib import Path
import sys
import unittest
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gesture_vision.recognition import new_smoothing_state, recognize_frame


def landmarks(offset=0):
    return [SimpleNamespace(x=offset + index, y=index + 0.5, z=index + 1.0) for index in range(21)]


class Scaler:
    def __init__(self):
        self.calls = []

    def transform(self, values):
        self.calls.append(values)
        return values


class Model:
    def __init__(self, predictions):
        self.predictions = iter(predictions)

    def predict(self, values, verbose=0):
        return [next(self.predictions)]


class Decoder:
    def __init__(self, labels):
        self.labels = labels

    def __call__(self, index):
        return self.labels[index]


class RecognitionTests(unittest.TestCase):
    def test_hand_attribution_uses_isolated_histories(self):
        scaler = Scaler()
        histories = new_smoothing_state(2)
        results = recognize_frame((("left", landmarks()), ("right", landmarks(10))), Model(((0.9, 0.1), (0.1, 0.9))), scaler, Decoder(("left-label", "right-label")), 0.7, histories)
        self.assertEqual(results, {"left": ("left-label", 0.9), "right": ("right-label", 0.9)})
        self.assertEqual((list(histories["left"]), list(histories["right"]), len(scaler.calls)), ([0], [1], 2))

    def test_missing_invalid_and_low_confidence_clear_history(self):
        cases = (
            ((), (), (None, 0.0)),
            ((("left", landmarks()[:-1]),), (), (None, 0.0)),
            ((("left", landmarks()),), ((0.6, 0.4),), (None, 0.6)),
        )
        for observations, predictions, expected in cases:
            with self.subTest(observations=observations):
                histories = new_smoothing_state(2)
                decoder = Decoder(("first", "next"))
                recognize_frame((("left", landmarks()),), Model(((0.9, 0.1),)), Scaler(), decoder, 0.7, histories)
                results = recognize_frame(observations, Model(predictions), Scaler(), decoder, 0.7, histories)
                self.assertEqual((results["left"], list(histories["left"])), (expected, []))
                self.assertEqual(recognize_frame((("left", landmarks()),), Model(((0.1, 0.9),)), Scaler(), decoder, 0.7, histories)["left"], ("next", 0.9))


if __name__ == "__main__":
    unittest.main()
