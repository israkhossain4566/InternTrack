import os
import re
import string
import logging


logger = logging.getLogger(__name__)

SENTENCE_TRANSFORMER_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
MODEL_DISPLAY_NAME = "all-MiniLM-L6-v2"
_semantic_model = None
_semantic_util = None


TECHNICAL_KEYWORDS = [
    ("python", "Python"),
    ("django", "Django"),
    ("sql", "SQL"),
    ("rest api", "REST API"),
    ("git", "Git"),
    ("docker", "Docker"),
    ("cloud", "Cloud Platforms"),
    ("unit testing", "Unit Testing"),
    ("ci cd", "CI/CD"),
    ("machine learning", "Machine Learning"),
    ("javascript", "JavaScript"),
    ("html", "HTML"),
    ("css", "CSS"),
    ("react", "React"),
    ("api", "API"),
    ("postgresql", "PostgreSQL"),
    ("mysql", "MySQL"),
    ("aws", "AWS"),
    ("azure", "Azure"),
    ("linux", "Linux"),
]

SUGGESTION_MESSAGES = {
    "Docker": "Add Docker experience if applicable.",
    "REST API": "Mention REST API projects.",
    "Machine Learning": "Include ML experience if relevant.",
    "Unit Testing": "Add testing frameworks or unit testing experience if you have it.",
    "CI/CD": "Mention CI/CD tools or deployment workflows if applicable.",
    "Cloud Platforms": "Include cloud technologies if you have used them.",
}


def extract_pdf_text(file):
    from PyPDF2 import PdfReader

    file.seek(0)
    reader = PdfReader(file)
    text_parts = []

    for page in reader.pages:
        text_parts.append(page.extract_text() or "")

    return "\n".join(text_parts).strip()


def extract_docx_text(file):
    from docx import Document

    file.seek(0)
    document = Document(file)
    text_parts = []

    for paragraph in document.paragraphs:
        text_parts.append(paragraph.text)

    return "\n".join(text_parts).strip()


def extract_doc_text(file):
    file.seek(0)
    content = file.read()
    text = content.decode("latin-1", errors="ignore")
    text = re.sub(r"[^A-Za-z\s]", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def extract_uploaded_document_text(uploaded_file):
    extension = os.path.splitext(uploaded_file.name)[1].lower()

    if extension == ".pdf":
        return extract_pdf_text(uploaded_file)

    if extension == ".doc":
        return extract_doc_text(uploaded_file)

    if extension == ".docx":
        return extract_docx_text(uploaded_file)

    return ""


def prepare_text_for_embeddings(text):
    if text is None:
        return ""

    text = str(text).strip()
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)

    return text.strip()


def split_text_into_chunks(text, max_words=180):
    cleaned_text = prepare_text_for_embeddings(text)
    words = cleaned_text.split()

    if not words:
        return []

    return [
        " ".join(words[index : index + max_words])
        for index in range(0, len(words), max_words)
    ]


def get_semantic_model():
    global _semantic_model

    if _semantic_model is not None:
        return {
            "success": True,
            "model": _semantic_model,
            "error": None,
        }

    try:
        from sentence_transformers import SentenceTransformer

        _semantic_model = SentenceTransformer(SENTENCE_TRANSFORMER_MODEL)
        return {
            "success": True,
            "model": _semantic_model,
            "error": None,
        }
    except Exception as exc:
        logger.exception("Unable to load Sentence Transformer model.")
        return {
            "success": False,
            "model": None,
            "error": (
                "Unable to load the semantic model. "
                "If this is the first run, check your internet connection and installed packages."
            ),
        }


def get_sentence_transformer_util():
    global _semantic_util

    if _semantic_util is not None:
        return {
            "success": True,
            "util": _semantic_util,
            "error": None,
        }

    try:
        from sentence_transformers import util

        _semantic_util = util
        return {
            "success": True,
            "util": _semantic_util,
            "error": None,
        }
    except Exception as exc:
        logger.exception("Unable to load Sentence Transformer utilities.")
        return {
            "success": False,
            "util": None,
            "error": "Unable to load the semantic similarity utilities.",
        }


def clamp_score(score):
    return max(0, min(100, score))


def calculate_semantic_similarity_score(resume_text, job_description_text):
    resume_text = prepare_text_for_embeddings(resume_text)
    job_description_text = prepare_text_for_embeddings(job_description_text)

    if not resume_text:
        return {
            "success": False,
            "semantic_score": 0,
            "error": "The selected resume does not contain readable text.",
        }

    if not job_description_text:
        return {
            "success": False,
            "semantic_score": 0,
            "error": "Please paste a job description with readable text.",
        }

    model_result = get_semantic_model()
    if not model_result["success"]:
        return {
            "success": False,
            "semantic_score": 0,
            "error": model_result["error"],
        }

    util_result = get_sentence_transformer_util()
    if not util_result["success"]:
        return {
            "success": False,
            "semantic_score": 0,
            "error": util_result["error"],
        }

    resume_chunks = split_text_into_chunks(resume_text)
    job_chunks = split_text_into_chunks(job_description_text)

    if not resume_chunks or not job_chunks:
        return {
            "success": False,
            "semantic_score": 0,
            "error": "Not enough readable text was found for semantic comparison.",
        }

    try:
        model = model_result["model"]
        util = util_result["util"]
        resume_embeddings = model.encode(
            resume_chunks,
            convert_to_tensor=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        job_embeddings = model.encode(
            job_chunks,
            convert_to_tensor=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        similarity_matrix = util.cos_sim(job_embeddings, resume_embeddings)
        best_scores = similarity_matrix.max(dim=1).values
        similarity = best_scores.mean().item()
        semantic_score = clamp_score(similarity * 100)

        return {
            "success": True,
            "semantic_score": semantic_score,
            "error": None,
        }
    except Exception as exc:
        logger.exception("Semantic similarity calculation failed.")
        return {
            "success": False,
            "semantic_score": 0,
            "error": "Unable to calculate semantic similarity with the local model.",
        }


def get_english_stopwords():
    try:
        from nltk.corpus import stopwords

        return set(stopwords.words("english"))
    except LookupError:
        return {
            "a",
            "an",
            "and",
            "are",
            "as",
            "at",
            "be",
            "by",
            "for",
            "from",
            "has",
            "in",
            "is",
            "it",
            "of",
            "on",
            "or",
            "that",
            "the",
            "to",
            "with",
        }


def clean_text(text):
    from nltk.tokenize import RegexpTokenizer

    text = text.lower()
    text = text.translate(str.maketrans("", "", string.punctuation))
    text = re.sub(r"\d+", " ", text)

    tokenizer = RegexpTokenizer(r"\w+")
    tokens = tokenizer.tokenize(text)
    stop_words = get_english_stopwords()

    return [token for token in tokens if token not in stop_words]


def calculate_ats_score(resume_text, job_description_text):
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    clean_resume = " ".join(clean_text(resume_text))
    clean_job_description = " ".join(clean_text(job_description_text))

    if not clean_resume or not clean_job_description:
        return 0

    vectorizer = TfidfVectorizer()
    vectors = vectorizer.fit_transform([clean_resume, clean_job_description])
    similarity = cosine_similarity(vectors[0], vectors[1])[0][0]

    return round(similarity * 100)


def normalize_for_keyword_matching(text):
    text = text.lower()
    text = text.replace("/", " ")
    text = text.replace("-", " ")
    text = text.translate(str.maketrans("", "", string.punctuation))
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def get_keyword_analysis(resume_text, job_description_text):
    clean_resume = normalize_for_keyword_matching(resume_text)
    clean_job_description = normalize_for_keyword_matching(job_description_text)
    matched_keywords = []
    missing_keywords = []

    for keyword, display_name in TECHNICAL_KEYWORDS:
        if keyword in clean_job_description:
            if keyword in clean_resume:
                matched_keywords.append(display_name)
            else:
                missing_keywords.append(display_name)

    return matched_keywords, missing_keywords


def generate_suggestions(missing_keywords):
    suggestions = []

    for keyword in missing_keywords:
        suggestion = SUGGESTION_MESSAGES.get(
            keyword,
            f"Consider adding {keyword} experience if applicable.",
        )
        suggestions.append(suggestion)

    return suggestions


def calculate_skill_coverage_score(matched_keywords, missing_keywords):
    total_required_skills = len(matched_keywords) + len(missing_keywords)

    if total_required_skills == 0:
        return None

    return (len(matched_keywords) / total_required_skills) * 100


def calculate_hybrid_score(semantic_score, skill_coverage_score):
    if skill_coverage_score is None:
        return clamp_score(semantic_score)

    return clamp_score((semantic_score * 0.60) + (skill_coverage_score * 0.40))
