from app.labels import LABELS


def test_43_classes():
    assert len(LABELS) == 43


def test_known_indices():
    assert LABELS[14] == "Stop"
    assert LABELS[13] == "Yield"
    assert LABELS[17] == "No entry"
    assert LABELS[2] == "Speed limit (50km/h)"
