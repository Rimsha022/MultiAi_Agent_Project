
import pandas as pd

FILE = "research/experiment_results.csv"

df = pd.read_csv(FILE)

count_columns = [
    "supported_claims",
    "contradicted_claims",
    "insufficient_evidence",
    "total_claims",
]

for column in count_columns:
    df[column] = pd.to_numeric(
        df[column], errors="coerce"
    )

if "error_claims" in df.columns:
    df["error_claims"] = pd.to_numeric(
        df["error_claims"], errors="coerce"
    )
else:
    df["error_claims"] = 0

df["classified_claims"] = (
    df["supported_claims"]
    + df["contradicted_claims"]
    + df["insufficient_evidence"]
)

df["unaccounted_claims"] = (
    df["total_claims"]
    - df["classified_claims"]
    - df["error_claims"]
)

print("\nCLAIM COUNT AUDIT")
print("=" * 45)
print("Experiments:", len(df))
print("Total claims:", int(df["total_claims"].sum()))
print("Supported:", int(df["supported_claims"].sum()))
print("Contradicted:", int(df["contradicted_claims"].sum()))
print(
    "Insufficient evidence:",
    int(df["insufficient_evidence"].sum()),
)
print("Errors:", int(df["error_claims"].sum()))
print(
    "Classified claims:",
    int(df["classified_claims"].sum()),
)
print(
    "Unaccounted claims:",
    int(df["unaccounted_claims"].sum()),
)

mismatches = df[
    df["unaccounted_claims"].fillna(0).ne(0)
    | df[count_columns].isna().any(axis=1)
]

print("\nExperiments with mismatched claim counts:")

if mismatches.empty:
    print("No mismatches found.")
else:
    print(
        mismatches[
            [
                "question",
                "supported_claims",
                "contradicted_claims",
                "insufficient_evidence",
                "error_claims",
                "total_claims",
                "unaccounted_claims",
            ]
        ].to_string(index=False)
    )
