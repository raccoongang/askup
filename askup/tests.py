import logging

from django.conf import settings
from django.contrib.auth.models import AnonymousUser, User
from django.contrib.sessions.middleware import SessionMiddleware
from django.http import HttpResponseRedirect
from django.test import RequestFactory, TestCase
from django.urls import reverse

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

    def test_teacher_features_presence(self):
        """Test for a teacher features presence."""
        pass

    def test_admin_features_presence(self):
        """Test for an admin features presence."""
        pass


class QsetListView(TestCase):
    """Tests the Qset views (all three types subsets/questions/mixed)."""

    def setUp(self):
        """Set up the test assets."""
        settings.DEBUG = False
        self.factory = RequestFactory()

    def test_has_subsets(self):
        """Test Qset list view with the subsets."""
        pass

    def test_has_no_subsets(self):
        """Test Qset list view w/o the subsets."""
        pass

    def test_has_questions(self):
        """Test Qset list view with the questions."""
        pass

    def test_has_no_questions(self):
        """Test Qset list view w/o the questions."""
        pass

    def test_student_features_presence(self):
        """Test for a student features presence."""
        pass

    def test_teacher_features_presence(self):
        """Test for a teacher features presence."""
        pass

    def test_admin_features_presence(self):
        """Test for an admin features presence."""
        pass


# class CreateQset(TestCase):
#    def setUp(self):
#        self.admin = User.objects.create_superuser('test_admin', 'test_admin@example.com', 'test_admin')
#        self.teacher = User.objects.create_user(
#            'test_admin',
#            'test_admin@example.com',
#            'test_admin',
#            groups=[1]
#        )
