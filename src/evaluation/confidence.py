import numpy as np


def compute_confidence(docs):

    if not docs:
        return 0.0

    scores = []

    for doc in docs:

        score = doc.metadata.get("score", 0.5)

        scores.append(score)

    confidence = float(np.mean(scores))

    return round(confidence, 2)
