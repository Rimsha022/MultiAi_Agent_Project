import os
import pandas as pd
import matplotlib.pyplot as plt


RESULTS_FILE = "research/experiment_results.csv"
OUTPUT_DIR = "research/figures"


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


def prepare_output_directory():

    os.makedirs(
        OUTPUT_DIR,
        exist_ok=True
    )


def plot_trust_distribution(df):

    counts = (
        df["trust_level"]
        .value_counts()
    )

    plt.figure(figsize=(8, 5))

    counts.plot(
        kind="bar"
    )

    plt.title(
        "Distribution of Final Trust Levels"
    )

    plt.xlabel("Trust Level")
    plt.ylabel("Number of Responses")

    plt.tight_layout()

    plt.savefig(
        f"{OUTPUT_DIR}/trust_distribution.png",
        dpi=300
    )

    plt.close()


def plot_model_selection(df):

    counts = (
        df["selected_model"]
        .value_counts()
    )

    plt.figure(figsize=(8, 5))

    counts.plot(
        kind="bar"
    )

    plt.title(
        "Model Selection Frequency"
    )

    plt.xlabel("AI Model")
    plt.ylabel("Times Selected")

    plt.tight_layout()

    plt.savefig(
        f"{OUTPUT_DIR}/model_selection.png",
        dpi=300
    )

    plt.close()


def plot_score_components(df):

    score_columns = [
        "quality_score",
        "verification_score",
        "consistency_score",
        "evidence_score",
        "final_trust_score"
    ]

    averages = {}

    for column in score_columns:

        if column in df.columns:

            values = pd.to_numeric(
                df[column],
                errors="coerce"
            )

            averages[column] = (
                values.mean()
            )

    plt.figure(figsize=(10, 5))

    plt.bar(
        averages.keys(),
        averages.values()
    )

    plt.title(
        "Average Validation Score Components"
    )

    plt.xlabel("Evaluation Component")
    plt.ylabel("Average Score (/10)")

    plt.ylim(0, 10)

    plt.xticks(
        rotation=25,
        ha="right"
    )

    plt.tight_layout()

    plt.savefig(
        f"{OUTPUT_DIR}/score_components.png",
        dpi=300
    )

    plt.close()


def plot_category_performance(df):

    if "category" not in df.columns:
        return

    temp = df.copy()

    temp["final_trust_score"] = (
        pd.to_numeric(
            temp["final_trust_score"],
            errors="coerce"
        )
    )

    averages = (
        temp
        .groupby("category")[
            "final_trust_score"
        ]
        .mean()
        .sort_values(
            ascending=False
        )
    )

    plt.figure(figsize=(10, 6))

    averages.plot(
        kind="bar"
    )

    plt.title(
        "Average Trust Score by Question Category"
    )

    plt.xlabel("Question Category")
    plt.ylabel("Average Trust Score (/10)")

    plt.ylim(0, 10)

    plt.xticks(
        rotation=30,
        ha="right"
    )

    plt.tight_layout()

    plt.savefig(
        f"{OUTPUT_DIR}/category_performance.png",
        dpi=300
    )

    plt.close()


def main():

    try:

        prepare_output_directory()

        df = load_results()

        plot_trust_distribution(df)
        plot_model_selection(df)
        plot_score_components(df)
        plot_category_performance(df)

        print("\nResearch visualizations generated.")
        print(
            f"Saved to: {OUTPUT_DIR}"
        )

    except Exception as e:

        print(
            f"Visualization error: {e}"
        )


if __name__ == "__main__":
    main()