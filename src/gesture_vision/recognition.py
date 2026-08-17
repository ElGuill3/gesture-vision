"""Shared, dependency-light per-frame gesture recognition."""

from collections import Counter, deque
from math import isfinite

from .features import extract_landmark_features

HANDS = ("left", "right")


def new_smoothing_state(window):
    if isinstance(window, bool) or not isinstance(window, int) or window < 0:
        raise ValueError("Smoothing window must be a non-negative integer")
    return {hand: deque(maxlen=max(1, window)) for hand in HANDS}


def _predict(landmarks, model, scaler):
    features = extract_landmark_features(landmarks)
    probabilities = tuple(model.predict(scaler.transform([features]), verbose=0)[0])
    if not probabilities:
        raise ValueError("Model prediction is empty")
    index = max(range(len(probabilities)), key=probabilities.__getitem__)
    confidence = float(probabilities[index])
    if not isfinite(confidence):
        raise ValueError("Model confidence must be finite")
    return index, confidence


def recognize_frame(detections, model, scaler, decoder, threshold, histories):
    """Recognize attributed hands and clear state whenever input is unsafe."""
    outcomes = {hand: (None, 0.0) for hand in HANDS}
    try:
        detections = tuple(detections or ())
    except TypeError:
        detections = ()
    seen = set()
    for detection in detections:
        try:
            hand, landmarks = detection
            hand = str(hand).lower()
        except (TypeError, ValueError):
            continue
        if hand not in outcomes:
            continue
        seen.add(hand)
        history = histories[hand]
        try:
            index, confidence = _predict(landmarks, model, scaler)
            if confidence < threshold:
                history.clear()
                outcomes[hand] = (None, confidence)
                continue
            history.append(index)
            label = decoder(Counter(history).most_common(1)[0][0])
            if not isinstance(label, str) or not label:
                raise ValueError("Decoded label must be non-empty")
            outcomes[hand] = (label, confidence)
        except (AttributeError, IndexError, KeyError, TypeError, ValueError):
            history.clear()
    for hand in HANDS:
        if hand not in seen:
            histories[hand].clear()
    return outcomes
