import logging

from django.conf import settings
from django.contrib.auth.models import AnonymousUser, User
from django.contrib.sessions.middleware import SessionMiddleware
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.test import RequestFactory, TestCase
from django.urls import reverse

from .models import Qset, Question
from .views import login_view, OrganizationsView


log = logging.getLogger(__name__)


class UserAuthenticationCase(TestCase):
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
        middleware = SessionMiddleware()
        middleware.process_request(request)
        request.session.save()
        request.user = AnonymousUser()
        response = login_view(request)
        self.assertIs(isinstance(response, HttpResponseRedirect), True)


class OrganizationsListView(TestCase):
    """Tests the Organizations view."""

    fixtures = ['groups', 'mockup_data']

    def setUp(self):
        """Set up the test assets."""
        settings.DEBUG = False
        self.factory = RequestFactory()

    def test_has_organizations(self):
        """Test an Organizations view with the organizations."""
        request = self.factory.get(reverse('askup:organizations'))
        middleware = SessionMiddleware()
        middleware.process_request(request)
        request.session.save()
        request.user = User.objects.get(id=2)  # teacher02 from the mockup_data
        response = OrganizationsView.as_view()(request)
        self.assertContains(response, 'Organization 1')
        self.assertNotContains(response, 'You didn\'t apply to any organization')

    def test_has_no_organizations(self):
        """Test an Organizations view w/o the organizations."""
        request = self.factory.get(reverse('askup:organizations'))
        middleware = SessionMiddleware()
        middleware.process_request(request)
        request.session.save()
        request.user = User.objects.get(id=4)  # student02_no_orgs from the mockup_data
        response = OrganizationsView.as_view()(request)
        self.assertContains(response, 'You didn\'t apply to any organization')


class OrganizationListView(TestCase):
    """Tests the Organization view."""

    fixtures = ['groups', 'mockup_data']

    def setUp(self):
        """Set up the test assets."""
        settings.DEBUG = False
        self.client.login(username='admin', password='admin')

    def test_has_subsets(self):
        """Test an Organization view with the subsets."""
        response = self.client.get(reverse('askup:organization', kwargs={'pk': 1}))
        self.assertContains(response, 'Qset 1-1')
        self.assertNotContains(response, 'There are no subsets here.')

    def test_has_no_subsets(self):
        """Test an Organization view w/o the subsets."""
        response = self.client.get(reverse('askup:organization', kwargs={'pk': 3}))
        self.assertContains(response, 'There are no subsets here.')

    def test_admin_features_presence(self):
        """Test for an admin features presence."""
        response = self.client.get(reverse('askup:organization', kwargs={'pk': 1}))
        self.assertContains(response, 'data-target="#modal-edit-qset"')
        self.assertContains(response, 'data-target="#modal-new-qset">New subset</a>')

    def test_teacher_features_presence(self):
        """Test for a teacher features presence."""
        self.client.login(username='teacher01', password='teacher01')
        response = self.client.get(reverse('askup:organization', kwargs={'pk': 1}))
        self.assertContains(response, 'data-target="#modal-new-qset">New subset</a>')
        self.assertNotContains(response, 'data-target="#modal-edit-qset"')
        self.client.login(username='admin', password='admin')


class QsetListView(TestCase):
    """Tests the Qset views (all three types subsets/questions/mixed)."""

    fixtures = ['groups', 'mockup_data']

    def setUp(self):
        """Set up the test assets."""
        settings.DEBUG = False
        self.client.login(username='admin', password='admin')

    def test_type_2_has_subsets_and_questions(self):
        """Test Qset list view with the subsets."""
        response = self.client.get(reverse('askup:qset', kwargs={'pk': 4}))
        self.assertContains(response, 'Qset 1-1-1')
        self.assertContains(response, 'Question 1-1-1')
        self.assertNotContains(response, 'There are no subsets here.')
        self.assertNotContains(response, 'There are no questions here.')

    def test_type_0_has_no_subsets_and_questions(self):
        """Test Qset list view w/o the subsets and questions."""
        response = self.client.get(reverse('askup:qset', kwargs={'pk': 6}))
        self.assertContains(response, 'There are no subsets here.')
        self.assertContains(response, 'There are no questions here.')

    def test_type_1_has_no_subsets(self):
        """Test Qset list view w/o the subsets."""
        response = self.client.get(reverse('askup:qset', kwargs={'pk': 8}))
        self.assertContains(response, 'There are no subsets here.')

    def test_type_2_has_no_questions(self):
        """Test Qset list view w/o the questions."""
        response = self.client.get(reverse('askup:qset', kwargs={'pk': 9}))
        self.assertContains(response, 'There are no questions here.')

    def test_student_features_presence(self):
        """Test for a student features presence."""
        self.client.login(username='student01', password='student01')
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
        self.client.login(username='admin', password='admin')

    def test_teacher_features_presence(self):
        """Test for a teacher features presence."""
        self.client.login(username='teacher01', password='teacher01')
        response = self.client.get(reverse('askup:qset', kwargs={'pk': 4}))
        self.assertContains(response, 'Generate Question')
        self.assertContains(response, 'data-target="#modal-new-qset">New subset</a>')
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
        self.client.login(username='admin', password='admin')

    def test_admin_features_presence(self):
        """Test for an admin features presence."""
        response = self.client.get(reverse('askup:qset', kwargs={'pk': 4}))
        self.assertContains(response, 'Generate Question')
        self.assertContains(response, 'data-target="#modal-new-qset">New subset</a>')
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


class QsetModelFormTest(TestCase):
    """Tests the Qset model form (CRUD etc.)."""

    fixtures = ['groups', 'mockup_data']

    def setUp(self):
        """Set up the test assets."""
        settings.DEBUG = False
        self.client.login(username='admin', password='admin')

    def create_qset(self, name, type, parent_qset_id):
        """Create qset with the parameters."""
        self.client.post(
            reverse(
                'askup:qset_create'
            ),
            {
                'name': name,
                'parent_qset': parent_qset_id,
                'type': type
            }
        )

    def create_qset_success(self, name, type, parent_qset_id):
        """Create qset and look for a success."""
        self.create_qset(name, type, parent_qset_id)
        qset = get_object_or_404(Qset, name=name, parent_qset_id=parent_qset_id)
        self.assertEqual(qset.name, name)
        self.assertEqual(qset.type, type)

    def create_qset_fail_forbidden_parent(self, name, type, parent_qset_id):
        """Create qset and look for a fail."""
        self.client.login(username='teacher01', password='teacher01')

        with self.assertRaises(Http404):
            self.create_qset(name, type, parent_qset_id)
            get_object_or_404(Qset, name=name, parent_qset_id=parent_qset_id)

        self.client.login(username='admin', password='admin')

    def update_qset(self, qset_id, new_name, new_type, new_parent_qset_id):
        """Update qset with the parameters."""
        self.client.post(
            reverse(
                'askup:qset_update',
                kwargs={'pk': qset_id}
            ),
            {
                'name': new_name,
                'parent_qset': new_parent_qset_id,
                'type': new_type
            }
        )

    def update_qset_success(self, qset_id, new_name, new_type, new_parent_qset_id):
        """Update qset and look for a success."""
        self.update_qset(qset_id, new_name, new_type, new_parent_qset_id)
        qset = get_object_or_404(Qset, pk=qset_id)
        self.assertEqual(qset.name, new_name)
        self.assertEqual(qset.type, new_type)

    def test_create_qset(self):
        """Test qset creation."""
        parent_qset_id = 4

        name = 'test qset mixed'
        type = 0
        self.create_qset_success(name, type, parent_qset_id)

        name = 'test qset subsets only'
        type = 1
        self.create_qset_success(name, type, parent_qset_id)

        name = 'test qset questions only'
        type = 2
        self.create_qset_success(name, type, parent_qset_id)

        name = 'test qset mixed forbidden parent'
        type = 0
        self.create_qset_fail_forbidden_parent(name, type, 3)

    def test_update_qset(self):
        """Test qset updating."""
        parent_qset_id = 1
        qset_id = 4
        name = 'Qset 1-1 updated'
        type = 0
        self.update_qset_success(qset_id, name, type, parent_qset_id)

    def test_update_qset_fail_forbidden_parent(self):
        """Test qset updating with the forbiden parent."""
        self.client.login(username='teacher01', password='teacher01')

        with self.assertRaises(Http404):
            name = 'Qset 2-1 updated'
            parent_qset_id = 3
            self.update_qset(6, name, 1, parent_qset_id)
            get_object_or_404(Qset, name=name, parent_qset_id=parent_qset_id)

        self.client.login(username='admin', password='admin')

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

    def test_delete_qset_as_teacher_success(self):
        """Test successful qset deletion by the teacher."""
        # Try to delete Qset 1-2 by the teacher01
        self.client.login(username='teacher01', password='teacher01')

        with self.assertRaises(Http404):
            self.delete_and_get_qset(5)

        self.client.login(username='admin', password='admin')

    def test_delete_qset_as_student_fail(self):
        """Test failed by permissions student qset deletion."""
        # Try to delete Qset 1-1 by the student01
        self.client.login(username='student01', password='student01')
        self.delete_and_get_qset(4)
        self.client.login(username='admin', password='admin')

    def test_delete_qset_as_teacher_fail(self):
        """Test failed by permissions teacher qset deletion."""
        # Try to delete Qset 4-1 by the teacher01
        self.client.login(username='teacher01', password='teacher01')
        self.delete_and_get_qset(11)
        self.client.login(username='admin', password='admin')

    def test_parent_questions_count_update_on_delete(self):
        """Test parent question count update on qset delete."""
        qsets = {
            'org_qset': {
                'id': 1,  # Organization 1 from the mockups
                'orig_count': None,
                'new_count': None,
            },
            'first_qset': {
                'id': 4,  # Qset 1-1 from the mockups
                'orig_count': None,
                'new_count': None,
            },
        }
        delete_qset = get_object_or_404(Qset, pk=7)
        delete_qset_count = delete_qset.questions_count

        for key in qsets.keys():
            qsets[key]['orig_count'] = get_object_or_404(Qset, pk=qsets[key]['id']).questions_count

        delete_qset.delete()

        for key in qsets.keys():
            qsets[key]['new_count'] = get_object_or_404(Qset, pk=qsets[key]['id']).questions_count

        org_qset = qsets['org_qset']
        first_qset = qsets['first_qset']
        self.assertEqual(
            org_qset['new_count'],
            org_qset['orig_count']
        )
        self.assertEqual(
            first_qset['new_count'],
            first_qset['orig_count'] + delete_qset_count
        )

    def test_parent_questions_count_update_on_parent_change(self):
        """Test parent questions count update on parent change."""
        qsets = {
            'org_qset': {
                'id': 1,  # Organization 1 from the mockups
                'orig_count': None,
                'new_count': None,
            },
            'first_qset': {
                'id': 4,  # Qset 1-1 from the mockups
                'orig_count': None,
                'new_count': None,
            },
        }
        move_qset = get_object_or_404(Qset, pk=7)
        move_qset_count = move_qset.questions_count

        for key in qsets.keys():
            qsets[key]['orig_count'] = get_object_or_404(Qset, pk=qsets[key]['id']).questions_count

        move_qset.parent_qset_id = 10
        move_qset.save()

        for key in qsets.keys():
            qsets[key]['new_count'] = get_object_or_404(Qset, pk=qsets[key]['id']).questions_count

        org_qset = qsets['org_qset']
        first_qset = qsets['first_qset']
        self.assertEqual(
            org_qset['new_count'],
            org_qset['orig_count'] - move_qset_count
        )
        self.assertEqual(
            first_qset['new_count'],
            first_qset['orig_count'] - move_qset_count
        )


class QuestionModelFormTest(TestCase):
    """Tests the Question model form (CRUD etc.)."""

    fixtures = ['groups', 'mockup_data']

    def setUp(self):
        """Set up the test assets."""
        settings.DEBUG = False
        self.client.login(username='admin', password='admin')

    def create_question(self, text, answer_text, qset_id):
        """Create question with the parameters."""
        self.client.post(
            reverse(
                'askup:qset_question_create',
                kwargs={'qset_id': qset_id},
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
            self.create_question(text, answer_text, qset_id)
            get_object_or_404(Question, text=text, answer_text=answer_text, qset_id=qset_id)

    def test_question_fail_forbidden_parent(self):
        """Create question and look for a fail because on forbidden qset."""
        self.client.login(username='teacher01', password='teacher01')
        text = 'Test question that failed 2'
        answer_text = 'Test question answer that failed 2'
        qset_id = 11  # Organization 3 -> Qset 4-1 (forbidden for the teacher01)

        with self.assertRaises(Http404):
            self.create_question(text, answer_text, qset_id)
            get_object_or_404(Question, text=text, qset_id=qset_id)

        self.client.login(username='admin', password='admin')

    def test_create_question_success(self):
        """Test question creation."""
        qset_id = 4
        text = 'Test question 1'
        answer_text = 'Test answer 1'

        self.create_question(text, answer_text, qset_id)
        question = get_object_or_404(Question, text=text, qset_id=qset_id)
        self.assertEqual(question.text, text)
        self.assertEqual(question.answer_text, answer_text)
        self.assertEqual(question.qset_id, qset_id)

    def test_update_question(self):
        """Test question updating."""
        pass

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
            self.delete_and_get_question(1)  # Try to delete Question 1-1 by the admin

    def test_delete_question_failed_by_permissions(self):
        """Test failed by permissions question deletion."""
        self.client.login(username='student01', password='student01')
        self.delete_and_get_question(2)  # Try to delete Question 1-1-2 (teacher01) by the student01
        self.client.login(username='admin', password='admin')

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
        question = Question.objects.create(
            text='Question count test 1',
            answer_text='Question count test 1',
            qset=4,
            blooms_tag=0,
        )

        for key in qsets.keys():
            qsets[key]['orig_count'] = get_object_or_404(Qset, pk=qsets[key]['id']).questions_count

        question.delete()

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
