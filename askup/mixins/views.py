from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.decorators import method_decorator

from askup.models import Qset
from askup.utils.general import check_user_has_groups
from askup.utils.views import apply_filter_to_queryset, get_clean_filter_parameter, QSET_QUESTION_FILTERS


class CheckSelfForRedirectMixIn(object):
    """Provides a redirect, requested from within view object."""

    def dispatch(self, *args, **kwargs):
        """
        Check presence of required credentials and parameters.

        Overriding the dispatch method of generic.ListView
        """
        func_result = super().dispatch(*args, **kwargs)
        redirect = self.check_self_for_redirect()
        return redirect or func_result

    def check_self_for_redirect(self):
        """Check if object has a _redirect property and return it if found."""
        redirect = getattr(self, '_redirect', None)

        if redirect:
            return redirect
        else:
            return False


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
        redirect_to_do = self.check_model_accordance(pk)

        if redirect_to_do:
            return redirect_to_do

        applied_to_organization = self._current_qset.top_qset.users.filter(id=request.user.id)
        is_admin = check_user_has_groups(request.user, 'admin')

        if not is_admin and not applied_to_organization:
            return redirect(reverse('askup:organizations'))

        return super().dispatch(request, *args, **kwargs)

    def check_model_accordance(self, pk):
        """
        Check model accordance to a template.
        """
        is_organization = self._current_qset.parent_qset_id is None

        if is_organization and self.template_name != 'askup/organization.html':
            return redirect(reverse('askup:organization', kwargs={'pk': pk}))

        if not is_organization and self.model is not Qset:
            return redirect(reverse('askup:qset', kwargs={'pk': pk}))


class ListViewUserContextDataMixIn(object):
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
        context['filter'] = get_clean_filter_parameter(self.request)
        context['filter_label'] = QSET_QUESTION_FILTERS[context['filter']][0]
        context['qset_question_filters'] = QSET_QUESTION_FILTERS

        return None if context['filter'] == 'all' else context['filter']

    def process_user_filter(self, context, queryset):
        """Process user filter and return queryset with the correspondent changes."""
        filter = self.fill_user_filter_context(context)
        return apply_filter_to_queryset(self.request.user.id, filter, queryset)
