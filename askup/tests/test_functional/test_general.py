from collections import defaultdict
import logging

from django.conf import settings
from django.contrib.auth.models import AnonymousUser, User
from django.contrib.sessions.middleware import SessionMiddleware
from django.core.cache import cache
from django.db import models
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.test import RequestFactory, TestCase
from django.urls import reverse
from mock import patch

from askup.mixins.tests import LoginAdminByDefaultMixIn
from askup.models import Answer, Organization, Qset, Question, Vote
from askup.utils.general import (
    get_student_last_week_correct_answers_count,
    get_student_last_week_incorrect_answers_count,
    get_student_last_week_questions_count,
    get_student_last_week_votes_value,
    get_user_correct_answers_count,
    get_user_incorrect_answers_count,
    get_user_place_in_rank_list,
    get_user_profile_rank_list_and_total_users,
    get_user_score_by_id,
    send_subscription_emails,
)
from askup.utils.tests import client_user
from askup.views import login_view

log = logging.getLogger(__name__)


class GeneralTestCase(TestCase):
    """
    General test case class inherited by all the functional test cases below.
    """

    fixtures = ['groups', 'mockup_data']

    def setUp(self):
        """
        Set up the default test assets.
        """
        self.default_login()


class UserAuthenticationCase(LoginAdminByDefaultMixIn, TestCase):
    """Tests the user authentication."""

    def setUp(self):
        """Set up the test assets."""
        self.factory = RequestFactory()

    def test_authentication(self):
        """Test the user authentication."""
        User.objects.create_superuser('test_admin', 'test_admin@example.com', 'test_admin')
        login_form_data = {
            "username": "test_admin",
            "password": "test_admin",
        }
        request = self.factory.post(reverse('askup:sign_in'), data=login_form_data)
        self.client
        middleware = SessionMiddleware()
        middleware.process_request(request)
        request.session.save()
        request.user = AnonymousUser()
        response = login_view(request)
        self.assertIs(isinstance(response, HttpResponseRedirect), True)


class OrganizationsListView(LoginAdminByDefaultMixIn, GeneralTestCase):
    """Tests the Organizations view."""

    @client_user('teacher01', 'teacher01')
    def test_has_many_organizations(self):
        """Test an Organizations view with more than one organizations."""
        response = self.client.get(reverse('askup:organizations'))
        self.assertContains(response, 'Organization 1')
        self.assertNotContains(response, 'You didn\'t apply to any organization')

    @client_user('student01', 'student01')
    def test_has_one_organization(self):
        """Test an Organizations view with redirect because of only one organization."""
        response = self.client.get(reverse('askup:organizations'))
        self.assertRedirects(response, reverse('askup:organization', kwargs={'pk': 1}))

    @client_user('student02_no_orgs', 'student02_no_orgs')
    def test_has_no_organizations(self):
        """Test an Organizations view w/o the organizations."""
        response = self.client.get(reverse('askup:organizations'))
        self.assertContains(response, 'You didn\'t apply to any organization')
        self.client.login(username='admin', password='admin')


class OrganizationListView(LoginAdminByDefaultMixIn, GeneralTestCase):
    """Tests the Organization view."""

    def test_has_subjects(self):
        """Test an Organization view with the subjects."""
        response = self.client.get(reverse('askup:organization', kwargs={'pk': 1}))
        self.assertContains(response, 'Qset 1-1')
        self.assertNotContains(response, 'There are no subjects here.')

    def test_has_no_subjects(self):
        """Test an Organization view w/o the subjects."""
        response = self.client.get(reverse('askup:organization', kwargs={'pk': 3}))
        self.assertContains(response, 'There are no subjects here.')

    def test_admin_features_presence(self):
        """Test for an admin features presence."""
        response = self.client.get(reverse('askup:organization', kwargs={'pk': 1}))
        self.assertContains(response, 'data-target="#modal-edit-qset"')
        self.assertContains(response, 'data-target="#modal-new-qset">New subject</a>')

    @client_user('teacher01', 'teacher01')
    def test_teacher_features_presence(self):
        """Test for a teacher features presence."""
        response = self.client.get(reverse('askup:organization', kwargs={'pk': 1}))
        self.assertContains(response, 'data-target="#modal-new-qset">New subject</a>')
        self.assertNotContains(response, 'data-target="#modal-edit-qset"')


class QsetListView(LoginAdminByDefaultMixIn, GeneralTestCase):
    """Tests the Qset views (for questions only type)."""

    def test_type_2_has_questions(self):
        """Test Qset list view with the subjects."""
        response = self.client.get(reverse('askup:qset', kwargs={'pk': 4}))
        self.assertContains(response, 'Question 1-1-1')
        self.assertNotContains(response, 'There are no questions here.')

    def test_type_2_has_no_questions(self):
        """Test Qset list view w/o the questions."""
        response = self.client.get(reverse('askup:qset', kwargs={'pk': 9}))
        self.assertContains(response, 'There are no questions here.')

    @client_user('student01', 'student01')
    def test_student_features_presence(self):
        """Test for a student features presence."""
        response = self.client.get(reverse('askup:qset', kwargs={'pk': 4}))
        self.assertContains(response, 'Generate Question')
        self.assertContains(
            response,
            'a class="btn shortcut-button-link" href="{0}"'.format(
                reverse('askup:question_edit', kwargs={'pk': 1})
            )
        )
        self.assertContains(
            response,
            'a class="btn shortcut-button-link" href="{0}"'.format(
                reverse('askup:question_delete', kwargs={'pk': 1})
            )
        )
        self.assertNotContains(
            response,
            'a class="btn shortcut-button-link" href="{0}"'.format(
                reverse('askup:question_edit', kwargs={'pk': 2})
            )
        )
        self.assertNotContains(
            response,
            'a class="btn shortcut-button-link" href="{0}"'.format(
                reverse('askup:question_delete', kwargs={'pk': 2})
            )
        )

    @client_user('teacher01', 'teacher01')
    def test_teacher_features_presence(self):
        """Test for a teacher features presence."""
        response = self.client.get(reverse('askup:qset', kwargs={'pk': 4}))
        self.assertContains(response, 'Generate Question')
        self.assertContains(
            response,
            'a class="btn shortcut-button-link" href="{0}"'.format(
                reverse('askup:question_edit', kwargs={'pk': 1})
            )
        )
        self.assertContains(
            response,
            'a class="btn shortcut-button-link" href="{0}"'.format(
                reverse('askup:question_delete', kwargs={'pk': 1})
            )
        )

    def test_admin_features_presence(self):
        """Test for an admin features presence."""
        response = self.client.get(reverse('askup:qset', kwargs={'pk': 4}))
        self.assertContains(response, 'Generate Question')
        self.assertContains(
            response,
            'a class="btn shortcut-button-link" href="{0}"'.format(
                reverse('askup:question_edit', kwargs={'pk': 1})
            )
        )
        self.assertContains(
            response,
            'a class="btn shortcut-button-link" href="{0}"'.format(
                reverse('askup:question_delete', kwargs={'pk': 1})
            )
        )

    @client_user('student01', 'student01')
    def test_apply_filter_all_on_qset(self):
        """Test the "all" user filter selected."""
        response = self.client.get(
            '{}?filter=all'.format(reverse('askup:qset', kwargs={'pk': 4}))
        )
        self.assertContains(response, 'Question 1-1-1')  # My question
        self.assertContains(response, 'Question 1-1-2')  # Other's question
        self.assertContains(response, 'Question 1-1-3')  # My question

    @client_user('student01', 'student01')
    def test_apply_filter_mine_on_qset(self):
        """Test the "mine" user filter selected."""
        response = self.client.get(
            '{}?filter=mine'.format(reverse('askup:qset', kwargs={'pk': 4}))
        )
        self.assertContains(response, 'Question 1-1-1')  # My question
        self.assertNotContains(response, 'Question 1-1-2')  # Other's question
        self.assertContains(response, 'Question 1-1-3')  # My question

    @client_user('student01', 'student01')
    def test_apply_filter_others_on_qset(self):
        """Test the "others" user filter selected."""
        response = self.client.get(
            '{}?filter=others'.format(reverse('askup:qset', kwargs={'pk': 4}))
        )
        self.assertNotContains(response, 'Question 1-1-1')  # My question
        self.assertContains(response, 'Question 1-1-2')  # Other's question
        self.assertNotContains(response, 'Question 1-1-3')  # My question


class QsetModelFormTest(LoginAdminByDefaultMixIn, GeneralTestCase):
    """Tests the Qset model form (CRUD etc.)."""

    def create_qset(self, name, parent_qset_id):
        """Create qset with the parameters."""
        return self.client.post(
            reverse(
                'askup:qset_create'
            ),
            {
                'name': name,
                'parent_qset': parent_qset_id,
            }
        )

    def create_qset_success(self, name, parent_qset_id):
        """Create qset and look for a success."""
        self.create_qset(name, parent_qset_id)
        qset = get_object_or_404(Qset, name=name, parent_qset_id=parent_qset_id)
        self.assertEqual(qset.name, name)
        self.assertEqual(qset.type, 2)

    def update_qset(self, qset_id, new_name, new_parent_qset_id):
        """Update qset with the parameters."""
        return self.client.post(
            reverse(
                'askup:qset_update',
                kwargs={'pk': qset_id}
            ),
            {
                'name': new_name,
                'parent_qset': new_parent_qset_id,
            }
        )

    def test_create_qset_success(self):
        """Test qset creation."""
        parent_qset_id = 1
        name = 'test qset questions only'
        self.create_qset_success(name, parent_qset_id)

    def test_create_qset_fail_only_organization_parents(self):
        """Test qset creation failure because of simple qset as a parent."""
        self.create_qset('test qset questions only fail', 4)

    @client_user('teacher01', 'teacher01')
    def test_create_qset_fail_forbidden_parent(self):
        """Create qset and look for a fail."""
        parent_qset_id = 3
        name = 'test qset mixed forbidden parent'

        with self.assertRaises(Http404):
            self.create_qset(name, parent_qset_id)
            get_object_or_404(Qset, name=name, parent_qset_id=parent_qset_id)

    def test_update_qset_success(self):
        """Update qset and look for a success."""
        parent_qset_id = 1
        qset_id = 4
        name = 'Qset 1-1 updated'
        self.update_qset(qset_id, name, parent_qset_id)
        qset = get_object_or_404(Qset, pk=qset_id)
        self.assertEqual(qset.name, name)
        self.assertEqual(qset.type, 2)

    @client_user('teacher01', 'teacher01')
    def test_update_qset_fail_forbidden_parent(self):
        """Test qset updating with the forbiden parent."""
        with self.assertRaises(Http404):
            name = 'Qset 2-1 updated'
            parent_qset_id = 3
            self.update_qset(6, name, parent_qset_id)
            get_object_or_404(Qset, name=name, parent_qset_id=parent_qset_id)

    def delete_qset(self, qset_id):
        """Do delete particular qset through the client."""
        self.client.post(reverse('askup:qset_delete', kwargs={'pk': qset_id}))

    def delete_and_get_qset(self, qset_id):
        """Do delete and get the particular qset."""
        self.delete_qset(qset_id)
        get_object_or_404(Qset, pk=qset_id)

    def test_delete_qset_as_admin_success(self):
        """Test successful qset deletion by the admin."""
        with self.assertRaises(Http404):
            # Try to delete Qset 1-1 by the admin
            self.delete_and_get_qset(4)

    @client_user('teacher01', 'teacher01')
    def test_delete_qset_as_teacher_success(self):
        """Test successful qset deletion by the teacher."""
        # Try to delete Qset 1-2 by the teacher01
        with self.assertRaises(Http404):
            self.delete_and_get_qset(5)

    @client_user('student01', 'student01')
    def test_delete_qset_as_student_fail(self):
        """Test failed by permissions student qset deletion."""
        # Try to delete Qset 1-1 by the student01
        self.client.login(username='student01', password='student01')
        self.delete_and_get_qset(4)
        self.client.login(username='admin', password='admin')

    @client_user('teacher01', 'teacher01')
    def test_delete_qset_as_teacher_fail(self):
        """Test failed by permissions teacher qset deletion."""
        # Try to delete Qset 4-1 by the teacher01
        self.delete_and_get_qset(11)

    def test_parent_questions_count_update_on_qset_delete(self):
        """Test parent questions count update on qset delete."""
        org_qset = {
            'id': 1,  # Organization 1 from the mockups
            'orig_count': None,
            'new_count': None,
        }
        delete_qset = get_object_or_404(Qset, pk=4)  # Qset 1-1 from the mockups
        delete_qset_count = delete_qset.questions_count
        org_qset['orig_count'] = get_object_or_404(Qset, pk=org_qset['id']).questions_count
        delete_qset.delete()
        org_qset['new_count'] = get_object_or_404(Qset, pk=org_qset['id']).questions_count
        self.assertEqual(
            org_qset['new_count'],
            org_qset['orig_count'] - delete_qset_count
        )

    def test_parent_questions_count_update_on_parent_change(self):
        """Test parent questions count update on parent change."""
        org_qset = {
            'id': 1,  # Organization 1 from the mockups
            'orig_count': None,
            'new_count': None,
        }
        new_org_qset = {
            'id': 10,  # Organization 4 from the mockups
            'orig_count': None,
            'new_count': None,
        }
        move_qset = get_object_or_404(Qset, pk=4)
        move_qset_count = move_qset.questions_count
        org_qset['orig_count'] = get_object_or_404(Qset, pk=org_qset['id']).questions_count
        new_org_qset['orig_count'] = get_object_or_404(Qset, pk=new_org_qset['id']).questions_count
        move_qset.parent_qset_id = new_org_qset['id']
        move_qset.save()
        org_qset['new_count'] = get_object_or_404(Qset, pk=org_qset['id']).questions_count
        new_org_qset['new_count'] = get_object_or_404(Qset, pk=new_org_qset['id']).questions_count
        self.assertEqual(
            org_qset['new_count'],
            org_qset['orig_count'] - move_qset_count
        )
        self.assertEqual(
            new_org_qset['new_count'],
            new_org_qset['orig_count'] + move_qset_count
        )


class QuestionModelFormTest(LoginAdminByDefaultMixIn, GeneralTestCase):
    """Tests the Question model form (CRUD etc.)."""

    def qset_create_question(self, text, answer_text, qset_id, form_qset_id=None):
        """
        Create question by qset's "Generate question" form.

        :param self: Object of the TestCase instance containing initialized client to use
        :param text: Text of the question
        :param answer_text: Text of the correct question answer
        :param qset_id: Id of the subject where question will be created
        :param form_qset_id: Id of the subject, selected in the form of question (may be forged and unpermitted)
        :type text: TestCase
        :type text: str
        :type answer_text: str
        :type qset_id: int
        :type form_qset_id: int
        """
        form_qset_id = qset_id if form_qset_id is None else form_qset_id
        self.client.post(
            reverse(
                'askup:qset_question_create',
                kwargs={'qset_id': qset_id},
            ),
            {
                'text': text,
                'answer_text': answer_text,
                'qset': form_qset_id,
            }
        )

    def create_question(self, text, answer_text, qset_id):
        """Create question by general "Generate question" form."""
        return self.client.post(
            reverse(
                'askup:question_create',
            ),
            {
                'text': text,
                'answer_text': answer_text,
                'qset': qset_id,
            }
        )

    def test_question_fail_duplicate(self):
        """Create question and look for a fail because on forbidden qset."""
        text = 'Question 1-1-1'
        answer_text = 'Different answer 1-1-1'
        qset_id = 4  # Organization 1 -> Qset 1-1

        with self.assertRaises(Http404):
            self.qset_create_question(text, answer_text, qset_id)
            get_object_or_404(Question, text=text, answer_text=answer_text, qset_id=qset_id)

    def test_question_fail_no_qset_qset_form(self):
        """Create question and look for a fail because of no qset specified (qset question)."""
        text = 'Question 1-1-1-no-qset'
        answer_text = 'Different answer 1-1-1-no-qset'
        qset_id = None

        with self.assertRaises(Http404):
            self.qset_create_question(text, answer_text, 4, form_qset_id=None)
            get_object_or_404(Question, text=text, answer_text=answer_text, qset_id=qset_id)

    def test_question_fail_no_qset_general_form(self):
        """Create question and look for a fail because of no qset specified (general question)."""
        text = 'Question 1-1-1-no-qset'
        answer_text = 'Different answer 1-1-1-no-qset'
        qset_id = None

        with self.assertRaises(Http404):
            self.create_question(text, answer_text, None)
            get_object_or_404(Question, text=text, answer_text=answer_text, qset_id=qset_id)

    @client_user('teacher01', 'teacher01')
    def test_question_fail_forbidden_parent(self):
        """Create question and look for a fail because on forbidden qset."""
        text = 'Test question that failed 2'
        answer_text = 'Test question answer that failed 2'
        qset_id = 11  # Organization 3 -> Qset 4-1 (forbidden for the teacher01)

        with self.assertRaises(Http404):
            self.qset_create_question(text, answer_text, qset_id)
            get_object_or_404(Question, text=text, qset_id=qset_id)

    def test_qset_create_question_success(self):
        """Test question creation."""
        qset_id = 4
        text = 'Test question 1'
        answer_text = 'Test answer 1' * 50  # testing as well that the answer can be a big one (255+ chars) now

        self.qset_create_question(text, answer_text, qset_id)
        question = get_object_or_404(Question, text=text, qset_id=qset_id)
        self.assertEqual(question.text, text)
        self.assertEqual(question.answer_text, answer_text)
        self.assertEqual(question.qset_id, qset_id)

    def question_edit(self, question_id, text, answer_text, qset_id):
        """Send question edit request."""
        self.client.post(
            reverse('askup:question_edit', kwargs={'pk': question_id}),
            {
                'text': text,
                'answer_text': answer_text,
                'qset': qset_id,
            }
        )

    def test_edit_question_success(self):
        """Test question updating."""
        self.question_edit(1, 'Question 1-1-1 updated', 'Answer 1-1-1 updated', 5)
        question_exists = Question.objects.filter(id=1, text='Question 1-1-1 updated').exists()
        self.assertEqual(question_exists, True)

    def test_edit_question_fail_no_qset(self):
        """Test question updating."""
        self.question_edit(1, 'Question 1-1-1 updated', 'Answer 1-1-1 updated', None)
        question_exists = Question.objects.filter(id=1, text='Question 1-1-1 updated').exists()
        self.assertEqual(question_exists, False)

    @client_user('student01', 'student01')
    def test_edit_question_fail_no_permission(self):
        """Test question updating."""
        question_text = 'Question 1-1-2 updated'
        self.question_edit(2, question_text, 'Answer 1-1-2 updated', 4)
        question_exists = Question.objects.filter(id=2, text=question_text).exists()
        self.assertEqual(question_exists, False)

    def delete_question(self, question_id):
        """Do delete particular question through the client."""
        self.client.post(reverse('askup:question_delete', kwargs={'pk': question_id}))

    def delete_and_get_question(self, question_id):
        """Do delete and get the particular question."""
        self.delete_question(question_id)
        get_object_or_404(Question, pk=question_id)

    def test_delete_question_success(self):
        """Test successful question deletion."""
        with self.assertRaises(Http404):
            self.delete_and_get_question(1)  # Try to delete Question 1-1-1 by the admin

    @client_user('student01', 'student01')
    def test_delete_question_failed_by_permissions(self):
        """Test failed by permissions question deletion."""
        self.delete_and_get_question(2)  # Try to delete Question 1-1-2 (teacher01) by the student01

    def test_parent_questions_count_update_on_create(self):
        """Test parent question count update on question create."""
        qsets = {
            'org_qset': {
                'id': 1,  # Organization 1 from the mockups
                'orig_count': None,
                'new_count': None,
            },
            'parent_qset': {
                'id': 4,  # Qset 1-1 from the mockups
                'orig_count': None,
                'new_count': None,
            },
        }
        for key in qsets.keys():
            qsets[key]['orig_count'] = get_object_or_404(Qset, pk=qsets[key]['id']).questions_count

        Question.objects.create(
            text='Question count test 1',
            answer_text='Question count test 1',
            qset_id=4,
            blooms_tag=0,
            user_id=1
        )

        for key in qsets.keys():
            qsets[key]['new_count'] = get_object_or_404(Qset, pk=qsets[key]['id']).questions_count

        org_qset = qsets['org_qset']
        parent_qset = qsets['parent_qset']
        self.assertEqual(
            org_qset['new_count'],
            org_qset['orig_count'] + 1
        )
        self.assertEqual(
            parent_qset['new_count'],
            parent_qset['orig_count'] + 1
        )

    def test_parent_questions_count_update_on_delete(self):
        """Test parent question count update on question delete."""
        qsets = {
            'org_qset': {
                'id': 1,  # Organization 1 from the mockups
                'orig_count': None,
                'new_count': None,
            },
            'parent_qset': {
                'id': 4,  # Qset 1-1 from the mockups
                'orig_count': None,
                'new_count': None,
            },
        }
        question = get_object_or_404(Question, pk=1)

        for key in qsets.keys():
            qsets[key]['orig_count'] = get_object_or_404(Qset, pk=qsets[key]['id']).questions_count

        question.delete()

        for key in qsets.keys():
            qsets[key]['new_count'] = get_object_or_404(Qset, pk=qsets[key]['id']).questions_count

        org_qset = qsets['org_qset']
        parent_qset = qsets['parent_qset']
        self.assertEqual(
            org_qset['new_count'],
            org_qset['orig_count'] - 1
        )
        self.assertEqual(
            parent_qset['new_count'],
            parent_qset['orig_count'] - 1
        )

    def test_parent_questions_count_update_on_parent_change(self):
        """Test parent questions count update on parent change."""
        qsets = {
            'old_org_qset': {
                'id': 1,  # Organization 1 from the mockups
                'orig_count': None,
                'new_count': None,
            },
            'old_parent_qset': {
                'id': 4,  # Qset 1-1 from the mockups
                'orig_count': None,
                'new_count': None,
            },
            'new_org_qset': {
                'id': 10,  # Organization 4 from the mockups
                'orig_count': None,
                'new_count': None,
            },
            'new_parent_qset': {
                'id': 11,  # Qset 4-1 from the mockups
                'orig_count': None,
                'new_count': None,
            },
        }
        question = get_object_or_404(Question, pk=1)  # Question 1-1-1 (with the parent: Qset 1-1)

        for key in qsets.keys():
            qsets[key]['orig_count'] = get_object_or_404(Qset, pk=qsets[key]['id']).questions_count

        question.qset_id = qsets['new_parent_qset']['id']
        question.save()

        for key in qsets.keys():
            qsets[key]['new_count'] = get_object_or_404(Qset, pk=qsets[key]['id']).questions_count

        old_org_qset = qsets['old_org_qset']
        old_parent_qset = qsets['old_parent_qset']
        new_org_qset = qsets['new_org_qset']
        new_parent_qset = qsets['new_parent_qset']
        self.assertEqual(
            old_org_qset['new_count'],
            old_org_qset['orig_count'] - 1
        )
        self.assertEqual(
            old_parent_qset['new_count'],
            old_parent_qset['orig_count'] - 1
        )
        self.assertEqual(
            new_org_qset['new_count'],
            new_org_qset['orig_count'] + 1
        )
        self.assertEqual(
            new_parent_qset['new_count'],
            new_parent_qset['orig_count'] + 1
        )


class AnswerModelFormCase(LoginAdminByDefaultMixIn, GeneralTestCase):
    """Tests the Answer model related forms."""

    def create_answer(self, question_id, qset_id, answer_text):
        """create_answer."""
        return self.client.post(
            reverse(
                'askup:question_answer',
                kwargs={
                    'question_id': question_id,
                    'qset_id': qset_id,
                }
            ),
            {'text': answer_text}
        )

    def test_answer_the_question_success(self):
        """test_answer_the_question_success."""
        answer_text = 'Test answer' * 50  # testing as well that the answer can be a big one (255+ chars) now
        response = self.create_answer(1, 4, answer_text).json()
        answer = Answer.objects.filter(question_id=1, text=answer_text).first()
        self.assertIsNotNone(answer)
        self.assertEqual(response['result'], 'success')
        self.assertEqual(answer.text, answer_text)

    def test_answer_the_question_fail_inexistent_question(self):
        """test_answer_the_question_fail_inexistent_question."""
        answer_text = 'Test answer'
        inexistant_question_id = 111
        inexistant_qset_id = 111
        response = self.create_answer(inexistant_question_id, inexistant_qset_id, answer_text)
        self.assertEqual(response.json()['result'], 'error')
        self.assertTrue('redirect_url' in response.json())

    def test_answer_the_question_fail_empty_answer(self):
        """test_answer_the_question_fail_empty_answer."""
        answer_text = ''
        response = self.create_answer(1, 4, answer_text).json()
        self.assertEqual(response['result'], 'error')

    def test_answer_evaluation_success(self):
        """test_answer_evaluation_success."""
        answer_text = 'This test answer is very unique 01'
        answer_response = self.create_answer(1, 4, answer_text).json()
        self.client.get(answer_response['evaluation_urls']['wrong'])  # Evaluate as wrong (0)
        answer = Answer.objects.filter(question_id=1, text=answer_text).first()
        self.assertIsNotNone(answer)
        self.assertEqual(answer.self_evaluation, 0)

        answer_text = 'This test answer is very unique 02'
        answer_response = self.create_answer(1, 4, answer_text).json()
        self.client.get(answer_response['evaluation_urls']['sort-of'])  # Evaluate as wrong (1)
        answer = Answer.objects.filter(question_id=1, text=answer_text).first()
        self.assertIsNotNone(answer)
        self.assertEqual(answer.self_evaluation, 1)

        answer_text = 'This test answer is very unique 03'
        answer_response = self.create_answer(1, 4, answer_text).json()
        self.client.get(answer_response['evaluation_urls']['correct'])  # Evaluate as wrong (2)
        answer = Answer.objects.filter(question_id=1, text=answer_text).first()
        self.assertIsNotNone(answer)
        self.assertEqual(answer.self_evaluation, 2)

    def test_answer_evaluation_fail_wrong_evaluation_value(self):
        """test_answer_evaluation_fail_wrong_evaluation_value."""
        answer_text = 'This test answer is very unique'
        answer_response = self.create_answer(1, 4, answer_text).json()
        self.client.get(
            answer_response['evaluation_urls']['correct'].replace(
                'evaluation/2', 'evaluation/{}'.format(333)
            )
        )  # Evaluate as wrong (333)
        answer = Answer.objects.filter(question_id=1, text=answer_text).first()
        self.assertIsNotNone(answer)
        self.assertEqual(answer.self_evaluation, None)


class VoteModelFormTest(LoginAdminByDefaultMixIn, GeneralTestCase):
    """Tests the Vote model related functionality."""

    def upvote_question(self, question_id):
        """Upvote the questioon by sending a get request."""
        return self.client.get(
            reverse(
                'askup:question_upvote',
                kwargs={'question_id': question_id}
            )
        )

    def downvote_question(self, question_id):
        """Downvote the questioon by sending a get request."""
        return self.client.get(
            reverse(
                'askup:question_downvote',
                kwargs={'question_id': question_id}
            )
        )

    @client_user('student01', 'student01')
    def test_upvote_question_success(self):
        """Test upvote question with success."""
        question_id = 2
        original_votes = Vote.objects.filter(question_id=question_id).aggregate(models.Sum('value'))
        self.upvote_question(question_id)
        result_votes = Vote.objects.filter(question_id=question_id).aggregate(models.Sum('value'))
        self.assertEqual(result_votes['value__sum'], original_votes['value__sum'] + 1)

    @client_user('student01', 'student01')
    def test_downvote_question_success(self):
        """Test downvote question with success."""
        question_id = 2
        original_votes = Vote.objects.filter(question_id=question_id).aggregate(models.Sum('value'))
        self.downvote_question(question_id)
        self.client.login(username='student03', password='student03')
        self.downvote_question(question_id)
        result_votes = Vote.objects.filter(question_id=question_id).aggregate(models.Sum('value'))
        self.assertEqual(result_votes['value__sum'], original_votes['value__sum'] - 2)
        self.assertEqual(result_votes['value__sum'], -1)

    @client_user('student01', 'student01')
    def test_upvote_question_fail_own_question(self):
        """Test upvote question with fail by voting for own question."""
        question_id = 1
        original_votes = Vote.objects.filter(question_id=question_id).aggregate(models.Sum('value'))
        self.upvote_question(question_id)
        result_votes = Vote.objects.filter(question_id=question_id).aggregate(models.Sum('value'))
        self.assertEqual(result_votes['value__sum'], original_votes['value__sum'])

    @client_user('student01', 'student01')
    def test_downvote_question_fail_own_question(self):
        """Test downvote question with fail by voting for own question."""
        question_id = 1
        original_votes = Vote.objects.filter(question_id=question_id).aggregate(models.Sum('value'))
        self.downvote_question(question_id)
        result_votes = Vote.objects.filter(question_id=question_id).aggregate(models.Sum('value'))
        self.assertEqual(result_votes['value__sum'], original_votes['value__sum'])

    @client_user('student02_no_orgs', 'student02_no_orgs')
    def test_upvote_question_fail_permission(self):
        """Test upvote question with fail by permissions to the question organization."""
        question_id = 1
        original_votes = Vote.objects.filter(question_id=question_id).aggregate(models.Sum('value'))
        self.upvote_question(question_id)
        result_votes = Vote.objects.filter(question_id=question_id).aggregate(models.Sum('value'))
        self.assertEqual(result_votes['value__sum'], original_votes['value__sum'])

    @client_user('student02_no_orgs', 'student02_no_orgs')
    def test_downvote_question_fail_permission(self):
        """Test downvote question with fail by permissions to the question organization."""
        question_id = 1
        original_votes = Vote.objects.filter(question_id=question_id).aggregate(models.Sum('value'))
        self.downvote_question(question_id)
        result_votes = Vote.objects.filter(question_id=question_id).aggregate(models.Sum('value'))
        self.assertEqual(result_votes['value__sum'], original_votes['value__sum'])


class UserSignUpCase(LoginAdminByDefaultMixIn, GeneralTestCase):
    """Tests the user sign up process."""

    def user_sign_up(self, username, email, first_name, last_name, org, password1, password2):
        """
        Send the Sign Up form and return a response.
        """
        return self.client.post(
            reverse('askup:sign_up'),
            {
                'username': username,
                'email': email,
                'first_name': first_name,
                'last_name': last_name,
                'organization': org,
                'password1': password1,
                'password2': password2,
            }
        )

    def test_sign_up_success_some_spaces_inside_password(self):
        """
        Test sign up success with selected organization but not email restricted one.
        """
        response = self.user_sign_up(
            'testuser01',
            'testuser01@testuser01.com',
            'Test',
            'User',
            '3',
            'Password  String',
            'Password  String',
        )
        self.assertRedirects(response, reverse('askup:sign_up_activation_sent'))
        user = User.objects.filter(username='testuser01').first()
        self.assertNotEqual(user, None)
        user.is_active = True
        user.save()
        login_result = self.client.login(username='testuser01', password='Password  String')
        self.assertEquals(login_result, True)

    def test_sign_up_success_selected_organization(self):
        """
        Test sign up success with selected organization but not email restricted one.
        """
        response = self.user_sign_up(
            'testuser01',
            'testuser01@testuser01.com',
            'Test',
            'User',
            '3',
            'PasswordString',
            'PasswordString',
        )
        self.assertRedirects(response, reverse('askup:sign_up_activation_sent'))
        user = User.objects.filter(username='testuser01').first()
        self.assertNotEqual(user, None)
        orgs = user.qset_set.all()
        self.assertEqual(orgs.count(), 1)
        self.assertEqual(orgs[0].id, 3)

    def test_sign_up_success_selected_organization_and_email_restricted(self):
        """
        Test sign up success with selected one public organization and email restricted one.
        """
        response = self.user_sign_up(
            'testuser01',
            'testuser01@maildomain1.com',
            'Test',
            'User',
            '3',
            'PasswordString',
            'PasswordString',
        )
        self.assertRedirects(response, reverse('askup:sign_up_activation_sent'))
        user = User.objects.filter(username='testuser01').first()
        self.assertNotEqual(user, None)
        orgs = user.qset_set.all().order_by('id')
        self.assertEqual(orgs.count(), 1)
        self.assertEqual(orgs[0].id, 3)

    def test_sign_up_fail_empty_password(self):
        """
        Test sign up fails with empty password.
        """
        empty_pass = '      '
        self.user_sign_up(
            'testuser01',
            'testuser01@testuser01.com',
            'Test',
            'User',
            '3',
            empty_pass,
            empty_pass,
        )
        user = User.objects.filter(username='testuser01').first()
        self.assertIs(user, None)
        login_result = self.client.login(username='testuser01', password=empty_pass)
        self.assertIs(login_result, False)

    def test_sign_up_fail_unmatched_email_restricted_selected(self):
        """
        Test sign up fail on no username specified.
        """
        response = self.user_sign_up(
            'testuser01',
            'testuser01@testuser01.com',
            'Test',
            'User',
            '1',
            'PasswordString',
            'PasswordString',
        )
        self.assertContains(response, 'This organization is an email restricted.')
        user = User.objects.filter(email='testuser01@testuser01.com').first()
        self.assertEqual(user, None)

    def test_sign_up_fail_no_organization_selected(self):
        """
        Test sign up fail on no organization selected.
        """
        self.user_sign_up(
            'testuser01',
            'testuser01@testuser01.com',
            'Test',
            'User',
            '',
            'PasswordString',
            'PasswordString',
        )
        user = User.objects.filter(email='testuser01@testuser01.com').first()
        self.assertEqual(user, None)

    def test_sign_up_fail_no_username_specified(self):
        """
        Test sign up fail on no username specified.
        """
        self.user_sign_up(
            '',
            'testuser01@testuser01.com',
            'Test',
            'User',
            '3',
            'PasswordString',
            'PasswordString',
        )
        user = User.objects.filter(email='testuser01@testuser01.com').first()
        self.assertEqual(user, None)

    def test_sign_up_fail_no_email_specified(self):
        """
        Test sign up fail on no email specified.
        """
        self.user_sign_up(
            'testuser01',
            '',
            'Test',
            'User',
            '3',
            'PasswordString',
            'PasswordString',
        )
        user = User.objects.filter(username='testuser01').first()
        self.assertEqual(user, None)

    def test_sign_up_fail_passwords_doesnt_match(self):
        """
        Test sign up fail on unmatched passwords.
        """
        self.user_sign_up(
            'testuser01',
            'testuser01@testuser01.com',
            'Test',
            'User',
            '3',
            'PasswordString1',
            'PasswordString2',
        )
        user = User.objects.filter(username='testuser01').first()
        self.assertEqual(user, None)

    def test_sign_up_fail_passwords_unspecified(self):
        """
        Test sign up fail on unspecified passwords.
        """
        self.user_sign_up(
            'testuser01',
            'testuser01@testuser01.com',
            'Test',
            'User',
            '3',
            '',
            '',
        )
        user = User.objects.filter(username='testuser01').first()
        self.assertEqual(user, None)

    def test_sign_up_fail_username_has_at(self):
        """
        Test sign up fail on username contained @ symbol.
        """
        self.user_sign_up(
            'testuser01@test',
            'testuser01@testuser01.com',
            'Test',
            'User',
            '3',
            'testuser01',
            'testuser01',
        )
        user = User.objects.filter(username='testuser01@test').first()
        self.assertEqual(user, None)

    def test_sign_up_fail_username_has_non_latin_character(self):
        """
        Test sign up fail on username contained @ symbol.
        """
        self.user_sign_up(
            'Átestuser01',
            'testuser01@testuser01.com',
            'Test',
            'User',
            '3',
            'testuser01',
            'testuser01',
        )
        user = User.objects.filter(username='Átestuser01').first()
        self.assertEqual(user, None)


class StudentDashboardStatisticsCase(LoginAdminByDefaultMixIn, GeneralTestCase):
    """Tests the student dashboard statistics."""

    def get_user_profile(self, user_id):
        """
        Return user profile response.
        """
        return self.client.get(reverse('askup:user_profile', kwargs={'user_id': user_id}))

    def test_user_statistics(self):
        """
        Test the user authentication.
        """
        UserSignUpCase.user_sign_up(
            self,
            'testuser_stat',
            'testuser_stat@maildomain1.com',
            'Test',
            'User',
            '1',
            'tu_stat01',
            'tu_stat01',
        )
        user = User.objects.filter(username='testuser_stat').first()
        self.assertIsNotNone(user)
        user.is_active = True
        user.save()
        organization_id = 1

        self.initial_user_stats_assertions(user.id, organization_id)
        self.active_user_stats_assertions(user.id, organization_id)

    def initial_user_stats_assertions(self, user_id, organization_id):
        """
        Check freshly created user stats.
        """
        organization = Organization.objects.get(id=organization_id)
        rank_place = get_user_place_in_rank_list(user_id, organization_id)
        user_score = get_user_score_by_id(user_id, organization=organization)
        correct_answers = get_user_correct_answers_count(user_id, organization=organization)
        incorrect_answers = get_user_incorrect_answers_count(user_id, organization=organization)
        week_questions = get_student_last_week_questions_count(user_id, organization=organization)
        week_thumbs_ups = get_student_last_week_votes_value(user_id, organization=organization)
        week_correct_answers = get_student_last_week_correct_answers_count(
            user_id,
            organization=organization
        )
        week_incorrect_answers = get_student_last_week_incorrect_answers_count(
            user_id,
            organization=organization
        )

        self.assertEqual(rank_place, 0)  # 6-th user after the mockup ones
        self.assertEqual(user_score, 0)
        self.assertEqual(correct_answers, 0)
        self.assertEqual(incorrect_answers, 0)
        self.assertEqual(week_questions, 0)
        self.assertEqual(week_thumbs_ups, 0)
        self.assertEqual(week_correct_answers, 0)
        self.assertEqual(week_incorrect_answers, 0)

    def active_user_stats_assertions(self, user_id, organization_id):
        """
        Check an active user stats.
        """
        organization = Organization.objects.get(id=organization_id)
        self.client.login(username='testuser_stat', password='tu_stat01')
        question_text = 'Question text'
        question_answer = 'Question answer'
        QuestionModelFormTest.create_question(
            self, question_text, question_answer, 4
        )
        question = Question.objects.filter(text=question_text, user_id=user_id).first()
        self.assertIsNotNone(question)

        self.client.login(username='student01', password='student01')
        VoteModelFormTest.upvote_question(self, question.id)

        self.client.login(username='teacher01', password='teacher01')
        VoteModelFormTest.upvote_question(self, question.id)

        # Wrong
        self.answer_and_evaluate('testuser_stat', 'tu_stat01', question.id, 'Unique answer 01', 0)

        # Kind-of (counts as wrong)
        self.answer_and_evaluate('testuser_stat', 'tu_stat01', question.id, 'Unique answer 02', 1)

        # Correct
        self.answer_and_evaluate('testuser_stat', 'tu_stat01', question.id, 'Unique answer 03', 2)

        # Shouldn't count
        self.answer_and_evaluate('student01', 'student01', question.id, 'Unique answer 04', 2)

        rank_place = get_user_place_in_rank_list(organization_id, user_id)
        user_score = get_user_score_by_id(user_id, organization=organization)
        correct_answers = get_user_correct_answers_count(user_id, organization=organization)
        incorrect_answers = get_user_incorrect_answers_count(user_id, organization=organization)
        week_questions = get_student_last_week_questions_count(user_id, organization=organization)
        week_thumbs_ups = get_student_last_week_votes_value(user_id, organization=organization)
        week_correct_answers = get_student_last_week_correct_answers_count(
            user_id,
            organization=organization
        )
        week_incorrect_answers = get_student_last_week_incorrect_answers_count(
            user_id,
            organization=organization
        )

        self.assertEqual(rank_place, 1)
        self.assertEqual(user_score, 3)
        self.assertEqual(correct_answers, 1)
        self.assertEqual(incorrect_answers, 2)
        self.assertEqual(week_questions, 1)
        self.assertEqual(week_thumbs_ups, 3)
        self.assertEqual(week_correct_answers, 1)
        self.assertEqual(week_incorrect_answers, 2)

    def answer_and_evaluate(self, username, password, question_id, answer_text, evaluation):
        """
        Answer and evaluate question by a specified user.
        """
        self.client.login(username=username, password=password)
        answer_response = AnswerModelFormCase.create_answer(self, 1, 4, answer_text).json()
        self.client.get(
            answer_response['evaluation_urls']['correct'].replace(
                'evaluation/2', 'evaluation/{}'.format(evaluation)
            )
        )
        answer = Answer.objects.filter(question_id=1, text=answer_text).first()
        self.assertIsNotNone(answer)
        self.assertEqual(answer.self_evaluation, evaluation)


class StudentProfileRankListCase(LoginAdminByDefaultMixIn, TestCase):
    """Tests the student dashboard statistics."""

    fixtures = ['groups', 'mockup_data']

    def create_dummy_users(self):
        """
        Create 20 dummy users to fill over a rank list.
        """
        username = 'testuser_rank_list{}'
        first_name = 'Test {}'
        last_name = 'User {}'

        for i in range(20):
            UserSignUpCase.user_sign_up(
                self,
                username.format(i),
                'testuser_rank_list{}@maildomain1.com'.format(),
                first_name.format(i),
                last_name.format(i),
                '1',
                'tu_rlist01',
                'tu_rlist01',
            )

    def get_user_profile_rank_list_response(self, user_id, organization_id):
        """
        Return user profile response.
        """
        return self.client.get(
            reverse(
                'askup:user_profile_rank_list',
                kwargs={
                    'user_id': user_id,
                    'organization_id': organization_id,
                }
            )
        )

    def test_user_rank_list(self):
        """
        Test user rank list.
        """
        username = 'testuser_rank_list01'
        first_name = 'Test'
        last_name = 'User'
        UserSignUpCase.user_sign_up(
            self,
            username,
            'testuser_rank_list01@maildomain1.com',
            first_name,
            last_name,
            '1',
            'tu_rlist01',
            'tu_rlist01',
        )
        user01 = User.objects.filter(username=username).first()
        self.assertIsNotNone(user01)
        user01.is_active = True
        user01.save()

        UserSignUpCase.user_sign_up(
            self,
            'testuser_rank_list02',
            'testuser_rank_list02@maildomain1.com',
            '',
            '',
            '1',
            'tu_rlist02',
            'tu_rlist02',
        )
        user02 = User.objects.filter(username='testuser_rank_list02').first()
        self.assertIsNotNone(user02)
        user02.is_active = True
        user02.save()

        self.initial_user_rank_assertions(user01.id, 1)
        self.active_user_rank_assertions(user01, user02, 1)

    def initial_user_rank_assertions(self, user_id, organization_id):
        """
        Check freshly created user stats.
        """
        organization = Organization.objects.get(id=organization_id)
        rank_place = get_user_place_in_rank_list(organization_id, user_id)
        user_score = get_user_score_by_id(user_id, organization=organization)
        correct_answers = get_user_correct_answers_count(user_id, organization=organization)
        incorrect_answers = get_user_incorrect_answers_count(user_id, organization=organization)
        week_questions = get_student_last_week_questions_count(user_id, organization=organization)
        week_thumbs_ups = get_student_last_week_votes_value(user_id, organization=organization)
        week_correct_answers = get_student_last_week_correct_answers_count(
            user_id,
            organization=organization
        )
        week_incorrect_answers = get_student_last_week_incorrect_answers_count(
            user_id,
            organization=organization
        )

        self.assertEqual(rank_place, 0)  # 6-th user after the mockup ones
        self.assertEqual(user_score, 0)
        self.assertEqual(correct_answers, 0)
        self.assertEqual(incorrect_answers, 0)
        self.assertEqual(week_questions, 0)
        self.assertEqual(week_thumbs_ups, 0)
        self.assertEqual(week_correct_answers, 0)
        self.assertEqual(week_incorrect_answers, 0)

    def active_user_rank_assertions(self, user01, user02, organization_id):
        """
        Check an active user stats.
        """
        self.client.login(username='testuser_rank_list01', password='tu_rlist01')
        question_text = 'Question text'
        question_answer = 'Question answer'
        QuestionModelFormTest.create_question(
            self, question_text, question_answer, 4
        )
        question = Question.objects.filter(text=question_text, user_id=user01.id).first()

        self.client.login(username='student01', password='student01')
        VoteModelFormTest.upvote_question(self, question.id)

        self.client.login(username='teacher01', password='teacher01')
        VoteModelFormTest.upvote_question(self, question.id)

        # Wrong
        self.answer_and_evaluate('testuser_rank_list', 'tu_rlist01', question.id, 'Unique answer 01', 0)

        # Kind-of (counts as wrong)
        self.answer_and_evaluate('testuser_rank_list', 'tu_rlist01', question.id, 'Unique answer 02', 1)

        # Correct
        self.answer_and_evaluate('testuser_rank_list', 'tu_rlist01', question.id, 'Unique answer 03', 2)

        # Shouldn't count
        self.answer_and_evaluate('student01', 'student01', question.id, 'Unique answer 04', 2)

        rows, _ = get_user_profile_rank_list_and_total_users(user01.id, user01.id, organization_id)

        for place, return_user_id, name, questions, thumbs_up in rows:
            if return_user_id == user01.id:
                self.assertEqual(place, 1)
                self.assertEqual(
                    name,
                    '{} {} ({})'.format(
                        user01.first_name, user01.last_name, user01.username
                    )
                )
                self.assertEqual(thumbs_up, 3)
                self.assertEqual(questions, 1)

            if return_user_id == user02.id:
                self.assertEqual(place, 7)
                self.assertEqual(
                    name,
                    '{}'.format(user02.username)
                )
                self.assertEqual(thumbs_up, 0)
                self.assertEqual(questions, 0)

        response = self.get_user_profile_rank_list_response(user01.id, 1)

        # We've got only three users that were made it into the rank list (have any questions)
        self.assertContains(response, 'Total: 3 users')

    def answer_and_evaluate(self, username, password, question_id, answer_text, evaluation):
        """
        Answer and evaluate question by a specified user.
        """
        self.client.login(username=username, password=password)
        answer_response = AnswerModelFormCase.create_answer(self, 1, 4, answer_text).json()
        self.client.get(
            answer_response['evaluation_urls']['correct'].replace(
                'evaluation/2', 'evaluation/{}'.format(evaluation)
            )
        )
        answer = Answer.objects.filter(question_id=1, text=answer_text).first()
        self.assertIsNotNone(answer)
        self.assertEqual(answer.self_evaluation, evaluation)

    @client_user('admin', 'admin')
    def test_no_users_rank_in_organization_2(self):
        """
        Test that there is no users in the rank list of Organization 3.
        """
        # 5 - user assigned to "Organization 2", 2 - "Organization 2" id
        response = self.get_user_profile_rank_list_response(5, 2)

        # We've got no users that were made it into the rank list (have any questions)
        self.assertContains(response, 'Total: 0 users')


class StudentDashboardMyQuestionsCase(LoginAdminByDefaultMixIn, GeneralTestCase):
    """Tests the student dashboard statistics."""

    def get_user_profile(self, user_id, organization_id):
        """
        Return user profile response.
        """
        return self.client.get(
            reverse(
                'askup:user_profile',
                kwargs={'user_id': user_id, 'organization_id': organization_id}
            )
        )

    def get_qset_user_questions(self, qset_id, user_id):
        """
        Return qset user response.
        """
        return self.client.get(
            reverse(
                'askup:qset_user_questions',
                kwargs={
                    'qset_id': qset_id,
                    'user_id': user_id,
                }
            )
        )

    @client_user('student01', 'student01')
    def test_my_questions(self):
        """
        Test my questions.
        """
        user_id = 3  # student01 from the mockups
        qset_id = 4  # Qset 1-1 from the mockups
        response = self.get_user_profile(user_id, 1)

        self.assertContains(response, 'Qset 1-1')
        self.assertContains(response, '2 questions')
        self.assertContains(response, 'My questions')

        json_response = self.get_qset_user_questions(qset_id, user_id)
        self.assertContains(json_response, 'Question 1-1-1')
        self.assertContains(json_response, 'Question 1-1-3')
        self.assertNotContains(json_response, 'Question 1-1-2')

    def test_user_questions(self):
        """
        Test user questions.
        """
        user_id = 3  # student01 from the mockups
        response = self.get_user_profile(user_id, 1)

        self.assertContains(response, 'User\'s questions')

    @client_user('student01', 'student01')
    def test_you_have_not_questions(self):
        """
        Test you have no questions.
        """
        user_id = 3  # student01 from the mockups
        Question.objects.filter(user_id=user_id).delete()
        response = self.get_user_profile(user_id, 1)

        self.assertContains(response, 'You haven’t created any questions yet.')

    @client_user('student01', 'student01')
    def test_user_has_no_questions(self):
        """
        Test user has no questions.
        """
        user_id = 5  # student03 from the mockups
        Question.objects.filter(user_id=user_id).delete()
        response = self.get_user_profile(user_id, 1)

        self.assertContains(response, 'This user hasn’t created any questions yet.')


class UserDashboardMySubscriptionsCase(LoginAdminByDefaultMixIn, GeneralTestCase):
    """
    Tests the "My subscriptions" section of the user dashboard.
    """

    @staticmethod
    def get_my_subscriptions(self):
        """
        Return My subscriptions response.
        """
        return self.client.get(
            reverse(
                'askup:my_subscriptions',
                kwargs={}
            )
        )

    @staticmethod
    def change_qset_subscription(self, qset_id, subscribe):
        """
        Change qset subscription status (subscribe/unsubscribe).
        """
        return self.client.get(
            reverse(
                'askup:qset_subscription',
                kwargs={'qset_id': qset_id, 'subscribe': subscribe}
            )
        )

    @client_user('student01', 'student01')
    def test_my_subscriptions(self):
        """
        Test my subscriptions.
        """
        qset_id = 4  # Qset 1-1 from the mockups
        response = self.get_my_subscriptions(self)

        self.assertContains(response, 'Organization 1')
        self.assertContains(response, 'Qset 1-1')
        self.assertContains(response, 'Qset 1-2')
        self.assertContains(response, 'Qset 1-3')
        self.assertContains(response, 'Qset 1-4')
        self.assertContains(response, 'SUBSCRIBE')
        self.assertNotContains(response, 'UNSUBSCRIBE')

        self.change_qset_subscription(self, qset_id, 'subscribe')  # Subscribe current user to the selected qset

        response = self.get_my_subscriptions(self)
        self.assertContains(response, 'UNSUBSCRIBE')

        self.change_qset_subscription(self, qset_id, 'unsubscribe')  # Unsubscribe current user from the selected qset

        response = self.get_my_subscriptions(self)
        self.assertNotContains(response, 'UNSUBSCRIBE')

    @client_user('student01', 'student01')
    def test_subscription_success(self):
        """
        Test successful subscription.
        """
        qset_id = 4  # Qset 1-1 from the mockups
        # Subscribe current user to the selected qset
        response = self.change_qset_subscription(self, qset_id, 'subscribe').json()
        self.assertEqual(response['result'], 'success')
        self.assertEqual(
            response['url'],
            reverse(
                'askup:qset_subscription',
                kwargs={'qset_id': qset_id, 'subscribe': 'unsubscribe'}
            )
        )

        # Unsubscribe current user to the selected qset
        response = self.change_qset_subscription(self, qset_id, 'unsubscribe').json()
        self.assertEqual(response['result'], 'success')
        self.assertEqual(
            response['url'],
            reverse(
                'askup:qset_subscription',
                kwargs={'qset_id': qset_id, 'subscribe': 'subscribe'}
            )
        )

    @client_user('student01', 'student01')
    def test_subscription_fail(self):
        """
        Test failed on permission basis subscription.
        """
        qset_id = 10  # Qset 4-1 from the mockups
        # Subscribe current user to the selected qset
        response = self.change_qset_subscription(self, qset_id, 'subscribe').json()
        self.assertEqual(response['result'], 'fail')
        self.assertEqual(
            response['url'],
            reverse(
                'askup:qset_subscription',
                kwargs={'qset_id': qset_id, 'subscribe': 'subscribe'}
            )
        )

        # Unsubscribe current user to the selected qset
        response = self.change_qset_subscription(self, qset_id, 'unsubscribe').json()
        self.assertEqual(response['result'], 'fail')
        self.assertEqual(
            response['url'],
            reverse(
                'askup:qset_subscription',
                kwargs={'qset_id': qset_id, 'subscribe': 'unsubscribe'}
            )
        )


class TestSubscriptionsMailing(TestCase):
    """
    Testing the subject subscription mailing functionality.
    """

    fixtures = ['groups', 'mockup_data']

    @client_user('student01', 'student01')
    @patch('askup.utils.general.do_send_subscriptions_to_recipients')
    def test_subscriptions_sending_no_actual_subscriptions(self, mock_do_send_subscriptions_to_recipients):
        """
        Test subscriptions sending.
        """
        mock_do_send_subscriptions_to_recipients.return_value = None
        mock_do_send_subscriptions_to_recipients.assert_not_called()
        send_subscription_emails()

    @client_user('student01', 'student01')
    @patch('askup.utils.general.do_send_subscriptions_to_recipients')
    def test_subscriptions_sending_with_subscriptions(self, mock_do_send_subscriptions_to_recipients):
        """
        Test subscriptions sending.
        """
        qset_id_1 = 4  # Qset 1-1
        qset_id_2 = 5  # Qset 1-2
        text_1 = 'Test question 1-1'
        text_2 = 'Test question 1-2'
        answer_text_1 = 'Test question answer 1-1'
        answer_text_2 = 'Test question answer 1-2'
        QuestionModelFormTest.qset_create_question(self, text_1, answer_text_1, qset_id_1)
        QuestionModelFormTest.qset_create_question(self, text_2, answer_text_2, qset_id_2)
        UserDashboardMySubscriptionsCase.change_qset_subscription(self, qset_id_1, 'subscribe')
        send_subscription_emails()

        user_subscriptions = defaultdict(list)
        user_subscriptions['curious@student.org###Curious'] = [(qset_id_1, 'Qset 1-1', 1)]
        question_answer_url = reverse('askup:question_answer', kwargs={'question_id': 5, 'qset_id': qset_id_1})
        qset_questions = {
            qset_id_1: (
                f'<ul>\n<li><a href="{settings.SERVER_PROTOCOL}://{settings.SERVER_HOSTNAME}' +
                f'{question_answer_url}" title="{text_1}">{text_1}</a></li>\n</ul>'
            )
        }

        mock_do_send_subscriptions_to_recipients.return_value = None
        mock_do_send_subscriptions_to_recipients.assert_called_once_with(user_subscriptions, qset_questions)


class TestOrganizationQuiz(LoginAdminByDefaultMixIn, GeneralTestCase):
    """Tests the Organizations view."""

    def start_quiz(self, organization_id, filter):
        """
        Start quiz by organization id and filter.
        """
        url = '{}?filter={}&quiz_start=1&is_organization=1'.format(
            reverse('askup:start_quiz_all', kwargs={'qset_id': organization_id}),
            filter
        )
        return self.client.get(url)

    def create_answer_and_evaluate(self, user_id, first_question_id, organization_id, filter):
        """
        Start quiz by organization id and filter.
        """
        first_question_answer = Answer.objects.create(
            question_id=first_question_id,
            text='Answer text',
            user_id=user_id,
        )
        url = '{}?filter={}'.format(
            reverse(
                'askup:answer_evaluate',
                kwargs={
                    'answer_id': first_question_answer.id, 'qset_id': organization_id, 'evaluation': 2
                }
            ),
            filter
        )
        return self.client.get(url)

    def test_if_quiz_button_present(self):
        """
        Test if quiz select box is present due to the presence of the questions in the organization.
        """
        organization_id = 1  # Organization 1 - has questions
        response = self.client.get(reverse('askup:organization', kwargs={'pk': organization_id}))
        self.assertContains(response, 'Start quiz by...')

    def test_if_quiz_button_hidden(self):
        """
        Test if quiz select box is hidden due to no questions under the organization.
        """
        organization_id = 2  # Organization 2 - has no questions
        response = self.client.get(reverse('askup:organization', kwargs={'pk': organization_id}))
        self.assertNotContains(response, 'Start quiz by...')

    def test_if_cache_fills_with_the_ids(self):
        """
        Test if the cache is filling up with the questions ids on quiz successful start.
        """
        organization_id = 1  # Organization 1
        user_id = 1  # Admin
        self.start_quiz(organization_id, "all")  # Redirects us to the first question in the queue and leaves 3 in cache
        cache_key = 'quiz_user_{}_qset_{}'.format(user_id, organization_id)
        questions_ids = cache.get(cache_key)
        self.assertEqual(len(questions_ids), 3)

    def test_if_quiz_continues_after_middle_question_deleted(self):
        """
        Test if quiz continues successfuly after the next (but not last) question was deleted.
        """
        organization_id = 1  # Organization 1
        user_id = 1  # admin
        filter = 'all'

        # Redirects us to the first question in the queue and leaves 3 in cache
        first_question_response = self.start_quiz(organization_id, filter)

        first_question_id = first_question_response.url.split('/')[3]

        # Has all the questions but the first one (it was alreade popped out)
        cache_key = 'quiz_user_{}_qset_{}'.format(user_id, organization_id)

        questions_ids = cache.get(cache_key)
        Question.objects.filter(id=questions_ids[0]).delete()
        second_question_response = self.create_answer_and_evaluate(user_id, first_question_id, organization_id, filter)
        second_question_id = second_question_response.url.split('/')[3]
        self.assertEqual(second_question_id, str(questions_ids[1]))

    @client_user('student01', 'student01')
    def test_if_quiz_finishes_after_last_question_deleted(self):
        """
        Test if quiz redirects user to the organization after the next (and last) question was deleted.
        """
        organization_id = 1  # Organization 1
        user_id = 3  # student01
        filter = 'mine'

        # Redirects us to the first question in the queue and leaves 3 in cache
        first_question_response = self.start_quiz(organization_id, filter)

        first_question_id = first_question_response.url.split('/')[3]

        # Has all the questions but the first one (it was alreade popped out)
        cache_key = 'quiz_user_{}_qset_{}'.format(user_id, organization_id)

        questions_ids = cache.get(cache_key)
        Question.objects.filter(id=questions_ids[0]).delete()

        # Redirected to the organization instead of inexistent last question in the quiz
        second_question_response = self.create_answer_and_evaluate(user_id, first_question_id, organization_id, filter)
        organization_url = reverse('askup:organization', kwargs={'pk': organization_id})
        self.assertEqual(second_question_response.url, organization_url)
