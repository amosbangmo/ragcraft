import numpy as np

class EvaluationService:
    def compute_confidence(self, docs) -> float:
        if not docs:
            return 0.0

        scores = []

        for doc in docs:

            score = doc.metadata.get("score", 0.5)

            scores.append(score)

        confidence = float(np.mean(scores))

        return round(confidence, 2)
