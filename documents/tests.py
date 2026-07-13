import shutil
import tempfile
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import UploadedDocument
from .utils import calculate_semantic_similarity_score


TEST_MEDIA_ROOT = tempfile.mkdtemp()


class FakeMean:
    def __init__(self, value):
        self.value = value

    def item(self):
        return self.value


class FakeValues:
    def __init__(self, value):
        self.value = value

    def mean(self):
        return FakeMean(self.value)


class FakeMaxResult:
    def __init__(self, value):
        self.values = FakeValues(value)


class FakeSimilarityMatrix:
    def __init__(self, value):
        self.value = value

    def max(self, dim=1):
        return FakeMaxResult(self.value)


class FakeSemanticModel:
    def encode(self, chunks, convert_to_tensor, normalize_embeddings, show_progress_bar):
        return chunks


class FakeSemanticUtil:
    def __init__(self, similarity):
        self.similarity = similarity

    def cos_sim(self, job_embeddings, resume_embeddings):
        return FakeSimilarityMatrix(self.similarity)


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class ATSCheckerTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEST_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.user = User.objects.create_user(
            username="student",
            password="test-password",
        )
        self.client.force_login(self.user)

    def create_resume(self, text, title="Resume"):
        return UploadedDocument.objects.create(
            user=self.user,
            title=title,
            document_type=UploadedDocument.RESUME,
            file=SimpleUploadedFile(
                "resume.doc",
                text.encode("latin-1"),
                content_type="application/msword",
            ),
        )

    def post_ats(self, resume, job_description):
        return self.client.post(
            reverse("documents:ats_checker"),
            {
                "resume": resume.pk,
                "job_description_text": job_description,
            },
        )

    def test_empty_job_description_shows_form_error(self):
        resume = self.create_resume("Python Django SQL")

        response = self.post_ats(resume, "")

        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"],
            "job_description_text",
            "Please paste the job description text.",
        )

    def test_resume_with_no_extractable_text_shows_form_error(self):
        resume = self.create_resume("12345 !!!")

        response = self.post_ats(resume, "Python developer role")

        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"],
            "resume",
            "Could not extract text from this resume. Please use a readable PDF, DOC, or DOCX resume.",
        )

    @patch("documents.utils.get_sentence_transformer_util")
    @patch("documents.utils.get_semantic_model")
    def test_successful_semantic_score(self, mock_model, mock_util):
        mock_model.return_value = {
            "success": True,
            "model": FakeSemanticModel(),
            "error": None,
        }
        mock_util.return_value = {
            "success": True,
            "util": FakeSemanticUtil(0.8245),
            "error": None,
        }

        result = calculate_semantic_similarity_score(
            "Built Python and Django projects.",
            "Need a Python Django developer.",
        )

        self.assertTrue(result["success"])
        self.assertAlmostEqual(result["semantic_score"], 82.45)

    @patch("documents.utils.get_sentence_transformer_util")
    @patch("documents.utils.get_semantic_model")
    def test_semantic_score_remains_between_zero_and_one_hundred(
        self,
        mock_model,
        mock_util,
    ):
        mock_model.return_value = {
            "success": True,
            "model": FakeSemanticModel(),
            "error": None,
        }
        mock_util.return_value = {
            "success": True,
            "util": FakeSemanticUtil(1.5),
            "error": None,
        }

        result = calculate_semantic_similarity_score("Python", "Python")

        self.assertEqual(result["semantic_score"], 100)

    @patch("documents.views.calculate_semantic_similarity_score")
    def test_no_recognized_skills_uses_semantic_score_as_final_score(
        self,
        mock_semantic,
    ):
        resume = self.create_resume("Leadership communication writing")
        mock_semantic.return_value = {
            "success": True,
            "semantic_score": 70,
            "error": None,
        }

        response = self.post_ats(
            resume,
            "Strong leadership and communication are required.",
        )

        self.assertRedirects(response, reverse("documents:ats_result"))
        result = self.client.session["ats_result"]
        self.assertEqual(result["match_score"], 70)
        self.assertEqual(result["final_score"], 70)
        self.assertIsNone(result["skill_coverage_score"])
        self.assertIn("No predefined skills", result["skill_note"])

    @patch("documents.views.calculate_ats_score")
    @patch("documents.views.calculate_semantic_similarity_score")
    def test_model_loading_failure_uses_tfidf_fallback(
        self,
        mock_semantic,
        mock_tfidf,
    ):
        resume = self.create_resume("Python Django")
        mock_semantic.return_value = {
            "success": False,
            "semantic_score": 0,
            "error": "Unable to load the semantic model.",
        }
        mock_tfidf.return_value = 50

        response = self.post_ats(resume, "Python Django Docker")

        self.assertRedirects(response, reverse("documents:ats_result"))
        result = self.client.session["ats_result"]
        self.assertEqual(result["scoring_method"], "TF-IDF fallback + skill coverage")
        self.assertEqual(result["semantic_score"], 50)
        self.assertEqual(result["model_name"], "all-MiniLM-L6-v2")

    @patch("documents.views.calculate_semantic_similarity_score")
    def test_existing_ats_result_context_still_works(self, mock_semantic):
        resume = self.create_resume("Python Django projects")
        mock_semantic.return_value = {
            "success": True,
            "semantic_score": 80,
            "error": None,
        }

        response = self.post_ats(resume, "Python Django Docker role")

        self.assertRedirects(response, reverse("documents:ats_result"))
        result = self.client.session["ats_result"]
        self.assertEqual(result["match_score"], 75)
        self.assertEqual(result["semantic_score"], 80)
        self.assertEqual(result["skill_coverage_score"], 67)
        self.assertEqual(result["final_score"], 75)
        self.assertEqual(
            result["scoring_method"],
            "60% semantic similarity + 40% skill coverage",
        )
        self.assertEqual(result["model_name"], "all-MiniLM-L6-v2")
        self.assertEqual(result["matched_keywords"], ["Python", "Django"])
        self.assertEqual(result["missing_keywords"], ["Docker"])
        self.assertEqual(result["matched_skills"], ["Python", "Django"])
        self.assertEqual(result["missing_skills"], ["Docker"])
        self.assertEqual(result["recommendations"], result["suggestions"])
