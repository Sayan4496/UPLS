from detection.confidence_engine import ConfidenceEngine


class DetectorRegistry:
    """
    Registry that stores detector functions and returns the best match.
    """

    _detectors = []

    @classmethod
    def register(cls, name, detector_func):
        cls._detectors.append({
            "name": name,
            "detector": detector_func
        })

    @classmethod
    def get_detectors(cls):
        return list(cls._detectors)

    @classmethod
    def detect(cls, raw_content):
        results = []

        for entry in cls._detectors:
            detector = entry["detector"]
            detector_result = detector(raw_content)

            if isinstance(detector_result, dict):
                if detector_result.get("score") is None:
                    continue

                results.append({
                    "detector": entry["name"],
                    "score": detector_result["score"],
                    "reason": detector_result.get("reason", "")
                })

        return ConfidenceEngine.score_results(results)
