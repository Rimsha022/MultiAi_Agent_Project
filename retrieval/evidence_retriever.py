import os

from dotenv import load_dotenv
from tavily import TavilyClient


# =========================================================
# LOAD ENVIRONMENT VARIABLES
# =========================================================

load_dotenv()

tavily_api_key = os.getenv("TAVILY_API_KEY")


# =========================================================
# CREATE TAVILY CLIENT
# =========================================================

if tavily_api_key:

    tavily_client = TavilyClient(
        api_key=tavily_api_key
    )

else:

    tavily_client = None


# =========================================================
# RETRIEVE EVIDENCE FOR ONE CLAIM
# =========================================================

def retrieve_evidence(
    claim,
    max_results=3
):

    if not claim or not claim.strip():

        return []

    if tavily_client is None:

        raise ValueError(
            "TAVILY_API_KEY is missing. "
            "Please add it to your .env file."
        )

    # -----------------------------------------------------
    # Search the web for evidence related to the claim
    # -----------------------------------------------------

    search_response = tavily_client.search(

        query=claim,

        search_depth="advanced",

        max_results=max_results,

        include_answer=False,

        include_raw_content=False
    )


    # -----------------------------------------------------
    # Extract search results
    # -----------------------------------------------------

    raw_results = search_response.get(
        "results",
        []
    )


    evidence_results = []


    # -----------------------------------------------------
    # CLEAN RESULT FORMAT
    # -----------------------------------------------------

    for result in raw_results:

        evidence = {

            "title": result.get(
                "title",
                ""
            ),

            "url": result.get(
                "url",
                ""
            ),

            "content": result.get(
                "content",
                ""
            ),

            "relevance_score": result.get(
                "score",
                0
            )
        }

        evidence_results.append(
            evidence
        )


    return evidence_results


# =========================================================
# RETRIEVE EVIDENCE FOR MULTIPLE CLAIMS
# =========================================================

def retrieve_evidence_for_claims(
    claims,
    max_results=3
):

    all_evidence = []


    for number, claim in enumerate(
        claims,
        start=1
    ):

        try:

            evidence = retrieve_evidence(
                claim,
                max_results=max_results
            )


            all_evidence.append({

                "claim_number": number,

                "claim": claim,

                "evidence": evidence,

                "retrieval_success": True
            })


        except Exception as e:

            all_evidence.append({

                "claim_number": number,

                "claim": claim,

                "evidence": [],

                "retrieval_success": False,

                "error": str(e)
            })


    return all_evidence