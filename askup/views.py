"""Askup django views."""
import logging

from django.contrib.auth import authenticate, login, logout
from django.shortcuts import get_object_or_404, redirect, render
from django.views import generic

from .forms import QsetModelForm, UserLoginForm
from .models import Qset, Question


log = logging.getLogger(__name__)


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
        user = self.request.user

        if user.is_superuser:
            return Qset.objects.filter(parent_qset=None).order_by('name')
        if user.is_authenticated():
            return Qset.objects.filter(parent_qset=None, top_qset__users=user.id).order_by('name')
        else:
            return []


class OrganizationView(generic.ListView):
    """Handles root qsets of the Organization list view."""

    template_name = 'askup/organization.html'

    def get_context_data(self, **kwargs):
        """
        Get context data for the list view.

        Overriding the get_context_data of generic.ListView
        """
        context = super().get_context_data(**kwargs)
        current_org = get_object_or_404(Qset, pk=self.kwargs.get('pk'))
        context['main_title'] = current_org.name
        context['current_qset_name'] = current_org.name
        context['current_qset_id'] = current_org.id
        context['is_admin'] = self.request.user.is_superuser
        context['is_teacher'] = 'Teachers' in self.request.user.groups.values_list('name', flat=True)
        context['is_student'] = 'Students' in self.request.user.groups.values_list('name', flat=True)
        context['is_qset_creator'] = context['is_admin'] or context['is_teacher']
        context['is_qset_allowed'] = True
        return context

    def get_queryset(self):
        """
        Get queryset for the list view.

        Overriding the get_queryset of generic.ListView
        """
        pk = self.kwargs.get('pk')
        user = self.request.user
        log.debug("USER in view: %s", self.request)

        if user.is_superuser:
            log.debug('Filtered qsets for the superuser by pk=%s', pk)
            return Qset.objects.filter(parent_qset_id=pk).order_by('name')
        if user.is_authenticated():
            log.debug('Filtered qsets for the %s by pk=%s', user.username, pk)
            return Qset.objects.filter(parent_qset=pk, top_qset__users=user.id).order_by('name')
        else:
            return []


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
        context['current_qset'] = current_qset
        context['current_qset_name'] = current_qset.name
        context['current_qset_id'] = current_qset.id
        context['is_admin'] = self.request.user.is_superuser
        context['is_teacher'] = 'Teachers' in self.request.user.groups.values_list('name', flat=True)
        context['is_student'] = 'Students' in self.request.user.groups.values_list('name', flat=True)
        context['is_qset_creator'] = context['is_admin'] or context['is_teacher']
        context['is_qset_allowed'] = current_qset.type in (0, 1)
        context['is_question_creator'] = self.request.user.is_authenticated()
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


def login_view(request):
    """Provide the login view and functionality."""
    if request.user.is_authenticated():
        return redirect('/')

    form = UserLoginForm(request.POST or None)

    if form.is_valid():
        username = form.cleaned_data.get('username')
        password = form.cleaned_data.get('password')
        user = authenticate(username=username, password=password)
        login(request, user)

        if request.user.is_authenticated():
            return redirect('/')

    return render(request, 'askup/login_form.html', {'form': form})


def logout_view(request):
    """Provide the logout view and functionality."""
    logout(request)
    return redirect('/')


def create_qset(request):
    """Provide the create qset view for the student/teacher/admin."""
    if request.method == 'GET':
        form = QsetModelForm()
    else:
        form = QsetModelForm(request.POST or None)

        if form.is_valid():
            name = form.cleaned_data.get('name')
            type = form.cleaned_data.get('type')
            parent_qset = form.cleaned_data.get('parent_qset')
            qset = Qset.objects.create(name=name, parent_qset_id=parent_qset.id, type=type)
            return redirect('/askup/qset/{0}/'.format(qset.id))

    return render(request, 'askup/create_qset_form.html', {'form': form})


def create_question(request):
    """Provide the create question view for the student/teacher/admin."""
    pass


def index_view(request):
    """Provide the index view."""
    return render(request, 'askup/index.html')
