"""The versioned, dependency-free landmark feature contract."""

from math import isfinite

FEATURE_SCHEMA = "mediapipe-xyz-wrist-v1"
LANDMARK_COUNT = 21
FEATURE_DIMENSION = LANDMARK_COUNT * 3


def _coordinates(landmark):
    try:
        values = (landmark.x, landmark.y, landmark.z)
    except AttributeError:
        try:
            values = tuple(landmark)
        except TypeError as error:
            raise ValueError("Each landmark must provide x, y, and z values") from error
    if len(values) != 3:
        raise ValueError("Each landmark must provide exactly three coordinates")
    try:
        values = tuple(float(value) for value in values)
    except (TypeError, ValueError) as error:
        raise ValueError("Landmark coordinates must be numeric") from error
    if not all(isfinite(value) for value in values):
        raise ValueError("Landmark coordinates must be finite")
    return values


def extract_landmark_features(landmarks):
    """Return 21 wrist-normalized XYZ landmarks in landmark-major order."""
    try:
        landmarks = tuple(landmarks)
    except TypeError as error:
        raise ValueError("Landmarks must be an iterable of 21 landmarks") from error
    if len(landmarks) != LANDMARK_COUNT:
        raise ValueError("mediapipe-xyz-wrist-v1 requires exactly 21 landmarks")
    points = tuple(_coordinates(landmark) for landmark in landmarks)
    wrist = points[0]
    features = tuple(value - wrist[index] for point in points for index, value in enumerate(point))
    if len(features) != FEATURE_DIMENSION or not all(isfinite(value) for value in features):
        raise ValueError("Feature extraction produced invalid values")
    return features
