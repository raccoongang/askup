import logging

from django.conf import settings
from django.test import TestCase

from askup.models import Qset, Question

log = logging.getLogger(__name__)


class TestAdminPanelGroupQuestionsDeleting(TestCase):
    """
    Testing the admin panel group question deleting.
    """

    fixtures = ['groups', 'mockup_data']

    def setUp(self):
        """
        Set up the test conditions.
        """
        settings.DEBUG = False

    def test_group_geleting(self):
        """
        Test a group question deleting.

        Used in the admin panel when performing a group delete action.
        """
        qset = Qset.objects.get(id=4)
        questions_count_before = qset.questions_count  # 3 questions in this qset initially
        self.assertEqual(questions_count_before, 3)
        questions = Question.objects.filter(qset_id=qset.id)
        questions.delete()
        qset.refresh_from_db()
        questions_count_after = qset.questions_count  # 0 questions so far, after the deletion
        self.assertEqual(questions_count_after, 0)
