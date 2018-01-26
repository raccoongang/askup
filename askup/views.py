"""Askup django views."""
import logging

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import generic

from .forms import OrganizationModelForm, QsetDeleteModelForm, QsetModelForm, UserLoginForm
from .mixins import ListViewUserContextDataMixin, QsetViewMixin
from .models import Organization, Qset, Question
from .utils import user_group_required


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


class OrganizationView(ListViewUserContextDataMixin, QsetViewMixin, generic.ListView):
    """Handles root qsets of the Organization list view."""

    template_name = 'askup/organization.html'

    def get_context_data(self, **kwargs):
        """
        Get context data for the list view.

        Overriding the get_context_data of generic.ListView
        """
        context = super().get_context_data(**kwargs)
        context['main_title'] = self._current_qset.name
        context['current_qset_name'] = self._current_qset.name
        context['current_qset_id'] = self._current_qset.id
        self.fill_user_context(context)
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
        elif user.is_authenticated():
            log.debug('Filtered qsets for the %s by pk=%s', user.username, pk)
            return Qset.objects.filter(parent_qset_id=pk, top_qset__users=user.id).order_by('name')
        else:
            return []


class QsetView(ListViewUserContextDataMixin, QsetViewMixin, generic.ListView):
    """Handles the Qset list view (subsets only/questions only/mixed)."""

    model = Qset

    def get_template_names(self):
        """
        Get template names to use in the view.

        Overriding the get_template_names of generic.ListView
        """
        if self._current_qset.type == 1:
            return ['askup/qset_subsets_only.html']
        elif self._current_qset.type == 2:
            return ['askup/qset_questions_only.html']
        else:
            return ['askup/qset_mixed.html']

    def get_context_data(self, *args, **kwargs):
        """
        Get context data for the list view.

        Overriding the get_context_data of generic.ListView
        """
        context = super().get_context_data(*args, **kwargs)

        if self._current_qset.type == 1:
            # Clear the questions queryset if rendering the "qsets only" Qset
            context['questions_list'] = []
        else:
            context['questions_list'] = Question.objects.filter(qset_id=self.kwargs.get('pk'))

        self.fill_user_context(context)
        self.fill_qset_context(context)
        self.fill_checkboxes_context(context)
        return context

    def fill_qset_context(self, context):
        """Fill qset related context extra fields."""
        context['main_title'] = self._current_qset.name
        context['parent_qset_id'] = self._current_qset.parent_qset_id
        context['current_qset'] = self._current_qset
        context['current_qset_name'] = self._current_qset.name
        context['current_qset_id'] = self._current_qset.id
        context['current_qset_show_authors'] = self._current_qset.show_authors

    def fill_checkboxes_context(self, context):
        """Fill qset checkboxes states context."""
        qset = self._current_qset
        context['mixed_type'] = self.get_checkbox_state(qset.type == 0)
        context['subsets_type'] = self.get_checkbox_state(qset.type == 1)
        context['questions_type'] = self.get_checkbox_state(qset.type == 2)
        context['for_any_authenticated'] = self.get_checkbox_state(qset.for_any_authenticated)
        context['show_authors'] = self.get_checkbox_state(qset.show_authors)
        context['for_unauthenticated'] = self.get_checkbox_state(qset.for_unauthenticated)

    def get_checkbox_state(self, bool_expression):
        """Return a string of checked attribute if expression is True and empty string otherwise."""
        return ' checked="checked"' * bool_expression

    def get_queryset(self):
        """
        Get queryset for the list view.

        Overriding the get_queryset of generic.ListView
        """
        if self._current_qset.type == 2:
            # Clear the qsets queryset if rendering the "questions only" Qset
            queryset = []
        else:
            queryset = Qset.objects.filter(parent_qset_id=self.kwargs.get('pk'))

        return queryset


class QuestionView(generic.DetailView):
    """Handles the Question detailed view."""

    model = Question

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        """
        Check presence of required credentials and parameters.

        Overriding the dispatch method of generic.DetailView
        """
        return super().dispatch(*args, **kwargs)  # Uncomment on stub remove


class UserProfileView(generic.DetailView):
    """Handles the Question detailed view."""

    model = User
    template_name = 'askup/user_profile.html'

    @method_decorator(login_required)
    def dispatch(*args, **kwargs):
        """
        Check presence of required credentials and parameters.

        Overriding the dispatch method of generic.DetailView
        """
        # return super().dispatch(*args, **kwargs)  # Uncomment on stub remove
        # Stub
        return redirect(reverse('askup:organizations'))


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


@user_group_required('admins')
def organization_update(request, pk):
    """Provide the update qset view for the teacher/admin."""
    organization = get_object_or_404(Organization, pk=pk)

    if request.method == 'GET':
        form = OrganizationModelForm(instance=organization)
    else:
        form = OrganizationModelForm(request.POST or None, instance=organization)

        if form.is_valid():
            form.save()

    return redirect(reverse('askup:organization', kwargs={'pk': organization.id}))


@login_required
def qset_create(request):
    """Provide the create qset view for the student/teacher/admin."""
    if request.method == 'GET':
        form = QsetModelForm(user=request.user)
    else:
        form = QsetModelForm(request.POST or None, user=request.user)

        if form.is_valid():
            name = form.cleaned_data.get('name')
            type = form.cleaned_data.get('type')
            parent_qset = form.cleaned_data.get('parent_qset')
            qset = Qset.objects.create(
                name=name,
                parent_qset_id=parent_qset.id,
                top_qset_id=parent_qset.top_qset_id,
                type=type
            )
            return redirect(reverse('askup:qset', kwargs={'pk': qset.id}))

    return render(request, 'askup/create_qset_form.html', {'form': form})


@user_group_required('teachers', 'admins')
def qset_update(request, pk):
    """Provide the update qset view for the student/teacher/admin."""
    qset = get_object_or_404(Qset, pk=pk)

    if request.method == 'GET':
        form = QsetModelForm(user=request.user, instance=qset)
    else:
        form = QsetModelForm(request.POST or None, user=request.user, instance=qset)

        if form.is_valid():
            form.save()
            return redirect(reverse('askup:qset', kwargs={'pk': qset.id}))

    return render(request, 'askup/create_qset_form.html', {'form': form})


@user_group_required('teachers', 'admins')
def qset_delete(request, pk):
    """Provide the delete qset view for the teacher/admin."""
    qset = get_object_or_404(Qset, pk=pk)
    redirect_response = None

    if qset.parent_qset_id is None:
        return redirect(reverse('askup:qset', kwargs={'pk': qset.id}))

    if not request.user.is_superuser and request.user.id not in qset.top_qset.users.all():
        return redirect(reverse('askup:organizations'))

    if request.method == 'POST':
        redirect_response = do_qset_validate_delete(
            QsetDeleteModelForm(
                request.POST,
                instance=qset,
            ),
            qset
        )

    return redirect_response or render(
        request,
        'askup/delete_qset_form.html',
        {
            'form': QsetDeleteModelForm(instance=qset),
            'qset_name': qset.name,
        }
    )


def do_qset_validate_delete(form, qset):
    """Perform a form validation and delete qset."""
    if form.is_valid():  # checks the CSRF
        parent = qset.parent_qset
        qset.delete()
        redirect_url = 'askup:organization' if parent.parent_qset_id is None else 'askup:qset'
        return redirect(reverse(redirect_url, kwargs={'pk': parent.id}))

    return None


def question_answer(request, question_id=None):
    """Provide a create question view for the student/teacher/admin."""
    log.debug('Got the question answer request for the question_id: %s', question_id)
    # Stub
    return redirect(reverse('askup:question', kwargs={'pk': question_id}))

    if request.user.id is None:
        return redirect(reverse('askup:sign_in'))


@login_required
def question_create(request, qset_id=None):
    """Provide a create question view for the student/teacher/admin."""
    log.debug('Got the question creation request for the qset_id: %s', qset_id)
    # Stub
    return redirect(reverse('askup:qset', kwargs={'pk': qset_id}))


def question_edit(request):
    """Provide an edit question view for the student/teacher/admin."""
    # Stub
    return redirect(reverse('askup:organizations'))

    if request.user.id is None:
        return redirect(reverse('askup:sign_in'))


def question_delete(request):
    """Provide a delete question view for the student/teacher/admin."""
    # Stub
    return redirect(reverse('askup:organizations'))

    if request.user.id is None:
        return redirect(reverse('askup:sign_in'))


def index_view(request):
    """Provide the index view."""
    return render(request, 'askup/index.html')
