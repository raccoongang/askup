from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.decorators import method_decorator

from askup.models import Qset
from askup.utils.general import check_user_has_groups
from askup.utils.views import check_self_for_redirect_decorator


class CheckSelfForRedirectMixIn(object):
    """Provides a redirect, requested from within view object."""

    @check_self_for_redirect_decorator
    def dispatch(self, *args, **kwargs):
        """
        Check presence of required credentials and parameters.

        Overriding the dispatch method of generic.ListView
        """
        return super().dispatch(*args, **kwargs)


class QsetViewMixIn(object):
    """Qset/Organization view dispatch mixin."""

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        """
        Check presence of required credentials and parameters.

        Overriding the dispatch method of generic.ListView
        """
        pk = self.kwargs.get('pk')

        if not pk:
            return redirect(reverse('askup:organizations'))

        self._current_qset = get_object_or_404(Qset, pk=self.kwargs.get('pk'))
        applied_to_organization = self._current_qset.top_qset.users.filter(id=request.user.id)
        is_admin = check_user_has_groups(request.user, 'admin')

        if not is_admin and not applied_to_organization:
            return redirect(reverse('askup:organizations'))

        return super().dispatch(request, *args, **kwargs)


class UserFilterMixIn(object):
    """Provides the user filter related functionality."""

    @staticmethod
    def get_clean_filter_parameter(request):
        """Return a clean user filter value."""
        allowed_filters = ('all', 'mine', 'other')
        get_parameter = request.GET.get('filter')
        return 'all' if get_parameter not in allowed_filters else get_parameter

    @staticmethod
    def apply_filter_to_queryset(request, filter, queryset):
        """Return a queryset with user filter applied."""
        if filter == 'mine':
            return queryset.filter(user_id=request.user.id)

        if filter == 'other':
            return queryset.exclude(user_id=request.user.id)

        return queryset


class ListViewUserContextDataMixIn(UserFilterMixIn, object):
    """ListView user data mixin."""

    def fill_user_context(self, context):
        """Fill user related context extra fields."""
        user = self.request.user
        context['is_admin'] = check_user_has_groups(user, 'admin')
        context['is_teacher'] = check_user_has_groups(user, 'teacher')
        context['is_student'] = check_user_has_groups(user, 'student')
        context['is_qset_creator'] = context['is_admin'] or context['is_teacher']
        context['is_question_creator'] = user.is_authenticated()

    def fill_user_filter_context(self, context):
        """Fill a filter related context data."""
        context['filter'] = self.get_clean_filter_parameter(self.request)
        context['filter_all_active'] = 'active'
        context['filter_mine_active'] = ''
        context['filter_other_active'] = ''

        if context['filter'] == 'all':
            return

        context['filter_all_active'] = ''
        context['filter_mine_active'] = 'active' * (context['filter'] == 'mine')
        context['filter_other_active'] = 'active' * (context['filter'] == 'other')
        return context['filter']

    def process_user_filter(self, context, queryset):
        """Process user filter and return queryset with the correspondent changes."""
        filter = self.fill_user_filter_context(context)
        return self.apply_filter_to_queryset(self.request, filter, queryset)
