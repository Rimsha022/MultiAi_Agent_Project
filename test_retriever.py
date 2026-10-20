from retrieval.evidence_retriever import retrieve_evidence


claim = (
    "IBM Deep Blue defeated world chess "
    "champion Garry Kasparov in 1997."
)


results = retrieve_evidence(
    claim,
    max_results=3
)


print("\nRetrieved Evidence\n")


for number, result in enumerate(
    results,
    start=1
):

    print(
        f"RESULT {number}"
    )

    print(
        "Title:",
        result["title"]
    )

    print(
        "URL:",
        result["url"]
    )

    print(
        "Relevance Score:",
        result["relevance_score"]
    )

    print(
        "Content:",
        result["content"]
    )

    print(
        "\n" + "-" * 70 + "\n"
    )