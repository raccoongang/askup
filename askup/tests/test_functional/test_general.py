import logging

from django.conf import settings
from django.contrib.auth.models import AnonymousUser, User
from django.contrib.sessions.middleware import SessionMiddleware
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.test import RequestFactory, TestCase
from django.urls import reverse

from askup.mixins.tests import LoginAdminByDefaultMixIn
from askup.models import Answer, Qset, Question
from askup.views import login_view


log = logging.getLogger(__name__)


def client_user(username, password):
    """Decorate a TestCase class method to login client by username and password provided."""
    def client_wrapper(func):
        def wrapping_function(*args, **kwargs):
            args[0].client.login(username=username, password=password)
            result = func(*args, **kwargs)
            args[0].default_login()
            return result

        return wrapping_function

    return client_wrapper


class UserAuthenticationCase(LoginAdminByDefaultMixIn, TestCase):
    """Tests the user authentication."""

    def setUp(self):
        """Set up the test assets."""
        settings.DEBUG = False
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


class OrganizationsListView(LoginAdminByDefaultMixIn, TestCase):
    """Tests the Organizations view."""

    fixtures = ['groups', 'mockup_data']

    def setUp(self):
        """Set up the test assets."""
        settings.DEBUG = False
        self.default_login()

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


class OrganizationListView(LoginAdminByDefaultMixIn, TestCase):
    """Tests the Organization view."""

    fixtures = ['groups', 'mockup_data']

    def setUp(self):
        """Set up the test assets."""
        settings.DEBUG = False
        self.default_login()

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


class QsetListView(LoginAdminByDefaultMixIn, TestCase):
    """Tests the Qset views (for questions only type)."""

    fixtures = ['groups', 'mockup_data']

    def setUp(self):
        """Set up the test assets."""
        settings.DEBUG = False
        self.default_login()

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


class QsetModelFormTest(LoginAdminByDefaultMixIn, TestCase):
    """Tests the Qset model form (CRUD etc.)."""

    fixtures = ['groups', 'mockup_data']

    def setUp(self):
        """Set up the test assets."""
        settings.DEBUG = False
        self.default_login()

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
        move_qset = get_object_or_404(Qset, pk=4)
        move_qset_count = move_qset.questions_count
        org_qset['orig_count'] = get_object_or_404(Qset, pk=org_qset['id']).questions_count
        move_qset.parent_qset_id = 10
        move_qset.save()
        org_qset['new_count'] = get_object_or_404(Qset, pk=org_qset['id']).questions_count
        self.assertEqual(
            org_qset['new_count'],
            org_qset['orig_count'] - move_qset_count
        )


class QuestionModelFormTest(LoginAdminByDefaultMixIn, TestCase):
    """Tests the Question model form (CRUD etc.)."""

    fixtures = ['groups', 'mockup_data']

    def setUp(self):
        """Set up the test assets."""
        settings.DEBUG = False
        self.default_login()

    def qset_create_question(self, text, answer_text, qset_id, form_qset_id=None):
        """Create question by qset's "Generate question" form."""
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
        self.client.post(
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
        answer_text = 'Test answer 1'

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


class AnswerModelFormTest(LoginAdminByDefaultMixIn, TestCase):
    """Tests the Answer model related forms."""

    fixtures = ['groups', 'mockup_data']

    def setUp(self):
        """Set up the test assets."""
        settings.DEBUG = False
        self.default_login()

    def create_answer(self, question_id, answer_text):
        """create_answer."""
        return self.client.post(
            reverse('askup:question_answer', kwargs={'question_id': question_id}),
            {'text': answer_text}
        )

    def evaluate_answer(self, answer_id, self_evaluation):
        """evaluate_answer."""
        return self.client.get(
            reverse(
                'askup:answer_evaluate',
                kwargs={
                    'answer_id': answer_id,
                    'evaluation': self_evaluation,
                }
            )
        )

    def test_answer_the_question_success(self):
        """test_answer_the_question_success."""
        answer_text = 'Test answer'
        response = self.create_answer(1, answer_text).json()
        answer = get_object_or_404(Answer, pk=response['answer_id'])
        self.assertEqual(response['result'], 'success')
        self.assertEqual(answer.text, answer_text)

    def test_answer_the_question_fail_inexistent_question(self):
        """test_answer_the_question_fail_inexistent_question."""
        answer_text = 'Test answer'
        inexistant_question_id = 111

        with self.assertRaises(ValueError):
            self.create_answer(inexistant_question_id, answer_text).json()

    def test_answer_the_question_fail_empty_answer(self):
        """test_answer_the_question_fail_empty_answer."""
        answer_text = ''
        inexistant_question_id = 1
        response = self.create_answer(inexistant_question_id, answer_text).json()
        self.assertEqual(response['result'], 'error')

    def test_answer_evaluation_success(self):
        """test_answer_evaluation_success."""
        answer_text = 'Test answer'
        answer_response = self.create_answer(1, answer_text).json()
        self.evaluate_answer(answer_response['answer_id'], 0)
        answer = get_object_or_404(Answer, pk=answer_response['answer_id'])
        self.assertEqual(answer.self_evaluation, 0)

        answer_response = self.create_answer(1, answer_text).json()
        self.evaluate_answer(answer_response['answer_id'], 1)
        answer = get_object_or_404(Answer, pk=answer_response['answer_id'])
        self.assertEqual(answer.self_evaluation, 1)

        answer_response = self.create_answer(1, answer_text).json()
        self.evaluate_answer(answer_response['answer_id'], 2)
        answer = get_object_or_404(Answer, pk=answer_response['answer_id'])
        self.assertEqual(answer.self_evaluation, 2)

    def test_answer_evaluation_fail_wrong_evaluation_value(self):
        """test_answer_evaluation_fail_wrong_evaluation_value."""
        answer_text = 'Test answer'
        answer_response = self.create_answer(1, answer_text).json()
        self.evaluate_answer(answer_response['answer_id'], 3)
        answer = get_object_or_404(Answer, pk=answer_response['answer_id'])
        self.assertEqual(answer.self_evaluation, None)
