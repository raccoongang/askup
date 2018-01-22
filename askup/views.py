"""Askup django views."""
import logging

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import generic

from .forms import (
    AnswerModelForm,
    OrganizationModelForm,
    QsetDeleteModelForm,
    QsetModelForm,
    QuestionDeleteModelForm,
    QuestionModelForm,
    UserLoginForm,
)
from .models import Answer, Organization, Qset, Question
from .utils import redirect_unauthenticated, user_group_required


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

    @redirect_unauthenticated
    def dispatch(self, request, *args, **kwargs):
        """
        Check presence of required credentials and parameters.

        Overriding the dispatch method of generic.ListView
        """
        pk = self.kwargs.get('pk')

        if not pk:
            return redirect(reverse('askup:organizations'))

        self._current_org = get_object_or_404(Qset, pk=self.kwargs.get('pk'))
        applied_to_organization = self._current_org.top_qset.users.filter(id=request.user.id)

        if not request.user.is_superuser and not applied_to_organization:
            return redirect(reverse('askup:organizations'))

        return super().dispatch(request, *args, **kwargs)

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
        elif user.is_authenticated():
            log.debug('Filtered qsets for the %s by pk=%s', user.username, pk)
            return Qset.objects.filter(parent_qset_id=pk, top_qset__users=user.id).order_by('name')
        else:
            return []


class QsetView(generic.ListView):
    """Handles the Qset list view (subsets only/questions only/mixed)."""

    model = Qset

    @redirect_unauthenticated
    def dispatch(self, request, *args, **kwargs):
        """
        Check presence of required credentials and parameters.

        Overriding the dispatch method of generic.ListView
        """
        pk = self.kwargs.get('pk')

        if not pk:
            return redirect(reverse('askup:organizations'))

        self._current_qset = get_object_or_404(Qset, pk=self.kwargs.get('pk'))

        if self._current_qset.parent_qset_id is None:
            return redirect(reverse('askup:organization', kwargs={'pk': self._current_qset.id}))

        applied_to_organization = self._current_qset.top_qset.users.filter(id=request.user.id)

        if not request.user.is_superuser and not applied_to_organization:
            return redirect(reverse('askup:organizations'))

        return super().dispatch(request, *args, **kwargs)

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

        if self._current_qset.type == 2:
            # Clear the qsets queryset if rendering the "questions only" Qset
            context['object_list'] = []

        if self._current_qset.type == 1:
            # Clear the questions queryset if rendering the "qsets only" Qset
            context['questions_list'] = []
        else:
            context['questions_list'] = Question.objects.filter(qset_id=self.kwargs.get('pk'))

        checked = ' checked="checked"'
        context['parent_qset_id'] = self._current_qset.parent_qset_id
        context['main_title'] = self._current_qset.name
        context['current_qset'] = self._current_qset
        context['current_qset_name'] = self._current_qset.name
        context['current_qset_id'] = self._current_qset.id
        context['current_qset_show_authors'] = self._current_qset.show_authors
        context['is_admin'] = self.request.user.is_superuser
        context['is_teacher'] = 'Teachers' in self.request.user.groups.values_list('name', flat=True)
        context['is_student'] = 'Students' in self.request.user.groups.values_list('name', flat=True)
        context['is_qset_creator'] = context['is_admin'] or context['is_teacher']
        context['is_qset_allowed'] = self._current_qset.type in (0, 1)
        context['is_question_creator'] = self.request.user.is_authenticated()
        context['mixed_type'] = checked if self._current_qset.type == 0 else ''
        context['subsets_type'] = checked if self._current_qset.type == 1 else ''
        context['questions_type'] = checked if self._current_qset.type == 2 else ''
        context['for_any_authenticated'] = checked if self._current_qset.for_any_authenticated else ''
        context['show_authors'] = checked if self._current_qset.show_authors else ''
        context['for_unauthenticated'] = checked if self._current_qset.for_unauthenticated else ''
        context['breadcrumbs'] = self._current_qset.get_parents()
        return context

    def get_queryset(self):
        """
        Get queryset for the list view.

        Overriding the get_queryset of generic.ListView
        """
        queryset = Qset.objects.filter(parent_qset_id=self.kwargs.get('pk'))

        return queryset


class QuestionView(generic.DetailView):
    """Handles the Question detailed view."""

    model = Question

    @redirect_unauthenticated
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

    @redirect_unauthenticated
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


@redirect_unauthenticated
def qset_create(request):
    """Provide the create qset view for the student/teacher/admin."""
    parent_qset_id = request.POST.get('parent_qset')
    parent_qset = get_object_or_404(Qset, pk=parent_qset_id)

    if request.method == 'GET':
        form = QsetModelForm(user=request.user, parent_qset_id=parent_qset_id)
    else:
        form = QsetModelForm(request.POST or None, user=request.user, parent_qset_id=parent_qset_id)

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

    return render(
        request,
        'askup/qset_form.html',
        {
            'form': form,
            'main_title': 'Create qset:',
            'submit_label': 'Create',
            'breadcrumbs': parent_qset.get_parents()
        }
    )


@user_group_required('teachers', 'admins')
def qset_update(request, pk):
    """Provide the update qset view for the student/teacher/admin."""
    qset = get_object_or_404(Qset, pk=pk)

    if request.method == 'GET':
        form = QsetModelForm(user=request.user, instance=qset, parent_qset_id=qset.id)
    else:
        form = QsetModelForm(request.POST or None, user=request.user, instance=qset, parent_qset_id=qset.id)

        if form.is_valid():
            form.save()
            return redirect(reverse('askup:qset', kwargs={'pk': qset.id}))

    return render(
        request,
        'askup/qset_form.html',
        {
            'form': form,
            'main_title': 'Edit qset',
            'submit_label': 'Save',
            'breadcrumbs': qset.get_parents()
        }
    )


@user_group_required('teachers', 'admins')
def qset_delete(request, pk):
    """Provide the delete qset view for the teacher/admin."""
    qset = get_object_or_404(Qset, pk=pk)

    if qset.parent_qset_id is None:
        return redirect(reverse('askup:qset', kwargs={'pk': qset.id}))

    if not request.user.is_superuser and request.user not in qset.top_qset.users.all():
        return redirect(reverse('askup:organizations'))

    if request.method == 'POST':
        form = QsetDeleteModelForm(request.POST, instance=qset)

        if form.is_valid():  # checks the CSRF
            parent = qset.parent_qset
            qset.delete()
            redirect_url = 'askup:organization' if parent.parent_qset_id is None else 'askup:qset'
            return redirect(reverse(redirect_url, kwargs={'pk': parent.id}))
    else:
        form = QsetDeleteModelForm(instance=qset)

    return render(
        request,
        'askup/delete_qset_form.html',
        {
            'form': form,
            'qset_name': qset.name,
            'breadcrumbs': qset.get_parents(),
        }
    )


@redirect_unauthenticated
def question_answer(request, question_id=None):
    """Provide a create question view for the student/teacher/admin."""
    log.debug('Got the question answering request for the question_id: %s', question_id)
    question = get_object_or_404(Question, pk=question_id)
    is_quiz_all = request.GET.get('is_quiz_all', None)
    user = request.user
    answer = None

    if request.method == 'GET':
        form = AnswerModelForm(parent_qset_id=question.qset_id)

        return render(
            request,
            'askup/question_answer.html',
            {
                'form': form,
                'question_id': question.id,
                'question_text': question.text,
                'question_answer_text': question.answer_text,
                'is_quiz_all': is_quiz_all,
            }
        )
    else:
        form = AnswerModelForm(request.POST or None, parent_qset_id=question.qset_id)
        response = {'result': 'success'}

        if form.is_valid():
            text = form.cleaned_data.get('text')

            if not request.user.is_superuser and user not in question.qset.top_qset.users.all():
                log.info(
                    'User %s have tried to answer the question without the permissions.',
                    user.id
                )
                return redirect(reverse('askup:organizations'))

            answer = Answer.objects.create(
                text=text,
                question_id=question.id,
                user_id=user.id
            )
            response['answer_id'] = answer.id
        else:
            response['result'] = 'error'

        return JsonResponse(response)


@redirect_unauthenticated
def question_create(request, qset_id=None):
    """Provide a create question view for the student/teacher/admin."""
    log.debug('Got the question creation request for the qset_id: %s', qset_id)
    user = request.user
    parent_qset_id = qset_id

    if qset_id:
        qset = get_object_or_404(Qset, pk=qset_id)
    else:
        qset = None

    if request.method == 'GET':
        form = QuestionModelForm(
            initial={'qset': qset_id},
            user=user,
            parent_qset_id=parent_qset_id,
        )
    else:
        form = QuestionModelForm(
            request.POST or None,
            user=user,
            parent_qset_id=parent_qset_id,
        )

        if form.is_valid():
            text = form.cleaned_data.get('text')
            answer_text = form.cleaned_data.get('answer_text')
            blooms_tag = form.cleaned_data.get('blooms_tag')
            qset = get_object_or_404(Qset, pk=form.cleaned_data.get('qset').id)

            if not user.is_superuser and user not in qset.top_qset.users.all():
                return redirect(reverse('askup:organizations'))

            Question.objects.create(
                text=text,
                answer_text=answer_text,
                qset_id=qset.id,
                user_id=user.id,
                blooms_tag=blooms_tag,
            )
            return redirect(reverse('askup:qset', kwargs={'pk': qset.id}))

    return render(
        request,
        'askup/question_form.html',
        {
            'form': form,
            'main_title': 'Create question:',
            'submit_label': 'Create',
            'breadcrumbs': qset.get_parents(False) if qset else None,
        }
    )


@redirect_unauthenticated
def question_edit(request, pk):
    """Provide an edit question view for the student/teacher/admin."""
    question = get_object_or_404(Question, pk=pk)
    user = request.user
    is_teacher = 'Teachers' in user.groups.values_list('name', flat=True)
    is_admin = user.is_superuser

    if not is_admin and user not in question.qset.top_qset.users.all():
        return redirect(reverse('askup:organizations'))

    if not is_admin and not is_teacher and user.id != question.user_id:
        return redirect(reverse('askup:organizations'))

    if request.method == 'GET':
        form = QuestionModelForm(
            user=request.user,
            instance=question,
            parent_qset_id=question.qset_id,
        )
    else:
        form = QuestionModelForm(
            request.POST or None,
            user=request.user,
            instance=question,
            parent_qset_id=question.qset_id,
        )

        if form.is_valid():
            form.save()

    return render(
        request,
        'askup/question_form.html',
        {
            'form': form,
            'main_title': 'Edit question:',
            'submit_label': 'Save',
            'current_qset': question.qset,
        }
    )


@redirect_unauthenticated
def question_delete(request, pk):
    """Provide a delete question view for the student/teacher/admin."""
    question = get_object_or_404(Question, pk=pk)
    user = request.user
    is_teacher = 'Teachers' in user.groups.values_list('name', flat=True)
    is_admin = user.is_superuser

    if not is_admin and user not in question.qset.top_qset.users.all():
        return redirect(reverse('askup:organizations'))

    if not is_admin and not is_teacher and user.id != question.user_id:
        return redirect(reverse('askup:organizations'))

    if request.method == 'POST':
        form = QuestionDeleteModelForm(
            request.POST,
            instance=question,
            parent_qset_id=question.qset_id
        )

        if form.is_valid():  # checks the CSRF
            qset_id = question.qset_id
            question.delete()
            return redirect(reverse('askup:qset', kwargs={'pk': qset_id}))
    else:
        form = QuestionDeleteModelForm(
            instance=question,
            parent_qset_id=question.qset_id
        )

    return render(
        request,
        'askup/delete_question_form.html',
        {
            'form': form,
            'question_name': question.text,
        }
    )


@redirect_unauthenticated
def answer_evaluate(request, answer_id, evaluation):
    """Provide a self-evaluation for the student/teacher/admin."""
    log.debug(
        'Got the "%s" evaluation for the answer_id - %s',
        evaluation,
        answer_id
    )
    is_quiz_all = request.GET.get('is_quiz_all', None)
    user = request.user
    answer = get_object_or_404(Answer, pk=answer_id)
    evaluation_int = int(evaluation)

    if not user.is_superuser and user not in answer.question.qset.top_qset.users.all():
        return redirect(reverse('askup:organizations'))

    if evaluation_int in tuple(zip(*Answer.EVALUATIONS))[0]:
        answer.self_evaluation = evaluation_int
        answer.save()

    if is_quiz_all:
        qset_id = answer.question.qset_id
        question_text = answer.question.text
        next_question = Question.objects.filter(qset_id=qset_id, text__gt=question_text).order_by('text').first()

        if next_question:
            return redirect(
                '{0}?is_quiz_all=1'.format(
                    reverse('askup:question_answer', kwargs={'question_id': next_question.id})
                )
            )

    return redirect(reverse('askup:qset', kwargs={'pk': answer.question.qset_id}))


def index_view(request):
    """Provide the index view."""
    return render(request, 'askup/index.html')


@redirect_unauthenticated
def start_quiz_all(request, qset_id):
    """Provide a start quiz all in qset view for the student/teacher/admin."""
    log.debug('Got the quiz all request for the qset_id: %s', qset_id)
    qset = get_object_or_404(Qset, pk=qset_id)
    question = Question.objects.filter(qset_id=qset_id).order_by('text').first()
    user = request.user

    if not user.is_superuser and not user not in qset.top_qset.users.all():
        return redirect(reverse('askup:organizations'))

    if not question:
        raise Http404

    if request.method == 'GET':
        return redirect(
            '{0}?is_quiz_all=1'.format(
                reverse('askup:question_answer', kwargs={'question_id': question.id})
            )
        )
    else:
        return redirect(reverse('askup:organizations'))
