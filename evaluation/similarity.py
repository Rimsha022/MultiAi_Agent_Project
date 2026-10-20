from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity


# Load sentence embedding model
embedding_model = SentenceTransformer(
    "all-MiniLM-L6-v2"
)


def calculate_similarity(responses):

    # Get model names
    model_names = list(responses.keys())

    # Get responses
    texts = [
        responses[model]
        for model in model_names
    ]

    # Generate sentence embeddings
    embeddings = embedding_model.encode(
        texts
    )

    # Calculate cosine similarity
    similarity_matrix = cosine_similarity(
        embeddings
    )

    return model_names, similarity_matrix