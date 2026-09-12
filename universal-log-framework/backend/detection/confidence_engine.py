class ConfidenceEngine:
    """
    Lightweight scoring helper for format detection.
    Keeps the scoring logic separate from the detectors themselves so the
    format detector can stay simple and extensible.
    """

    @staticmethod
    def normalize(score):
        """
        Clamp confidence scores into the 0-1 range used by the API.
        """

        if score is None:
            return 0.0

        try:
            score = float(score)
        except (TypeError, ValueError):
            return 0.0

        return max(0.0, min(1.0, score))

    @staticmethod
    def score_results(results):
        """
        Accept a list of detector results and return the top-scoring detector.
        """

        if not results:
            return None

        scored_results = []

        for result in results:
            scored_results.append({
                "detector": result.get("detector", "unknown"),
                "score": ConfidenceEngine.normalize(result.get("score", 0.0)),
                "reason": result.get("reason", "")
            })

        scored_results.sort(
            key=lambda item: item["score"],
            reverse=True
        )

        best = scored_results[0]

        breakdown = {
            item["detector"]: round(item["score"], 2)
            for item in scored_results
        }

        return {
            "detected_format": best["detector"],
            "confidence": round(best["score"], 2),
            "score_breakdown": breakdown,
            "details": best
        }
