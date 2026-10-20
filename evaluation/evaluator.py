import json


def evaluate_response(
    client,
    user_query,
    response_text
):

    evaluation_prompt = f"""
You are an independent AI response evaluation agent.

Evaluate the following AI-generated response.

USER QUESTION:
{user_query}

AI RESPONSE:
{response_text}

Evaluate the response using these criteria:

1. Relevance
How directly and correctly the response answers
the user's question.

2. Completeness
How sufficiently the response covers the important
information required by the question.

3. Justification Quality
How clearly and logically the response explains
or supports its claims.

4. Context Awareness
How well the response understands the user's
intent and requirements.

5. Conciseness
How focused the response is without unnecessary
repetition or irrelevant information.

Score each criterion from 0 to 10.

Return ONLY valid JSON using exactly this format:

{{
    "relevance": 0,
    "completeness": 0,
    "justification": 0,
    "context_awareness": 0,
    "conciseness": 0
}}

Rules:

- Every score must be between 0 and 10.
- Return numbers only for the scores.
- Do not include explanations.
- Do not include Markdown.
- Do not include text before or after the JSON.
"""


    # =====================================================
    # GPT-OSS AS EVALUATION AGENT
    # =====================================================

    response = client.chat.completions.create(

        model="openai/gpt-oss-120b",

        messages=[
            {
                "role": "user",
                "content": evaluation_prompt
            }
        ],

        temperature=0,

        max_tokens=500
    )


    raw_text = (
        response
        .choices[0]
        .message
        .content
        .strip()
    )


    # =====================================================
    # CLEAN POSSIBLE MARKDOWN
    # =====================================================

    raw_text = (
        raw_text
        .replace("```json", "")
        .replace("```JSON", "")
        .replace("```", "")
        .strip()
    )


    # =====================================================
    # PARSE JSON
    # =====================================================

    scores = json.loads(raw_text)


    # =====================================================
    # VALIDATE METRICS
    # =====================================================

    required_metrics = [
        "relevance",
        "completeness",
        "justification",
        "context_awareness",
        "conciseness"
    ]


    for metric in required_metrics:

        if metric not in scores:

            raise ValueError(
                f"Missing evaluation metric: {metric}"
            )


        try:

            score = float(
                scores[metric]
            )

        except (TypeError, ValueError):

            raise ValueError(
                f"Invalid score for {metric}"
            )


        if score < 0 or score > 10:

            raise ValueError(
                f"{metric} score must be "
                f"between 0 and 10."
            )


        scores[metric] = score


    return scores