import os
import sys
import time
import argparse
import pandas as pd

# Add project root directory to Python path
PROJECT_ROOT = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from pipeline import run_validation_pipeline


BENCHMARK_FILE = "research/benchmark_questions.csv"
RESULTS_FILE = "research/experiment_results.csv"


# ---------------------------------------------------------
# LOAD BENCHMARK DATASET
# ---------------------------------------------------------

def load_benchmark_questions():
    """
    Load and validate the benchmark dataset.
    """

    if not os.path.exists(BENCHMARK_FILE):
        raise FileNotFoundError(
            f"Benchmark file not found: {BENCHMARK_FILE}"
        )

    df = pd.read_csv(BENCHMARK_FILE)

    required_columns = {
        "question_id",
        "category",
        "question"
    }

    missing_columns = required_columns - set(df.columns)

    if missing_columns:
        raise ValueError(
            "Missing required benchmark columns: "
            + ", ".join(missing_columns)
        )

    return df


# ---------------------------------------------------------
# LOAD EXISTING RESULTS
# ---------------------------------------------------------

def load_existing_results():
    """
    Load previous experiment results if available.
    """

    if not os.path.exists(RESULTS_FILE):
        return pd.DataFrame()

    try:
        return pd.read_csv(RESULTS_FILE)

    except Exception:
        return pd.DataFrame()


# ---------------------------------------------------------
# FIND COMPLETED QUESTIONS
# ---------------------------------------------------------

def get_completed_questions():
    """
    Return questions already successfully logged.
    """

    results_df = load_existing_results()

    if results_df.empty:
        return set()

    if "question" not in results_df.columns:
        return set()

    return set(
        results_df["question"]
        .dropna()
        .astype(str)
        .str.strip()
    )


# ---------------------------------------------------------
# FIND PENDING QUESTIONS
# ---------------------------------------------------------

def get_pending_questions():
    """
    Return benchmark questions not yet completed.
    """

    benchmark_df = load_benchmark_questions()

    completed_questions = get_completed_questions()

    benchmark_df["question_clean"] = (
        benchmark_df["question"]
        .astype(str)
        .str.strip()
    )

    pending_df = benchmark_df[
        ~benchmark_df["question_clean"].isin(
            completed_questions
        )
    ].copy()

    pending_df = pending_df.drop(
        columns=["question_clean"]
    )

    return pending_df


# ---------------------------------------------------------
# DISPLAY EXPERIMENT STATUS
# ---------------------------------------------------------

def show_experiment_status():

    benchmark_df = load_benchmark_questions()

    completed_questions = get_completed_questions()

    total_questions = len(benchmark_df)

    completed = benchmark_df[
        benchmark_df["question"]
        .astype(str)
        .str.strip()
        .isin(completed_questions)
    ].shape[0]

    pending = total_questions - completed

    print("\nBenchmark Experiment Status")
    print("---------------------------")

    print(
        f"Total benchmark questions: {total_questions}"
    )

    print(
        f"Completed experiments: {completed}"
    )

    print(
        f"Pending experiments: {pending}"
    )

    if total_questions > 0:

        progress = (
            completed / total_questions
        ) * 100

        print(
            f"Progress: {progress:.2f}%"
        )


# ---------------------------------------------------------
# CHECK RATE LIMIT ERROR
# ---------------------------------------------------------

def is_rate_limit_error(error_message):

    if not error_message:
        return False

    text = str(error_message).lower()

    keywords = [
        "429",
        "rate limit",
        "rate_limit",
        "rate_limit_exceeded",
        "tokens per minute",
        "tokens per day"
    ]

    return any(
        keyword in text
        for keyword in keywords
    )


# ---------------------------------------------------------
# RUN SINGLE EXPERIMENT
# ---------------------------------------------------------
def run_single_experiment(
    question,
    category,
    max_retries=3
):
    """
    Run one benchmark experiment.

    An experiment is considered valid only if the
    main pipeline and required verification stages
    complete successfully.
    """

    for attempt in range(
        1,
        max_retries + 1
    ):

        try:

            result = run_validation_pipeline(
                question,
                category,
                True
            )

            if result is None:
                raise RuntimeError(
                    "Pipeline returned None."
                )

            # -----------------------------------------
            # MAIN PIPELINE STATUS
            # -----------------------------------------

            pipeline_success = result.get(
                "success",
                False
            )

            pipeline_error = result.get(
                "error"
            )

            # -----------------------------------------
            # VERIFICATION STATUS
            # -----------------------------------------

            verification = result.get(
                "verification",
                {}
            )

            if verification is None:
                verification = {}

            verification_error = (
                verification.get("error")
            )

            # -----------------------------------------
            # CHECK FOR RATE LIMITS ANYWHERE
            # -----------------------------------------

            rate_limit_detected = (
                is_rate_limit_error(
                    pipeline_error
                )
                or
                is_rate_limit_error(
                    verification_error
                )
            )

            if rate_limit_detected:

                if attempt < max_retries:

                    wait_time = (
                        30 * attempt
                    )

                    print(
                        "API rate limit detected. "
                        f"Retrying in {wait_time} "
                        "seconds..."
                    )

                    time.sleep(
                        wait_time
                    )

                    continue

                return {
                    "success": False,
                    "error": (
                        "Experiment incomplete because "
                        "API rate limit/quota was reached."
                    ),
                    "incomplete": True
                }

            # -----------------------------------------
            # MAIN PIPELINE FAILURE
            # -----------------------------------------

            if not pipeline_success:

                return {
                    "success": False,
                    "error": (
                        pipeline_error
                        or
                        "Validation pipeline failed."
                    ),
                    "incomplete": True
                }

            # -----------------------------------------
            # VERIFICATION FAILURE
            # -----------------------------------------

            if verification_error:

                return {
                    "success": False,
                    "error": (
                        "Verification stage failed: "
                        + str(
                            verification_error
                        )
                    ),
                    "incomplete": True
                }

            # -----------------------------------------
            # CHECK REQUIRED OUTPUTS
            # -----------------------------------------

            selected_model = result.get(
                "selected_model"
            )

            trust_score = result.get(
                "final_trust_score"
            )

            trust_level = result.get(
                "trust_level"
            )

            if (
                not selected_model
                or trust_score is None
                or not trust_level
            ):

                return {
                    "success": False,
                    "error": (
                        "Experiment incomplete: "
                        "required final outputs "
                        "are missing."
                    ),
                    "incomplete": True
                }

            # -----------------------------------------
            # VALID EXPERIMENT
            # -----------------------------------------

            result[
                "benchmark_valid"
            ] = True

            return result

        except Exception as e:

            error_text = str(e)

            if is_rate_limit_error(
                error_text
            ):

                if attempt < max_retries:

                    wait_time = (
                        30 * attempt
                    )

                    print(
                        "API rate limit detected. "
                        f"Retrying in {wait_time} "
                        "seconds..."
                    )

                    time.sleep(
                        wait_time
                    )

                    continue

            return {
                "success": False,
                "error": error_text,
                "incomplete": True
            }

    return {
        "success": False,
        "error": (
            "Maximum retry attempts reached."
        ),
        "incomplete": True
    }

# ---------------------------------------------------------
# RUN BENCHMARK
# ---------------------------------------------------------

def run_benchmark(
    limit=None,
    delay=20
):

    pending_df = get_pending_questions()

    if pending_df.empty:

        print(
            "\nAll benchmark experiments "
            "have already been completed."
        )

        return

    if limit is not None:

        pending_df = pending_df.head(
            limit
        )

    total_to_run = len(
        pending_df
    )

    print(
        f"\nStarting {total_to_run} "
        f"benchmark experiment(s)..."
    )

    print(
        "===================================="
    )

    successful = 0
    failed = 0

    for experiment_number, (_, row) in enumerate(
        pending_df.iterrows(),
        start=1
    ):

        question_id = str(
            row["question_id"]
        )

        category = str(
            row["category"]
        )

        question = str(
            row["question"]
        ).strip()

        print(
            f"\nExperiment "
            f"{experiment_number}/{total_to_run}"
        )

        print(
            f"Question ID: {question_id}"
        )

        print(
            f"Category: {category}"
        )

        print(
            f"Question: {question}"
        )

        print(
            "Running validation pipeline..."
        )

        result = run_single_experiment(
            question=question,
            category=category
        )

        if (
            result.get("success", False)
            and result.get(
                "benchmark_valid",
                False
            )
        ):

            successful += 1

            print(
                "Status: SUCCESS"
            )

            print(
                "Selected Model:",
                result.get(
                    "selected_model",
                    "N/A"
                )
            )

            trust_score = result.get(
                "final_trust_score"
            )

            if trust_score is not None:

                print(
                    f"Final Trust Score: "
                    f"{trust_score:.2f}/10"
                )

            print(
                "Trust Level:",
                result.get(
                    "trust_level",
                    "N/A"
                )
            )

        else:

            failed += 1

            if result.get("incomplete", False):
                print("Status: INCOMPLETE")
            else:
                print("Status: FAILED")

            print(
                "Error:",
                result.get(
                    "error",
                    "Unknown error"
                )
            )

        # Avoid unnecessary wait after final experiment
        if experiment_number < total_to_run:

            print(
                f"\nWaiting {delay} seconds "
                "before next experiment..."
            )

            time.sleep(
                delay
            )

    print(
        "\n===================================="
    )

    print(
        "Benchmark Run Complete"
    )

    print(
        "===================================="
    )

    print(
        f"Successful: {successful}"
    )

    print(
        f"Failed: {failed}"
    )

    print(
        f"Attempted: {total_to_run}"
    )

    print()

    show_experiment_status()


# ---------------------------------------------------------
# COMMAND LINE
# ---------------------------------------------------------

def main():

    parser = argparse.ArgumentParser(
        description=(
            "Run benchmark experiments "
            "for the Multi-Agent AI system."
        )
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help=(
            "Maximum number of pending "
            "questions to run."
        )
    )

    parser.add_argument(
        "--delay",
        type=int,
        default=20,
        help=(
            "Delay in seconds between "
            "experiments."
        )
    )

    parser.add_argument(
        "--status",
        action="store_true",
        help=(
            "Only display benchmark "
            "experiment status."
        )
    )

    args = parser.parse_args()

    if args.status:

        show_experiment_status()

        pending_df = (
            get_pending_questions()
        )

        if not pending_df.empty:

            print(
                "\nNext experiments:"
            )

            print(
                pending_df[
                    [
                        "question_id",
                        "category",
                        "question"
                    ]
                ]
                .head(10)
                .to_string(
                    index=False
                )
            )

        return

    run_benchmark(
        limit=args.limit,
        delay=args.delay
    )


if __name__ == "__main__":

    try:

        main()

    except KeyboardInterrupt:

        print(
            "\nBenchmark experiment "
            "stopped by user."
        )

    except Exception as e:

        print(
            f"\nBenchmark runner error: {e}"
        )