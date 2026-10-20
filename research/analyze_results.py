import os
import pandas as pd


RESULTS_FILE = "research/experiment_results.csv"


def load_results():

    if not os.path.exists(RESULTS_FILE):
        raise FileNotFoundError(
            f"Results file not found: {RESULTS_FILE}"
        )

    df = pd.read_csv(RESULTS_FILE)

    if df.empty:
        raise ValueError(
            "Experiment results file is empty."
        )

    return df


def show_overall_summary(df):

    print("\nRESEARCH EXPERIMENT SUMMARY")
    print("=" * 45)

    print(f"Total experiments: {len(df)}")

    if "final_trust_score" in df.columns:

        scores = pd.to_numeric(
            df["final_trust_score"],
            errors="coerce"
        )

        print(
            f"Average Trust Score: "
            f"{scores.mean():.2f}/10"
        )

        print(
            f"Highest Trust Score: "
            f"{scores.max():.2f}/10"
        )

        print(
            f"Lowest Trust Score: "
            f"{scores.min():.2f}/10"
        )


def show_trust_distribution(df):

    if "trust_level" not in df.columns:
        return

    print("\nTRUST LEVEL DISTRIBUTION")
    print("=" * 45)

    counts = (
        df["trust_level"]
        .value_counts()
    )

    for level, count in counts.items():

        percentage = (
            count / len(df)
        ) * 100

        print(
            f"{level}: "
            f"{count} "
            f"({percentage:.2f}%)"
        )


def show_model_performance(df):

    if "selected_model" not in df.columns:
        return

    print("\nMODEL SELECTION FREQUENCY")
    print("=" * 45)

    counts = (
        df["selected_model"]
        .value_counts()
    )

    print(counts.to_string())


def show_average_components(df):

    columns = [
        "quality_score",
        "verification_score",
        "consistency_score",
        "evidence_score",
        "final_trust_score"
    ]

    available = [
        column
        for column in columns
        if column in df.columns
    ]

    print("\nAVERAGE SCORE COMPONENTS")
    print("=" * 45)

    for column in available:

        values = pd.to_numeric(
            df[column],
            errors="coerce"
        )

        print(
            f"{column}: "
            f"{values.mean():.2f}"
        )


def show_evidence_summary(df):

    evidence_columns = [
        "supported_claims",
        "contradicted_claims",
        "insufficient_evidence",
        "total_claims"
    ]

    if not all(
        column in df.columns
        for column in evidence_columns
    ):
        return

    print("\nEXTERNAL EVIDENCE SUMMARY")
    print("=" * 45)

    for column in evidence_columns:

        values = pd.to_numeric(
            df[column],
            errors="coerce"
        )

        print(
            f"{column}: "
            f"{values.sum():.0f}"
        )


def show_category_performance(df):

    if (
        "category" not in df.columns
        or
        "final_trust_score" not in df.columns
    ):
        return

    temp = df.copy()

    temp["final_trust_score"] = (
        pd.to_numeric(
            temp["final_trust_score"],
            errors="coerce"
        )
    )

    category_summary = (
        temp
        .groupby("category")[
            "final_trust_score"
        ]
        .agg(["count", "mean"])
        .sort_values(
            "mean",
            ascending=False
        )
    )

    print("\nCATEGORY PERFORMANCE")
    print("=" * 45)

    print(
        category_summary.to_string()
    )


def main():

    try:

        df = load_results()

        show_overall_summary(df)

        show_trust_distribution(df)

        show_model_performance(df)

        show_average_components(df)

        show_evidence_summary(df)

        show_category_performance(df)

    except Exception as e:

        print(
            f"Analysis error: {e}"
        )


if __name__ == "__main__":
    main()