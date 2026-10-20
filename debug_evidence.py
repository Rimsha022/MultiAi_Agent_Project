
import json
import pandas as pd

from dotenv import load_dotenv
from groq import Groq

from pipeline import verify_external_evidence
from verification.claim_extractor import extract_claims

load_dotenv()

client = Groq()

df = pd.read_csv("research/experiment_results.csv")

row = df[
    df["question"].str.contains(
        "smallest country",
        case=False,
        na=False
    )
].iloc[-1]

question = row["question"]

print("Question:", question)
print("\nStored CSV counts:")
print("Total claims:", row["total_claims"])
print("Supported:", row["supported_claims"])
print("Contradicted:", row["contradicted_claims"])
print("Insufficient evidence:", row["insufficient_evidence"])

print("\nExtracting claims from the original answer...")

# IMPORTANT:
# Use the original answer from your pipeline if available.
# Do not substitute the question for the answer.
print(
    "\nThe CSV alone does not contain enough information "
    "to reproduce the original claim verification."
)
print(
    "Next, inspect where verify_external_evidence() is called "
    "inside pipeline.py."
)
