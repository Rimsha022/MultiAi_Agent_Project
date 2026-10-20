# =========================================================
# SCORING ENGINE
# =========================================================


# Weights for each evaluation criterion
WEIGHTS = {
    "relevance": 0.25,
    "completeness": 0.20,
    "justification": 0.20,
    "context_awareness": 0.15,
    "conciseness": 0.05,
    "consistency": 0.15
}


def calculate_quality_scores(evaluation_results):
    """
    Calculate weighted quality score for each model.

    Formula:
        Quality Score = Sum(weight_i * metric_i)

    All metrics are scored from 0 to 10.
    Therefore, final quality score is also 0 to 10.
    """

    quality_scores = {}

    for model, scores in evaluation_results.items():

        total_score = 0

        for metric, weight in WEIGHTS.items():

            metric_score = scores.get(metric, 0)

            total_score += metric_score * weight

        quality_scores[model] = round(
            total_score,
            3
        )

    return quality_scores


def rank_models(quality_scores):
    """
    Rank models from highest to lowest quality score.
    """

    ranked_models = sorted(
        quality_scores.items(),
        key=lambda item: item[1],
        reverse=True
    )

    return ranked_models