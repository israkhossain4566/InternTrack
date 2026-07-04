import os
import re
import string


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
