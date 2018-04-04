import logging

from django.conf import settings
from django.test import TestCase

from askup.models import Qset, Question
from askup.utils.general import (
    get_checked_user_organization_by_id,
    get_first_user_organization,
    get_user_organizations_for_filter,
)
from askup.utils.views import select_user_organization
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

    def test_group_deleting(self):
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


class TestUserProfileOrganization(TestCase):
    """
    Testing the user profile organization functions.
    """

    fixtures = ['groups', 'mockup_data']

    def setUp(self):
        """
        Set up the test conditions.
        """
        settings.DEBUG = False

    def test_get_first_user_organization(self):
        """
        Test the getting of the first user organization.
        """
        organization = get_first_user_organization(3, None)  # User is "student01", viewer is "admin"
        self.assertIsNotNone(organization)  # He has an organizations assigned
        self.assertEqual(organization.id, 1)  # "Organization 1" is the first one in his list

    def test_get_checked_user_organization_by_id(self):
        """
        Test the getting of the user organization by id.
        """
        organization = get_checked_user_organization_by_id(3, 1, None)  # "student01" and his organization (id=1)
        self.assertIsNotNone(organization)  # He has this organization assigned
        self.assertEqual(organization.id, 1)  # Got the "Organization 1" (id=1) as his organization.

        organization = get_checked_user_organization_by_id(3, 3, 1)  # "student01" and another's organization
        self.assertIsNone(organization)  # He has no this organization assigned

    def test_get_user_organizations_for_filter(self):
        """
        Test the getting of the first user organization.
        """
        organizations = get_user_organizations_for_filter(3, None)  # User is "student01", viewer is "admin"
        self.assertEqual(len(organizations), 1)  # He has one organization to show in the filter
        self.assertTrue('id' in organizations[0])
        self.assertTrue('name' in organizations[0])
        self.assertEqual(organizations[0]['id'], 1)
        self.assertEqual(organizations[0]['name'], 'Organization 1')

        organizations = get_user_organizations_for_filter(4, None)  # User is "student02_no_orgs", viewer is "admin"
        self.assertEqual(len(organizations), 0)  # He has no organizations to show in the filter

        organizations = get_user_organizations_for_filter(5, None)  # User is "student03", viewer is "admin"
        self.assertEqual(len(organizations), 2)  # He has two organizations to show in the filter
        self.assertEqual(organizations[0]['id'], 1)
        self.assertEqual(organizations[0]['name'], 'Organization 1')
        self.assertEqual(organizations[1]['id'], 2)
        self.assertEqual(organizations[1]['name'], 'Organization 2')

    def test_select_user_organization(self):
        """
        Test the organization selection by the user and organization id.
        """
        organization = select_user_organization(3, 1, None)  # 3 - student01, has 1 - "Organization 1"
        self.assertIsNotNone(organization)
        self.assertEqual(organization.id, 1)

        organization = select_user_organization(3, 3, None)  # 3 - student01, has no 3 - "Organization 3"
        self.assertIsNone(organization)

        organization = select_user_organization(4, 1, None)  # 4 - student02_no_orgs, has no organizations
        self.assertIsNone(organization)
