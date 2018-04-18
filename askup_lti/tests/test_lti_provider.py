import logging

from django.test import TestCase
from django.test.client import Client
from django.urls.base import reverse
import mock

from askup_lti.models import LtiProvider, LtiUser

log = logging.getLogger(__name__)


def mock_tool_provider():
    """
    Mock tool provider object.
    """
    m = mock.Mock()
    m.is_valid_request.return_value = True
    return m


class LTIlaunchTest(TestCase):
    """
    Test LTI launch view with the correct and incorrect parameters.
    """

    fixtures = ['groups', 'mockup_data']

    def setUp(self):
        """
        Set required parameters for the tests in the class LTIlaunchTest.
        """
        self.client = Client()
        self.url = reverse('lti:launch')
        self.provider = LtiProvider.objects.create(consumer_name='test_provider')

    @mock.patch('askup_lti.provider.DjangoToolProvider.from_django_request', return_value=mock_tool_provider())
    def test_qset_is_not_added_to_launch_url(self, mock_ltiprovider):
        """
        Check lti launch if qset_id is not set to the launch URL.
        """
        response = self.client.post(self.url, {'oauth_consumer_key': self.provider.consumer_key})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'askup_lti/announcement.html')

    @mock.patch('askup_lti.provider.DjangoToolProvider.from_django_request', return_value=mock_tool_provider())
    def test_incorrect_qset_is_used_in_launch_url(self, mock_ltiprovider):
        """
        Check lti launch if incorrect qset_id is used in the launch URL.
        """
        url = self.url + '/qset/12'
        response = self.client.post(url, {'oauth_consumer_key': self.provider.consumer_key})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'askup_lti/announcement.html')

    @mock.patch('askup_lti.provider.DjangoToolProvider.from_django_request', return_value=mock_tool_provider())
    def test_correct_qset_is_used_in_launch_url(self, mock_ltiprovider):
        """
        Check lti launch if correct qset_id is used in the launch URL.
        """
        qset_id = 4
        url = '{base_url}/qset/{qset_id}'.format(base_url=self.url, qset_id=qset_id)
        response = self.client.post(url, {'oauth_consumer_key': self.provider.consumer_key, 'user_id': 'test_lti_user'})
        self.assertRedirects(response, reverse('askup:qset', args=[qset_id]))
        self.assertTemplateUsed(response, 'askup_lti/announcement.html')

        # Check LTIUser was created
        lti_user = LtiUser.objects.first()
        self.assertEqual(lti_user.user_id, 'test_lti_user')
