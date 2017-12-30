"""Askup django views."""
from django.shortcuts import get_object_or_404
from django.views import generic

from .models import Qset, Question


class OrganizationsView(generic.ListView):
    """Handles the User Organizations list view."""

    template_name = 'askup/organizations.html'

    def get_context_data(self, **kwargs):
        """
        Get context data for the list view.

        Overriding the get_context_data of generic.ListView
        """
        context = super().get_context_data(**kwargs)
        context['main_title'] = 'Your organizations'
        return context

    def get_queryset(self):
        """
        Get queryset for the Organizations list view.

        Overriding the get_queryset of generic.ListView
        """
        return Qset.objects.filter(parent_qset=None).order_by('name')


class OrganizationView(generic.ListView):
    """Handles root qsets of the Organization list view."""

    template_name = 'askup/organization.html'

    def get_context_data(self, **kwargs):
        """
        Get context data for the list view.

        Overriding the get_context_data of generic.ListView
        """
        context = super().get_context_data(**kwargs)

        try:
            main_title = Qset.objects.get(id=self.kwargs.get('pk')).name
        except Exception:
            main_title = 'N/A'

        context['main_title'] = main_title
        context['is_admin'] = self.request.user.is_superuser
        context['is_teacher'] = self.request.user.is_superuser
        return context

    def get_queryset(self):
        """
        Get queryset for the list view.

        Overriding the get_queryset of generic.ListView
        """
        return Qset.objects.filter(parent_qset_id=self.kwargs.get('pk')).order_by('name')


class QsetView(generic.ListView):
    """Handles the Qset list view (subsets only/questions only/mixed)."""

    model = Qset

    def get_template_names(self):
        """
        Get template names to use in the view.

        Overriding the get_template_names of generic.ListView
        """
        if self._current_qset_type == 1:
            return ['askup/qset_subsets_only.html']
        elif self._current_qset_type == 2:
            return ['askup/qset_questions_only.html']
        else:
            return ['askup/qset_mixed.html']

    def get_context_data(self, **kwargs):
        """
        Get context data for the list view.

        Overriding the get_context_data of generic.ListView
        """

        current_qset = get_object_or_404(Qset, pk=self.kwargs.get('pk'))
        self._current_qset_type = current_qset.type
        context = super().get_context_data(**kwargs)

        if self._current_qset_type == 2:
            # Clear the qsets queryset if rendering the "questions only" Qset
            context['object_list'] = []

        if self._current_qset_type == 1:
            # Clear the questions queryset if rendering the "qsets only" Qset
            context['questions_list'] = []
        else:
            context['questions_list'] = Question.objects.filter(qset_id=self.kwargs.get('pk'))

        context['main_title'] = current_qset.name
        context['is_qset_creator'] = self.request.user
        return context

    def get_queryset(self):
        """
        Get queryset for the list view.

        Overriding the get_queryset of generic.ListView
        """
        queryset = Qset.objects.filter(parent_qset_id=self.kwargs.get('pk'))
        parent_qset = get_object_or_404(Qset, pk=self.kwargs.get('pk'))

        if parent_qset:
            self._parent_qset = parent_qset

        return queryset


class QuestionView(generic.DetailView):
    """Handles the Question detailed view."""

    model = Question
    template_name = 'askup/question.html'
