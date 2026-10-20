import os

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from google import genai
from groq import Groq

from evaluation.similarity import calculate_similarity
from evaluation.evaluator import evaluate_response
from verification.verifier import verify_answer
from verification.claim_extractor import extract_claims

from retrieval.evidence_retriever import retrieve_evidence
from retrieval.evidence_verifier import verify_claim_with_evidence
from agents.synthesis_agent import synthesize_verified_answer
from research.experiment_logger import log_experiment

from evaluation.scoring import (
    calculate_quality_scores,
    rank_models,
    WEIGHTS
)


# =========================================================
# 1. STREAMLIT PAGE CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="Multi-Agent AI Validation",
    layout="wide"
)


# =========================================================
# 2. LOAD API KEYS
# =========================================================

load_dotenv()

google_api_key = os.getenv("GOOGLE_API_KEY")
groq_api_key = os.getenv("GROQ_API_KEY")


# =========================================================
# 3. CHECK API KEYS
# =========================================================

if not google_api_key:
    st.error(
        "GOOGLE_API_KEY is missing. "
        "Please add it to your .env file."
    )
    st.stop()

if not groq_api_key:
    st.error(
        "GROQ_API_KEY is missing. "
        "Please add it to your .env file."
    )
    st.stop()


# =========================================================
# 4. CREATE API CLIENTS
# =========================================================

gemini_client = genai.Client(
    api_key=google_api_key
)

groq_client = Groq(
    api_key=groq_api_key
)


# =========================================================
# 5. APPLICATION HEADER
# =========================================================

st.title(
    "Multi-Agent AI for Cross-Model Validation"
)

st.write(
    "This system generates independent responses from "
    "multiple AI models and compares them for "
    "cross-model validation."
)

st.divider()


# =========================================================
# 6. USER INPUT / RESEARCH EXPERIMENT MODE
# =========================================================

BENCHMARK_FILE = "research/benchmark_questions.csv"

input_mode = st.radio(
    "Question Mode:",
    ["Manual Question", "Research Experiment"],
    horizontal=True
)

category = "Manual"

if input_mode == "Research Experiment":

    try:
        benchmark_df = pd.read_csv(BENCHMARK_FILE)

        required_benchmark_columns = {
            "question_id",
            "category",
            "question"
        }

        if not required_benchmark_columns.issubset(
            benchmark_df.columns
        ):
            st.error(
                "benchmark_questions.csv must contain "
                "question_id, category, and question columns."
            )
            st.stop()

        categories = benchmark_df[
            "category"
        ].dropna().unique().tolist()

        category = st.selectbox(
            "Select benchmark category:",
            categories
        )

        category_questions = benchmark_df[
            benchmark_df["category"] == category
        ].copy()

        question_options = {
            f"{row['question_id']} — {row['question']}":
                row["question"]
            for _, row in category_questions.iterrows()
        }

        selected_question_label = st.selectbox(
            "Select benchmark question:",
            list(question_options.keys())
        )

        user_query = question_options[
            selected_question_label
        ]

        st.info(
            f"Experiment Category: {category}"
        )

    except FileNotFoundError:
        st.error(
            "research/benchmark_questions.csv was not found."
        )
        st.stop()

    except Exception as e:
        st.error(
            f"Could not load benchmark questions: {e}"
        )
        st.stop()

else:

    user_query = st.text_area(
        "Enter your question:",
        placeholder=(
            "Example: What is machine learning?"
        ),
        height=100
    )


# =========================================================
# 7. GENERATE BUTTON
# =========================================================

if st.button(
    "Generate Responses",
    type="primary"
):

    # =====================================================
    # CHECK EMPTY QUERY
    # =====================================================

    if not user_query.strip():

        st.warning(
            "Please enter a question."
        )

    else:

        # =================================================
        # 8. COMMON PROMPT FOR ALL MODELS
        # =================================================

        agent_prompt = f"""
Answer the following question accurately, clearly,
and completely.

Instructions:

- Answer only what is asked.
- Keep the final response between approximately
  250 and 400 words.
- Include the important information required to
  answer the question.
- Avoid unnecessary repetition.
- Be factual and objective.
- Use headings or bullet points only when useful.
- Do not expose internal reasoning or chain-of-thought.
- Make sure the final answer is complete and does
  not end in the middle of a sentence, list, or table.

User Question:

{user_query}
"""


        # =================================================
        # INITIALIZE RESPONSE VARIABLES
        # =================================================

        gemini_text = None
        gpt_text = None
        qwen_text = None

        gpt_finish_reason = None
        qwen_finish_reason = None


        # =================================================
        # 9. GEMINI AGENT
        # =================================================

        st.header("Model Responses")

        st.subheader("Gemini Response")

        try:

            with st.spinner(
                "Gemini is generating a response..."
            ):

                gemini_response = (
                    gemini_client.models.generate_content(
                        model="gemini-3-flash-preview",
                        contents=agent_prompt
                    )
                )

                gemini_text = gemini_response.text
                gemini_finish_reason = (
                    gemini_response
                    .candidates[0]
                    .finish_reason
                )


            if gemini_text:

                st.markdown(
                    gemini_text
                )

            else:

                st.warning(
                    "Gemini returned an empty response."
                )

        
        except Exception as e:

            error_message = str(e)

            # Show the actual error for debugging
            st.error(f"Gemini API Error: {error_message}")

            if (
                "429" in error_message
                or "RESOURCE_EXHAUSTED" in error_message
                or "quota" in error_message.lower()
            ):

                st.warning(
                    "Gemini quota may have been reached. "
                    "The system will continue using other available models."
                )

            gemini_text = None

        st.divider()


        # =================================================
        # 10. GPT-OSS AGENT
        # =================================================

        st.subheader("GPT-OSS Response")

        try:

            with st.spinner(
                "GPT-OSS is generating a response..."
            ):

                gpt_response = (
                    groq_client.chat.completions.create(

                        model="openai/gpt-oss-120b",

                        messages=[
                            {
                                "role": "user",
                                "content": agent_prompt
                            }
                        ],

                        temperature=0.7,

                        max_tokens=4096
                    )
                )


                gpt_text = (
                    gpt_response
                    .choices[0]
                    .message
                    .content
                )


                gpt_finish_reason = (
                    gpt_response
                    .choices[0]
                    .finish_reason
                )


            if gpt_text:

                st.markdown(
                    gpt_text
                )

            else:

                st.warning(
                    "GPT-OSS returned an empty response."
                )


        except Exception as e:

            st.error(
                f"GPT-OSS Error: {e}"
            )


        st.divider()

        # =================================================
        # QWEN AGENT
        # =================================================

        st.subheader("Qwen Response")

        try:

            with st.spinner(
                "Qwen is generating a response..."
            ):

                qwen_response = (
                    groq_client.chat.completions.create(

                        model="qwen/qwen3.8-27b",

                        messages=[
                            {
                                "role": "user",
                                "content": agent_prompt
                            }
                        ],

                        # Disable thinking/reasoning mode
                        reasoning_effort="none",

                        temperature=0.7,

                        max_tokens=2000
                    )
                )

                qwen_text = (
                    qwen_response
                    .choices[0]
                    .message
                    .content
                )

                qwen_finish_reason = (
                    qwen_response
                    .choices[0]
                    .finish_reason
                )


            if qwen_text:

                st.markdown(qwen_text)

            else:

                st.warning(
                    "Qwen returned an empty response."
                )

        except Exception as e:

            st.error(
                f"Qwen Error: {e}"
            )
        
        # =================================================
        # 12. RESPONSE COLLECTION LAYER
        # =================================================

        responses = {

            "Gemini": gemini_text,

            "GPT-OSS": gpt_text,

            "Qwen": qwen_text
        }


        # Remove failed or empty responses
        responses = {

            model: response

            for model, response
            in responses.items()

            if response is not None
            and response.strip()
        }


        # =================================================
        # 13. CROSS-MODEL ANALYSIS
        # =================================================

        st.divider()

        st.header(
            "Cross-Model Analysis"
        )


        # =================================================
        # CHECK RESPONSE COUNT
        # =================================================

        if len(responses) < 2:

            st.warning(
                "At least two successful model responses "
                "are required for cross-model analysis."
            )

        else:

            # =============================================
            # 14. SEMANTIC SIMILARITY
            # =============================================

            st.subheader(
                "Semantic Similarity"
            )

            st.write(
                "The following matrix measures the "
                "semantic similarity between the "
                "responses generated by the models."
            )


            try:

                with st.spinner(
                    "Calculating semantic similarity..."
                ):

                    (
                        model_names,
                        similarity_matrix

                    ) = calculate_similarity(
                        responses
                    )


                # =========================================
                # CREATE SIMILARITY DATAFRAME
                # =========================================

                similarity_df = pd.DataFrame(

                    similarity_matrix,

                    index=model_names,

                    columns=model_names
                )


                # =========================================
                # DISPLAY SIMILARITY MATRIX
                # =========================================

                st.dataframe(

                    similarity_df.round(3),

                    use_container_width=True
                )


                # =========================================
                # 15. CROSS-MODEL CONSISTENCY
                # =========================================

                st.subheader(
                    "Cross-Model Consistency Scores"
                )


                consistency_scores = {}


                for i, model in enumerate(
                    model_names
                ):

                    other_scores = []


                    for j in range(
                        len(model_names)
                    ):

                        # Ignore similarity of a model
                        # with itself
                        if i != j:

                            other_scores.append(
                                similarity_matrix[i][j]
                            )


                    # Calculate average agreement
                    # with the other models

                    if other_scores:

                        average_similarity = (
                            sum(other_scores)
                            / len(other_scores)
                        )

                    else:

                        average_similarity = 0


                    consistency_scores[model] = (
                        average_similarity
                    )


                # =========================================
                # CREATE CONSISTENCY DATAFRAME
                # =========================================

                consistency_df = pd.DataFrame({

                    "Model":
                        list(
                            consistency_scores.keys()
                        ),

                    "Consistency Score":
                        [
                            round(score, 3)

                            for score
                            in consistency_scores.values()
                        ],

                    "Consistency (%)":
                        [
                            round(
                                score * 100,
                                2
                            )

                            for score
                            in consistency_scores.values()
                        ]
                })


                # =========================================
                # DISPLAY CONSISTENCY SCORES
                # =========================================

                st.dataframe(

                    consistency_df,

                    use_container_width=True,

                    hide_index=True
                )


                # =========================================
                # 16. HIGHEST CROSS-MODEL CONSISTENCY
                # =========================================

                if consistency_scores:

                    highest_consistency_score = max(
                        consistency_scores.values()
                    )

                    highest_consistency_models = [
                        model
                        for model, score in consistency_scores.items()
                        if abs(score - highest_consistency_score) < 1e-6
                    ]

                    if len(highest_consistency_models) > 1:

                        tied_models = ", ".join(
                            highest_consistency_models
                        )

                        st.write(
                            "**Highest Cross-Model Consistency:** "
                            f"Tie between {tied_models} "
                            f"({highest_consistency_score * 100:.2f}%)"
                        )

                    else:

                        highest_consistency_model = (
                            highest_consistency_models[0]
                        )

                        st.write(
                            "**Highest Cross-Model Consistency:** "
                            f"{highest_consistency_model} "
                            f"({highest_consistency_score * 100:.2f}%)"
                        )

                st.info(
                    "Cross-model consistency measures semantic agreement "
                    "between model responses. A high consistency score does "
                    "not by itself prove factual correctness, so consistency "
                    "is used as one component of the final multi-criteria "
                    "evaluation score."
                )

                # =================================================
                # 17. EVALUATION AGENT
                # =================================================

                st.divider()

                st.header("Evaluation Agent")

                st.write(
                    "Each response is independently evaluated "
                    "using multiple quality criteria."
                )

                # Dictionary for storing evaluation results
                evaluation_results = {}


                # =================================================
                # 18. EVALUATE EACH MODEL RESPONSE
                # =================================================

                with st.spinner(
                    "Evaluation Agent is scoring the responses..."
                ):

                    for model, response_text in responses.items():

                        try:

                            scores = evaluate_response(
                                groq_client,
                                user_query,
                                response_text
                            )

                            evaluation_results[model] = scores

                        except Exception as e:

                            st.error(
                                f"Evaluation failed for {model}: {e}"
                            )


                # =================================================
                # 19. ADD CROSS-MODEL CONSISTENCY SCORE
                # =================================================

                for model in evaluation_results:

                    if model in consistency_scores:

                        # Convert 0-1 similarity score
                        # into 0-10 evaluation score

                        evaluation_results[model][
                            "consistency"
                        ] = consistency_scores[model] * 10


                # =================================================
                # 20. DISPLAY MULTI-CRITERIA EVALUATION TABLE
                # =================================================

                if evaluation_results:

                    st.subheader(
                        "Multi-Criteria Evaluation"
                    )

                    # Convert dictionary into DataFrame
                    evaluation_df = pd.DataFrame(
                        evaluation_results
                    ).T


                    # Required columns
                    required_columns = [
                        "relevance",
                        "completeness",
                        "justification",
                        "context_awareness",
                        "conciseness",
                        "consistency"
                    ]


                    # Check that all columns exist
                    available_columns = [
                        column
                        for column in required_columns
                        if column in evaluation_df.columns
                    ]


                    evaluation_df = evaluation_df[
                        available_columns
                    ]


                    # Rename columns for display
                    column_names = {
                        "relevance": "Relevance",
                        "completeness": "Completeness",
                        "justification": "Justification Quality",
                        "context_awareness": "Context Awareness",
                        "conciseness": "Conciseness",
                        "consistency": "Cross-Model Consistency"
                    }

                    evaluation_df = evaluation_df.rename(
                        columns=column_names
                    )


                    # Display table
                    st.dataframe(
                        evaluation_df.round(2),
                        use_container_width=True
                    )


                    # =================================================
                    # 21. SHOW INDIVIDUAL MODEL SCORES
                    # =================================================

                    st.subheader("Evaluation Summary")

                    for model in evaluation_results:

                        with st.expander(
                            f"{model} Evaluation"
                        ):

                            scores = evaluation_results[model]

                            st.write(
                                f"**Relevance:** "
                                f"{scores.get('relevance', 0):.2f}/10"
                            )

                            st.write(
                                f"**Completeness:** "
                                f"{scores.get('completeness', 0):.2f}/10"
                            )

                            st.write(
                                f"**Justification Quality:** "
                                f"{scores.get('justification', 0):.2f}/10"
                            )

                            st.write(
                                f"**Context Awareness:** "
                                f"{scores.get('context_awareness', 0):.2f}/10"
                            )

                            st.write(
                                f"**Conciseness:** "
                                f"{scores.get('conciseness', 0):.2f}/10"
                            )

                            st.write(
                                f"**Cross-Model Consistency:** "
                                f"{scores.get('consistency', 0):.2f}/10"
                            )


                    # =================================================
                    # 22. SCORING ENGINE
                    # =================================================

                    st.divider()

                    st.header("Scoring Engine")

                    st.write(
                        "The system calculates a weighted quality score "
                        "for each model using the multi-criteria "
                        "evaluation results."
                    )


                    # =================================================
                    # DISPLAY SCORING WEIGHTS
                    # =================================================

                    st.subheader("Evaluation Weights")

                    weights_df = pd.DataFrame({

                        "Criterion": [
                            "Relevance",
                            "Completeness",
                            "Justification Quality",
                            "Context Awareness",
                            "Conciseness",
                            "Cross-Model Consistency"
                        ],

                        "Weight (%)": [
                            WEIGHTS["relevance"] * 100,
                            WEIGHTS["completeness"] * 100,
                            WEIGHTS["justification"] * 100,
                            WEIGHTS["context_awareness"] * 100,
                            WEIGHTS["conciseness"] * 100,
                            WEIGHTS["consistency"] * 100
                        ]
                    })

                    st.dataframe(
                        weights_df,
                        use_container_width=True,
                        hide_index=True
                    )


                    # =================================================
                    # CALCULATE QUALITY SCORES
                    # =================================================

                    quality_scores = calculate_quality_scores(
                        evaluation_results
                    )


                    # =================================================
                    # RANK MODELS
                    # =================================================

                    ranked_models = rank_models(
                        quality_scores
                    )


                    # =================================================
                    # CREATE RANKING TABLE
                    # =================================================

                    ranking_data = []

                    for rank, (model, score) in enumerate(
                        ranked_models,
                        start=1
                    ):

                        ranking_data.append({

                            "Rank": rank,

                            "Model": model,

                            "Quality Score": round(
                                score,
                                2
                            ),

                            "Quality (%)": round(
                                score * 10,
                                2
                            )
                        })


                    ranking_df = pd.DataFrame(
                        ranking_data
                    )


                    # =================================================
                    # DISPLAY RANKING
                    # =================================================

                    st.subheader("Model Ranking")

                    st.dataframe(
                        ranking_df,
                        use_container_width=True,
                        hide_index=True
                    )


                    # =================================================
                    # 23. BEST ANSWER SELECTION
                    # =================================================

                    if ranked_models:

                        best_model = ranked_models[0][0]

                        best_score = ranked_models[0][1]

                        best_response = responses[
                            best_model
                        ]

                        st.divider()

                        st.header(
                            "Best Answer Selection"
                        )

                        st.success(
                            f"Selected Model: {best_model}"
                        )


                        # =================================================
                        # DISPLAY QUALITY SCORE
                        # =================================================

                        col1, col2 = st.columns(2)

                        with col1:

                            st.metric(
                                "Quality Score",
                                f"{best_score:.2f}/10"
                            )

                        with col2:

                            st.metric(
                                "Quality Percentage",
                                f"{best_score * 10:.2f}%"
                            )


                        # =================================================
                        # DISPLAY SELECTED RESPONSE
                        # =================================================

                        st.subheader(
                            "Selected Response"
                        )

                        st.markdown(
                            best_response
                        )

                        st.divider()

                        # =================================================
                        # 24. VERIFICATION AGENT
                        # =================================================

                        st.header("Verification Agent")

                        # Always initialize these variables before use.
                        verification = {}
                        extracted_claims = []
                        evidence_results = []
                        verification_score = None
                        confidence = None
                        verification_available = False

                        # =================================================
                        # VERIFICATION SCORE AND CONFIDENCE
                        # =================================================

                        try:
                            with st.spinner(
                                "Verifying factual reliability..."
                            ):
                                verification = verify_answer(
                                    groq_client,
                                    user_query,
                                    best_response
                                )

                            verification_score = verification.get(
                                "verification_score"
                            )

                            confidence = verification.get(
                                "confidence"
                            )

                            verification_available = (
                                verification_score is not None
                            )

                            col1, col2 = st.columns(2)

                            with col1:
                                st.metric(
                                    label="Verification Score",
                                    value=(
                                        f"{verification_score:.2f}/10"
                                        if verification_available
                                        else "Unavailable"
                                    )
                                )

                            with col2:
                                st.metric(
                                    label="Confidence",
                                    value=(
                                        f"{confidence:.2f}%"
                                        if confidence is not None
                                        else "Unavailable"
                                    )
                                )

                        except Exception as e:
                            verification = {}
                            verification_score = None
                            confidence = None
                            verification_available = False

                            st.warning(
                                "The Verification Agent is unavailable for this "
                                "run. It will be excluded from the trust score "
                                "and the remaining weights will be normalized. "
                                f"Error: {e}"
                            )

                        # =================================================
                        # 25. FACTUAL CLAIM EXTRACTION
                        # =================================================

                        st.subheader("Factual Claim Extraction")

                        try:
                            with st.spinner(
                                "Extracting verifiable factual claims..."
                            ):
                                extracted_claims = extract_claims(
                                    groq_client,
                                    user_query,
                                    best_response
                                )

                            if extracted_claims:
                                st.write(
                                    f"Detected **{len(extracted_claims)} "
                                    f"verifiable factual claims**."
                                )

                                for number, claim in enumerate(
                                    extracted_claims,
                                    start=1
                                ):
                                    st.write(
                                        f"**Claim {number}:** {claim}"
                                    )

                            else:
                                st.info(
                                    "No externally verifiable factual "
                                    "claims were detected."
                                )

                        except Exception as e:
                            extracted_claims = []
                            st.warning(
                                "The claim extraction agent could not "
                                f"process this response: {e}"
                            )

                        # =================================================
                        # 26. EXTERNAL EVIDENCE VERIFICATION
                        # =================================================

                        st.subheader("External Evidence Verification")

                        if extracted_claims:

                            with st.spinner(
                                "Retrieving and verifying external evidence..."
                            ):

                                for claim in extracted_claims:

                                    try:
                                        # Retrieve up to three sources
                                        evidence = retrieve_evidence(
                                            claim,
                                            max_results=3
                                        )

                                        # Verify the claim against the evidence
                                        if evidence:
                                            evidence_verification = (
                                                verify_claim_with_evidence(
                                                    client=groq_client,
                                                    claim=claim,
                                                    evidence=evidence
                                                )
                                            )
                                        else:
                                            evidence_verification = {
                                                "status": "INSUFFICIENT_EVIDENCE",
                                                "confidence": 0,
                                                "reason": (
                                                    "No relevant external "
                                                    "evidence was retrieved."
                                                )
                                            }

                                        evidence_results.append({
                                            "claim": claim,
                                            "status": (
                                                evidence_verification.get(
                                                    "status",
                                                    "INSUFFICIENT_EVIDENCE"
                                                )
                                            ),
                                            "confidence": (
                                                evidence_verification.get(
                                                    "confidence",
                                                    0
                                                )
                                            ),
                                            "reason": (
                                                evidence_verification.get(
                                                    "reason",
                                                    ""
                                                )
                                            ),
                                            "evidence": evidence or []
                                        })

                                    except Exception as e:
                                        evidence_results.append({
                                            "claim": claim,
                                            "status": "ERROR",
                                            "confidence": 0,
                                            "reason": (
                                                "Evidence verification "
                                                f"failed: {e}"
                                            ),
                                            "evidence": []
                                        })

                        else:
                            st.info(
                                "External evidence verification was skipped "
                                "because no factual claims were available."
                            )

                        # =================================================
                        # 27. DISPLAY EXTERNAL EVIDENCE RESULTS
                        # =================================================

                        if evidence_results:

                            for number, result in enumerate(
                                evidence_results,
                                start=1
                            ):

                                status = result.get(
                                    "status",
                                    "INSUFFICIENT_EVIDENCE"
                                )

                                evidence_confidence = result.get(
                                    "confidence",
                                    0
                                )

                                with st.expander(
                                    f"Claim {number} — {status}",
                                    expanded=False
                                ):
                                    st.write(
                                        f"**Claim:** {result['claim']}"
                                    )

                                    st.write(
                                        f"**Evidence Status:** {status}"
                                    )

                                    st.write(
                                        "**Evidence Confidence:** "
                                        f"{evidence_confidence:.2f}%"
                                    )

                                    st.write(
                                        f"**Reason:** "
                                        f"{result.get('reason', '')}"
                                    )

                                    sources = result.get(
                                        "evidence",
                                        []
                                    )

                                    if sources:
                                        st.write("**Retrieved Sources:**")

                                        for source_number, source in enumerate(
                                            sources,
                                            start=1
                                        ):
                                            title = source.get(
                                                "title",
                                                "Unknown source"
                                            )

                                            url = source.get(
                                                "url",
                                                ""
                                            )

                                            st.write(
                                                f"{source_number}. {title}"
                                            )

                                            if url:
                                                st.caption(url)

                        # =================================================
                        # 28. SUPPORTED CLAIMS
                        # =================================================

                        st.subheader("Supported Claims")

                        supported_claims = verification.get(
                            "supported_claims",
                            []
                        )

                        if supported_claims:
                            for claim in supported_claims:
                                st.success(claim)
                        else:
                            st.info(
                                "No supported claims were identified "
                                "by the verification model."
                            )

                        # =================================================
                        # 29. POTENTIAL ISSUES
                        # =================================================

                        st.subheader("Potential Issues")

                        unsupported_claims = verification.get(
                            "unsupported_claims",
                            []
                        )

                        if unsupported_claims:
                            for claim in unsupported_claims:
                                st.warning(claim)
                        else:
                            st.success(
                                "No unsupported claims detected."
                            )

                        # =================================================
                        # 30. VERIFICATION SUMMARY
                        # =================================================

                        st.subheader("Verification Summary")

                        reason = verification.get(
                            "reason",
                            "No verification explanation available."
                        )

                        st.info(reason)

                        # =================================================
                        # FINAL TRUST AGENT
                        # =================================================

                        st.divider()
                        st.header("Final Trust Assessment")

                        # -------------------------------------------------
                        # 1. QUALITY SCORE
                        # -------------------------------------------------

                        # best_score is already on a 0-10 scale
                        quality_component = best_score


                        # -------------------------------------------------
                        # 2. VERIFICATION SCORE
                        # -------------------------------------------------

                        # verification_score is already on a 0-10 scale
                        verification_component = verification_score


                        # -------------------------------------------------
                        # 3. CROSS-MODEL CONSISTENCY
                        # -------------------------------------------------

                        # consistency score originally ranges from 0-1
                        # Convert it to 0-10

                        consistency_component = (
                            consistency_scores.get(best_model, 0) * 10
                        )


                        # -------------------------------------------------
                        # 4. EXTERNAL EVIDENCE SCORE
                        # -------------------------------------------------

                        supported_count = 0
                        contradicted_count = 0
                        insufficient_count = 0
                        error_count = 0

                        for result in evidence_results:

                            status = str(
                                result.get("status", "")
                            ).upper()

                            if status == "SUPPORTED":
                                supported_count += 1

                            elif status == "CONTRADICTED":
                                contradicted_count += 1

                            elif status == "INSUFFICIENT_EVIDENCE":
                                insufficient_count += 1

                            else:
                                error_count += 1


                        total_evidence_claims = len(evidence_results)


                        # -------------------------------------------------
                        # CALCULATE EVIDENCE SUPPORT SCORE
                        # -------------------------------------------------

                        if total_evidence_claims > 0:

                            # Supported claims receive full credit.
                            # Insufficient evidence receives partial credit.
                            # Contradicted claims receive zero credit.

                            evidence_points = (
                                supported_count
                                + (0.5 * insufficient_count)
                            )

                            evidence_support_ratio = (
                                evidence_points / total_evidence_claims
                            )

                            evidence_component = (
                                evidence_support_ratio * 10
                            )

                        else:

                            evidence_component = 0


                        # -------------------------------------------------
                        # 5. FINAL TRUST WEIGHTS
                        # -------------------------------------------------

                        TRUST_WEIGHTS = {

                            "quality": 0.30,

                            "verification": 0.25,

                            "evidence": 0.35,

                            "consistency": 0.10
                        }


                        # -------------------------------------------------
                        # 6. CALCULATE FINAL TRUST SCORE
                        # -------------------------------------------------

                        active_components = {
                            "quality": quality_component,
                            "evidence": evidence_component,
                            "consistency": consistency_component
                        }

                        if verification_available:
                            active_components["verification"] = (
                                verification_component
                            )

                        active_weight_total = sum(
                            TRUST_WEIGHTS[name]
                            for name in active_components
                        )

                        normalized_trust_weights = {
                            name: TRUST_WEIGHTS[name] / active_weight_total
                            for name in active_components
                        }

                        final_trust_score = sum(
                            active_components[name]
                            * normalized_trust_weights[name]
                            for name in active_components
                        )


                        final_trust_percentage = (
                            final_trust_score * 10
                        )


                        # -------------------------------------------------
                        # 7. DETERMINE TRUST LEVEL
                        # -------------------------------------------------

                        if final_trust_score >= 8:

                            trust_level = "HIGH TRUST"

                        elif final_trust_score >= 6:

                            trust_level = "MODERATE TRUST"

                        else:

                            trust_level = "LOW TRUST"


                        # -------------------------------------------------
                        # 8. DISPLAY FINAL TRUST SCORE
                        # -------------------------------------------------

                        col1, col2, col3 = st.columns(3)

                        with col1:

                            st.metric(
                                "Final Trust Score",
                                f"{final_trust_score:.2f}/10"
                            )

                        with col2:

                            st.metric(
                                "Trust Percentage",
                                f"{final_trust_percentage:.2f}%"
                            )

                        with col3:

                            st.metric(
                                "Trust Level",
                                trust_level
                            )


                        # -------------------------------------------------
                        # 9. DISPLAY COMPONENT SCORES
                        # -------------------------------------------------

                        st.subheader("Trust Score Components")

                        trust_component_rows = [
                            {
                                "Component": "Response Quality",
                                "Score (/10)": round(quality_component, 2),
                                "Weight (%)": round(
                                    normalized_trust_weights["quality"] * 100,
                                    2
                                )
                            },
                            {
                                "Component": (
                                    "Verification"
                                    if verification_available
                                    else "Verification (Unavailable)"
                                ),
                                "Score (/10)": (
                                    round(verification_component, 2)
                                    if verification_available
                                    else "N/A"
                                ),
                                "Weight (%)": (
                                    round(
                                        normalized_trust_weights[
                                            "verification"
                                        ] * 100,
                                        2
                                    )
                                    if verification_available
                                    else 0.0
                                )
                            },
                            {
                                "Component": "External Evidence",
                                "Score (/10)": round(evidence_component, 2),
                                "Weight (%)": round(
                                    normalized_trust_weights["evidence"] * 100,
                                    2
                                )
                            },
                            {
                                "Component": "Cross-Model Consistency",
                                "Score (/10)": round(
                                    consistency_component,
                                    2
                                ),
                                "Weight (%)": round(
                                    normalized_trust_weights[
                                        "consistency"
                                    ] * 100,
                                    2
                                )
                            }
                        ]

                        trust_components_df = pd.DataFrame(
                            trust_component_rows
                        )


                        st.dataframe(
                            trust_components_df,
                            use_container_width=True,
                            hide_index=True
                        )


                        # -------------------------------------------------
                        # 10. EVIDENCE SUMMARY
                        # -------------------------------------------------

                        st.subheader("Evidence Summary")

                        col1, col2, col3, col4 = st.columns(4)

                        with col1:

                            st.metric(
                                "Supported",
                                supported_count
                            )

                        with col2:

                            st.metric(
                                "Contradicted",
                                contradicted_count
                            )

                        with col3:

                            st.metric(
                                "Insufficient Evidence",
                                insufficient_count
                            )

                        with col4:

                            st.metric(
                                "Verification Errors",
                                error_count
                            )


                        # -------------------------------------------------
                        # 11. FINAL DECISION
                        # -------------------------------------------------

                        st.subheader("Final Decision")


                        if trust_level == "HIGH TRUST":

                            if contradicted_count == 0:

                                st.success(
                                    "The selected response has a high trust score. "
                                    "The evaluation, verification, cross-model "
                                    "agreement, and external evidence indicate that "
                                    "the response is highly reliable."
                                )

                            else:

                                st.warning(
                                    "The response achieved a high overall trust "
                                    "score, but one or more factual claims were "
                                    "contradicted by external evidence. These claims "
                                    "should be reviewed before the answer is treated "
                                    "as fully verified."
                                )


                        elif trust_level == "MODERATE TRUST":

                            st.warning(
                                "The selected response has moderate reliability. "
                                "Some claims may be unsupported, contradicted, or "
                                "lack sufficient external evidence. Further "
                                "verification is recommended."
                            )


                        else:

                            st.error(
                                "The selected response has a low trust score. "
                                "The answer should not be considered reliable "
                                "without additional verification."
                            )

                        # =================================================
                        # 31. EXPLAINABLE DECISION
                        # =================================================

                        st.subheader(
                            "Why This Response Was Selected"
                        )

                        best_metrics = evaluation_results[
                            best_model
                        ]

                        sorted_metrics = sorted(
                            best_metrics.items(),
                            key=lambda item: item[1],
                            reverse=True
                        )

                        top_metrics = sorted_metrics[:3]

                        metric_display_names = {
                            "relevance": "Relevance",
                            "completeness": "Completeness",
                            "justification": "Justification Quality",
                            "context_awareness": "Context Awareness",
                            "conciseness": "Conciseness",
                            "consistency": "Cross-Model Consistency"
                        }

                        st.write(
                            f"The **{best_model}** response achieved "
                            f"the highest weighted quality score of "
                            f"**{best_score:.2f}/10**."
                        )

                        st.write(
                            "Its strongest evaluation criteria were:"
                        )

                        for metric, score in top_metrics:

                            metric_name = metric_display_names.get(
                                metric,
                                metric
                            )

                            st.write(
                                f"- **{metric_name}:** "
                                f"{score:.2f}/10"
                            )

                        # =================================================
                        # 32. VERIFIED ANSWER SYNTHESIS AGENT
                        # =================================================

                        st.divider()
                        st.header("Verified Final Answer")

                        try:

                            with st.spinner(
                                "Generating evidence-grounded final answer..."
                            ):

                                synthesis_result = synthesize_verified_answer(
                                    client=groq_client,
                                    question=user_query,
                                    selected_answer=best_response,
                                    evidence_results=evidence_results
                                )

                            verified_answer = synthesis_result.get(
                                "verified_answer",
                                best_response
                            )

                            corrections = synthesis_result.get(
                                "corrections_made",
                                []
                            )

                            uncertain_removed = synthesis_result.get(
                                "uncertain_claims_removed",
                                []
                            )

                            # =============================================
                            # DISPLAY FINAL VERIFIED ANSWER
                            # =============================================

                            st.subheader(
                                "Final Evidence-Grounded Response"
                            )

                            st.markdown(
                                verified_answer
                            )

                            # =============================================
                            # DISPLAY CORRECTIONS
                            # =============================================

                            if corrections:

                                st.subheader(
                                    "Corrections Made"
                                )

                                for correction in corrections:

                                    st.warning(
                                        correction
                                    )

                            # =============================================
                            # DISPLAY REMOVED UNCERTAIN CLAIMS
                            # =============================================

                            if uncertain_removed:

                                st.subheader(
                                    "Uncertain Claims Removed"
                                )

                                for claim in uncertain_removed:

                                    st.info(
                                        claim
                                    )

                            # =============================================
                            # FINAL RELIABILITY
                            # =============================================

                            st.subheader(
                                "Final Reliability"
                            )

                            if final_trust_score >= 8:

                                st.success(
                                    f"HIGH TRUST — "
                                    f"{final_trust_percentage:.2f}%"
                                )

                            elif final_trust_score >= 6:

                                st.warning(
                                    f"MODERATE TRUST — "
                                    f"{final_trust_percentage:.2f}%"
                                )

                            else:

                                st.error(
                                    f"LOW TRUST — "
                                    f"{final_trust_percentage:.2f}%"
                                )

                        except Exception as e:

                            st.error(
                                "Verified answer synthesis failed: "
                                f"{e}"
                            )


                        # =================================================
                        # 33. AGENT DECISION TRACE
                        # =================================================

                        st.divider()
                        st.header("Agent Decision Trace")

                        st.write(
                            "This trace summarizes how the multi-agent system "
                            "generated, compared, evaluated, verified, and "
                            "finalized the response."
                        )

                        with st.expander(
                            "Step 1 — Multi-Model Response Generation"
                        ):
                            st.write(
                                f"**Successful Models:** "
                                f"{', '.join(responses.keys())}"
                            )
                            st.write(
                                f"**Responses Generated:** {len(responses)}"
                            )
                            st.write(
                                "Each available model independently generated "
                                "an answer to the user query."
                            )

                        with st.expander(
                            "Step 2 — Cross-Model Validation"
                        ):
                            st.write(
                                f"**Selected Model Consistency:** "
                                f"{consistency_component:.2f}/10"
                            )
                            st.write(
                                f"**Semantic Agreement:** "
                                f"{consistency_component * 10:.2f}%"
                            )
                            st.write(
                                "Model responses were compared using semantic "
                                "similarity to measure cross-model agreement."
                            )

                        with st.expander(
                            "Step 3 — Evaluation and Ranking"
                        ):
                            st.write(
                                f"**Selected Model:** {best_model}"
                            )
                            st.write(
                                f"**Weighted Quality Score:** "
                                f"{best_score:.2f}/10"
                            )
                            st.write(
                                f"**Quality Percentage:** "
                                f"{best_score * 10:.2f}%"
                            )
                            st.write(
                                "Responses were evaluated for relevance, "
                                "completeness, justification quality, context "
                                "awareness, conciseness, and consistency."
                            )

                        with st.expander(
                            "Step 4 — Verification Agent"
                        ):
                            st.write(
                                "**Verification Score:** "
                                + (
                                    f"{verification_component:.2f}/10"
                                    if verification_available
                                    else "Unavailable (excluded)"
                                )
                            )
                            st.write(
                                "**Verification Confidence:** "
                                + (
                                    f"{confidence:.2f}%"
                                    if confidence is not None
                                    else "Unavailable"
                                )
                            )
                            st.write(
                                f"**Factual Claims Extracted:** "
                                f"{len(extracted_claims)}"
                            )
                            st.write(
                                "The selected response was checked for factual "
                                "correctness, internal consistency, and "
                                "unsupported claims."
                            )

                        with st.expander(
                            "Step 5 — External Evidence Verification"
                        ):
                            st.write(
                                f"**Claims Checked:** {total_evidence_claims}"
                            )
                            st.write(
                                f"**Supported:** {supported_count}"
                            )
                            st.write(
                                f"**Contradicted:** {contradicted_count}"
                            )
                            st.write(
                                f"**Insufficient Evidence:** "
                                f"{insufficient_count}"
                            )
                            st.write(
                                f"**Verification Errors:** {error_count}"
                            )
                            st.write(
                                f"**Evidence Score:** "
                                f"{evidence_component:.2f}/10"
                            )

                        with st.expander(
                            "Step 6 — Final Trust Assessment"
                        ):
                            st.write(
                                f"**Response Quality:** "
                                f"{quality_component:.2f}/10"
                            )
                            st.write(
                                "**Verification:** "
                                + (
                                    f"{verification_component:.2f}/10"
                                    if verification_available
                                    else "Unavailable (weight redistributed)"
                                )
                            )
                            st.write(
                                f"**External Evidence:** "
                                f"{evidence_component:.2f}/10"
                            )
                            st.write(
                                f"**Cross-Model Consistency:** "
                                f"{consistency_component:.2f}/10"
                            )
                            st.write(
                                f"**Final Trust Score:** "
                                f"{final_trust_score:.2f}/10"
                            )
                            st.write(
                                f"**Trust Percentage:** "
                                f"{final_trust_percentage:.2f}%"
                            )
                            st.write(
                                f"**Trust Level:** {trust_level}"
                            )

                        with st.expander(
                            "Step 7 — Verified Answer Synthesis"
                        ):
                            if "verified_answer" in locals():
                                st.success(
                                    "The Synthesis Agent successfully generated "
                                    "the final evidence-grounded response."
                                )
                                st.write(
                                    f"**Corrections Made:** "
                                    f"{len(corrections)}"
                                )
                                st.write(
                                    f"**Uncertain Claims Removed:** "
                                    f"{len(uncertain_removed)}"
                                )
                            else:
                                st.warning(
                                    "The Synthesis Agent did not produce a "
                                    "verified final response."
                                )

                        st.subheader("Decision Summary")

                        st.success(
                            f"The system selected {best_model} with a quality "
                            f"score of {best_score:.2f}/10. After factual "
                            f"verification and external evidence validation, "
                            f"the response received a final trust score of "
                            f"{final_trust_score:.2f}/10 "
                            f"({final_trust_percentage:.2f}%), classified as "
                            f"{trust_level}."
                        )


                        # =================================================
                        # 34. RESEARCH EXPERIMENT LOGGING
                        # =================================================

                        try:
                            results_file = log_experiment(
                                question=user_query,
                                category=category,
                                selected_model=best_model,
                                quality_score=best_score,
                                verification_score=verification_score,
                                verification_confidence=confidence,
                                consistency_score=consistency_component,
                                evidence_score=evidence_component,
                                supported_count=supported_count,
                                contradicted_count=contradicted_count,
                                insufficient_count=insufficient_count,
                                total_claims=total_evidence_claims,
                                final_trust_score=final_trust_score,
                                trust_level=trust_level
                            )

                            st.caption(
                                "Experiment saved to "
                                f"{results_file}"
                            )

                        except Exception as e:
                            st.warning(
                                "The experiment completed, but the result "
                                f"could not be logged: {e}"
                            )



            except Exception as e:

                st.error(
                    f"Similarity Analysis Error: {e}"
                )