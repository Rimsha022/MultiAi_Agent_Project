import os
import pandas as pd
import numpy as np

from scipy.stats import ttest_1samp
from scipy.stats import binomtest


RESULTS_FILE = "research/experiment_results.csv"


def load_results():

    if not os.path.exists(RESULTS_FILE):
        raise FileNotFoundError(
            f"Results file not found: {RESULTS_FILE}"
        )

    df = pd.read_csv(RESULTS_FILE)

    if df.empty:
        raise ValueError(
            "No experiment results available."
        )

    return df


def print_hypothesis_result(
    hypothesis,
    null_hypothesis,
    alternative_hypothesis,
    statistic,
    p_value,
    alpha=0.05
):

    print("\n" + "=" * 65)
    print(hypothesis)
    print("=" * 65)

    print(f"H0: {null_hypothesis}")
    print(f"H1: {alternative_hypothesis}")

    print(f"\nTest Statistic: {statistic:.4f}")
    print(f"p-value: {p_value:.6f}")
    print(f"Significance Level: {alpha}")

    if p_value < alpha:

        print(
            "\nDecision: REJECT H0"
        )

        print(
            "Result: Statistically significant evidence "
            "supports H1."
        )

    else:

        print(
            "\nDecision: FAIL TO REJECT H0"
        )

        print(
            "Result: Insufficient statistical evidence "
            "to support H1."
        )


def test_mean_trust_score(df):

    scores = pd.to_numeric(
        df["final_trust_score"],
        errors="coerce"
    ).dropna()

    statistic, p_value = ttest_1samp(
        scores,
        popmean=8,
        alternative="greater"
    )

    print_hypothesis_result(
        "HYPOTHESIS 1 — OVERALL TRUSTWORTHINESS",
        "Mean final trust score is <= 8/10.",
        "Mean final trust score is > 8/10.",
        statistic,
        p_value
    )

    print(
        f"Observed Mean Trust Score: "
        f"{scores.mean():.4f}/10"
    )


def test_high_trust_proportion(df):

    total = len(df)

    high_trust = (
        df["trust_level"]
        .astype(str)
        .str.upper()
        .eq("HIGH TRUST")
        .sum()
    )

    result = binomtest(
        high_trust,
        total,
        p=0.80,
        alternative="greater"
    )

    print_hypothesis_result(
        "HYPOTHESIS 2 — HIGH-TRUST RELIABILITY",
        "High-trust response proportion is <= 80%.",
        "High-trust response proportion is > 80%.",
        result.statistic,
        result.pvalue
    )

    print(
        f"High-Trust Responses: "
        f"{high_trust}/{total}"
    )

    print(
        f"Observed Proportion: "
        f"{high_trust / total:.4f}"
    )


def test_evidence_support(df):

    supported = int(
        pd.to_numeric(
            df["supported_claims"],
            errors="coerce"
        ).sum()
    )

    total_claims = int(
        pd.to_numeric(
            df["total_claims"],
            errors="coerce"
        ).sum()
    )

    result = binomtest(
        supported,
        total_claims,
        p=0.85,
        alternative="greater"
    )

    print_hypothesis_result(
        "HYPOTHESIS 3 — EXTERNAL EVIDENCE SUPPORT",
        "Supported claim proportion is <= 85%.",
        "Supported claim proportion is > 85%.",
        result.statistic,
        result.pvalue
    )

    print(
        f"Supported Claims: "
        f"{supported}/{total_claims}"
    )

    print(
        f"Observed Support Rate: "
        f"{supported / total_claims:.4f}"
    )


def test_consistency(df):

    scores = pd.to_numeric(
        df["consistency_score"],
        errors="coerce"
    ).dropna()

    statistic, p_value = ttest_1samp(
        scores,
        popmean=8,
        alternative="greater"
    )

    print_hypothesis_result(
        "HYPOTHESIS 4 — CROSS-MODEL CONSISTENCY",
        "Mean consistency score is <= 8/10.",
        "Mean consistency score is > 8/10.",
        statistic,
        p_value
    )

    print(
        f"Observed Mean Consistency: "
        f"{scores.mean():.4f}/10"
    )


def main():

    print("\n")
    print("=" * 65)
    print("HYPOTHESIS TESTING")
    print("=" * 65)

    df = load_results()

    print(
        f"\nExperiments analyzed: {len(df)}"
    )

    test_mean_trust_score(df)

    test_high_trust_proportion(df)

    test_evidence_support(df)

    test_consistency(df)

    print("\n" + "=" * 65)
    print("HYPOTHESIS TESTING COMPLETE")
    print("=" * 65)


if __name__ == "__main__":

    try:

        main()

    except Exception as e:

        print(
            f"\nHypothesis testing error: {e}"
        )