from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.decorators import method_decorator

from askup.models import Qset
from askup.utils import check_user_has_groups


class QsetViewMixin(object):
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

        if not request.user.is_superuser and not applied_to_organization:
            return redirect(reverse('askup:organizations'))

        return super().dispatch(request, *args, **kwargs)


class ListViewUserContextDataMixin(object):
    """ListView user data mixin."""

    def fill_user_context(self, context):
        """Fill user related context extra fields."""
        context['is_admin'] = self.request.user.is_superuser
        context['is_teacher'] = check_user_has_groups(self.request.user, 'teachers')
        context['is_student'] = check_user_has_groups(self.request.user, 'students')
        context['is_qset_creator'] = context['is_admin'] or context['is_teacher']
        context['is_question_creator'] = self.request.user.is_authenticated()
