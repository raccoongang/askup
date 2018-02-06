import logging

from django.contrib import admin
from django.http import HttpResponseRedirect

from askup.models import Qset


log = logging.getLogger(__name__)


class CookieFilterMixIn(admin.ModelAdmin):
    """Provides a default filter functionality to the ModelAdmin inheritors."""

    def changelist_view(self, request, *args, **kwargs):
        """Apply default filters."""
        url = request.META['PATH_INFO']
        query = request.META.get('QUERY_STRING', '')
        self._request = request
        filters_query_string, cookies = self.get_filters_query_string()

        if filters_query_string != query:
            # If filters query are different after applying default and cookie filters onto GET ones.
            response = HttpResponseRedirect("{0}?{1}".format(url, filters_query_string))
        else:
            response = super().changelist_view(request, *args, **kwargs)

        for cookie_name, cookie_value in cookies.items():
            response.set_cookie('admin-filter-{0}'.format(cookie_name), cookie_value)

        return response

    def get_filters_query_string(self):
        """
        Return filters query string and cookies.

        Return filters query string and cookies composed of default, applied and cookie filters.
        """
        cookie_filters = {}
        result_filters = self.get_default_filters()
        cookie_filters = self.get_cookie_filters()
        applied_filters = self.get_applied_filters()
        result_filters.update(cookie_filters)
        result_filters.update(applied_filters)
        result_filters = self.check_org_qset_relation(result_filters, clean_field='qset')
        query_parameters = list(
            map(
                lambda key: '{0}={1}'.format(key, result_filters[key]),
                result_filters,
            )
        )
        query_string = '&'.join(query_parameters)
        return query_string, self.get_diff_applied_and_cookie(applied_filters, cookie_filters)

    def get_diff_applied_and_cookie(self, applied_filters, cookie_filters):
        """Compare applied and cookie filters and return changed cookie fields."""
        changed_fields = {}

        for key, applied_value in applied_filters.items():
            cookie_value = cookie_filters.get(key, '')

            if key in applied_filters and applied_value != cookie_value:
                changed_fields[key] = applied_value

        return changed_fields

    def get_default_filters(self):
        """Return default filters for the ModelAdmin."""
        filters = {}

        if getattr(self, 'default_filters', None) is None:
            self.default_filters = tuple()

        for key, value in self.default_filters.items():
            if key not in self._request.GET:
                filters[key] = value

        return filters

    def get_applied_filters(self):
        """Return all applied filters."""
        filters = {}

        for key, value in self._request.GET.items():
            filters[key] = value

        return filters

    def get_cookie_filters(self):
        """
        Return cookie filters for the ModelAdmin.

        Returns a dictionary where key is a cookie key and value is it's value
        when value is not empty.
        """
        filters = {}

        if getattr(self, 'cookie_filters', None) is None:
            self.default_filters = tuple()

        for key in self.cookie_filters:
            cookie_key = 'admin-filter-{0}'.format(key)
            value = self._request.COOKIES.get(cookie_key, None)

            if value:
                filters[key] = value

        return filters

    def check_org_qset_relation(self, filters, clean_field='qset'):
        """
        Check org->qset relation.

        Checks org->qset relation and if qset doesn't belong this organization -
        clears the qset field.
        """
        qset_id = filters.get('qset')
        org_id = filters.get('org')

        if org_id is None or qset_id is None:
            return filters

        qset_exists = Qset.objects.filter(id=qset_id, top_qset_id=org_id).exists()

        if not qset_exists:
            filters[clean_field] = '0'

        return filters


class ParseUrlToParameters(object):
    """Provides a response parsing functionality."""

    @staticmethod
    def parse_response_url_to_parameters(response):
        """Parse response url to parameter pair strings "name=value"."""
        url_parts = response.url.split('?')

        if len(url_parts) < 2:
            return

        query_string = url_parts[1] if len(url_parts) > 1 else ''
        parameters = query_string.split('&') if query_string else []
        return url_parts[0], parameters
