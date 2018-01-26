"""Askup django views."""
import logging

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.decorators import method_decorator
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
from .mixins.views import ListViewUserContextDataMixin, QsetViewMixin
from .models import Answer, Organization, Qset, Question
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
            context['questions_list'] = Question.objects.filter(
                qset_id=self.kwargs.get('pk')
            ).order_by('-vote_value', 'text')

        self.fill_user_context(context)
        self.fill_qset_context(context)
        self.fill_checkboxes_context(context)
        context['breadcrumbs'] = self._current_qset.get_parents()
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
    parent_qset_id = request.POST.get('parent_qset')
    parent_qset = get_object_or_404(Qset, pk=parent_qset_id)
    form = do_make_qset_form(request, parent_qset_id)

    if request.method == 'POST':
        if form.is_valid():
            name = form.cleaned_data.get('name')
            parent_qset = form.cleaned_data.get('parent_qset')
            qset = Qset.objects.create(
                name=name,
                parent_qset_id=parent_qset.id,
                top_qset_id=parent_qset.top_qset_id,
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


def do_make_qset_form(request, parent_qset_id):
    """Compose qset form and return it."""
    if request.method == 'POST':
        return QsetModelForm(
            request.POST or None,
            user=request.user,
            qset_id=parent_qset_id
        )
    else:
        return QsetModelForm(
            user=request.user,
            qset_id=parent_qset_id
        )


@user_group_required('teachers', 'admins')
def qset_update(request, pk):
    """Provide the update qset view for the student/teacher/admin."""
    qset = get_object_or_404(Qset, pk=pk)

    if request.method == 'GET':
        form = QsetModelForm(user=request.user, instance=qset, qset_id=qset.id)
    else:
        form = QsetModelForm(request.POST or None, user=request.user, instance=qset, qset_id=qset.id)

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
    redirect_response = None

    if qset.parent_qset_id is None:
        return redirect(reverse('askup:qset', kwargs={'pk': qset.id}))

    if not request.user.is_superuser and request.user not in qset.top_qset.users.all():
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
            'breadcrumbs': qset.get_parents(),
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


@login_required
def question_answer(request, question_id=None):
    """Provide a create question view for the student/teacher/admin."""
    log.debug('Got the question answering request for the question_id: %s', question_id)
    question = get_object_or_404(Question, pk=question_id)
    is_quiz_all = request.GET.get('is_quiz_all', None)
    form = do_make_answer_form(request, question)

    if request.method == 'GET':
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
        response = do_validate_answer_form(form, request, question)
        return JsonResponse(response)


def do_make_answer_form(request, question):
    """Compose and return answer form."""
    if request.method == 'POST':
        return AnswerModelForm(request.POST or None, parent_qset_id=question.qset_id)
    else:
        return AnswerModelForm(parent_qset_id=question.qset_id)


def do_validate_answer_form(form, request, question):
    """
    Validate answer form and create an Answer object on success.

    Returns response dictionary to pass to the JsonResponse after.
    """
    response = {'result': 'success'}
    user = request.user

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

    return response


@login_required
def question_create(request, qset_id=None):
    """Provide a create question view for the student/teacher/admin."""
    log.debug('Got the question creation request for the qset_id: %s', qset_id)

    if qset_id:
        qset = get_object_or_404(Qset, pk=qset_id)
    else:
        qset = None

    form, redirect_response = do_make_form_and_create(request, qset_id)

    if redirect_response:
        return redirect_response

    return render(
        request,
        'askup/question_form.html',
        {
            'form': form,
            'main_title': 'Create question:',
            'submit_label': 'Create',
            'breadcrumbs': qset and qset.get_parents(True),
        }
    )


def do_make_form_and_create(request, qset_id):
    """Compose form and create question on validation success."""
    user = request.user

    if request.method == 'POST':
        form = do_compose_question_create_form(request, user, qset_id)

        if form.is_valid():
            qset = get_object_or_404(Qset, pk=form.cleaned_data.get('qset').id)
            text = form.cleaned_data.get('text')
            answer_text = form.cleaned_data.get('answer_text')
            blooms_tag = form.cleaned_data.get('blooms_tag')

            return do_check_user_and_create_question(user, qset, text, answer_text, blooms_tag)
    else:
        form = do_compose_question_create_form(request, user, qset_id)

    return form, None


def do_compose_question_create_form(request, user, qset_id):
    """Compose create question form."""
    if request.method == 'POST':
        return QuestionModelForm(
            request.POST,
            user=user,
            qset_id=qset_id,
        )
    else:
        return QuestionModelForm(
            initial={'qset': qset_id},
            user=user,
            qset_id=qset_id,
        )


def do_check_user_and_create_question(user, qset, text, answer_text, blooms_tag):
    """Check user permissions and create question in the database."""
    if not user.is_superuser and user not in qset.top_qset.users.all():
        return None, redirect(reverse('askup:organizations'))

    Question.objects.create(
        text=text,
        answer_text=answer_text,
        qset_id=qset.id,
        user_id=user.id,
        blooms_tag=blooms_tag,
    )
    return None, redirect(reverse('askup:qset', kwargs={'pk': qset.id}))


@login_required
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

    form = do_compose_question_form_and_update(request, question)

    return render(
        request,
        'askup/question_form.html',
        {
            'form': form,
            'main_title': 'Edit question:',
            'submit_label': 'Save',
            'current_qset': question.qset,
            'breadcrumbs': question.qset.get_parents(True),
        }
    )


def do_compose_question_form_and_update(request, question):
    """Compose Question form and update question on validation success."""
    if request.method == 'POST':
        form = QuestionModelForm(
            request.POST,
            user=request.user,
            instance=question,
            qset_id=question.qset_id,
        )

        if form.is_valid():
            form.save()
    else:
        form = QuestionModelForm(
            user=request.user,
            instance=question,
            qset_id=question.qset_id,
        )

    return form


@login_required
def question_delete(request, pk):
    """Provide a delete question view for the student/teacher/admin."""
    question = get_object_or_404(Question, pk=pk)
    qset_id = question.qset_id
    user = request.user
    is_teacher = 'Teachers' in user.groups.values_list('name', flat=True)
    is_admin = user.is_superuser

    if not is_admin and user not in question.qset.top_qset.users.all():
        return redirect(reverse('askup:organizations'))

    if not is_admin and not is_teacher and user.id != question.user_id:
        return redirect(reverse('askup:organizations'))

    form = do_make_form_and_delete(request, question)

    if form is None:
        return redirect(reverse('askup:qset', kwargs={'pk': qset_id}))

    return render(
        request,
        'askup/delete_question_form.html',
        {
            'form': form,
            'question_name': question.text,
        }
    )


def do_make_form_and_delete(request, question):
    """Make form and delete question on validation success."""
    if request.method == 'POST':
        form = QuestionDeleteModelForm(
            request.POST,
            instance=question,
            parent_qset_id=question.qset_id,
        )
    else:
        form = QuestionDeleteModelForm(
            instance=question,
            parent_qset_id=question.qset_id,
        )

    if form.is_valid():  # checks the CSRF
        question.delete()
        return None

    return form


@login_required
def answer_evaluate(request, answer_id, evaluation):
    """Provide a self-evaluation for the student/teacher/admin."""
    log.debug(
        'Got the "%s" evaluation for the answer_id - %s',
        evaluation,
        answer_id
    )
    is_quiz_all = request.GET.get('is_quiz_all', None)
    answer = get_object_or_404(Answer, pk=answer_id)

    if not do_user_checks_and_evaluate(request.user, answer, evaluation):
        return redirect(reverse('askup:organizations'))

    if is_quiz_all:
        qset_id = answer.question.qset_id
        next_question = Question.objects.filter(
            qset_id=qset_id,
            text__gt=answer.question.text
        ).order_by('text').first()

        if next_question:
            return redirect(
                '{0}?is_quiz_all=1'.format(
                    reverse('askup:question_answer', kwargs={'question_id': next_question.id})
                )
            )

    return redirect(reverse('askup:qset', kwargs={'pk': answer.question.qset_id}))


def do_user_checks_and_evaluate(user, answer, evaluation):
    """Do user checks and evaluate answer for the answer evaluation view."""
    evaluation_int = int(evaluation)

    if not user.is_superuser and user not in answer.question.qset.top_qset.users.all():
        return False

    if evaluation_int in tuple(zip(*Answer.EVALUATIONS))[0]:
        answer.self_evaluation = evaluation_int
        answer.save()

    return True


def index_view(request):
    """Provide the index view."""
    return render(request, 'askup/index.html')


@login_required
def start_quiz_all(request, qset_id):
    """Provide a start quiz all in qset view for the student/teacher/admin."""
    log.debug('Got the quiz all request for the qset_id: %s', qset_id)
    qset = get_object_or_404(Qset, pk=qset_id)
    question = Question.objects.filter(qset_id=qset_id).order_by('text').first()
    user = request.user

    if not user.is_superuser and user not in qset.top_qset.users.all():
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


@login_required
def question_upvote(request, question_id):
    """Provide a question up-vote functionality."""
    return question_vote(request.user, question_id, 1)


@login_required
def question_downvote(request, question_id):
    """Provide a question down-vote functionality."""
    return question_vote(request.user, question_id, -1)


def question_vote(user, question_id, value):
    """Provide a general question vote functionality."""
    question = get_object_or_404(Question, pk=question_id)

    if not user.is_superuser and user not in question.qset.top_qset.users.all():
        return redirect(reverse('askup:organizations'))

    vote_result = question.vote(user.id, value)

    if vote_result is False:
        response = {'result': 'error'}
    else:
        response = {'result': 'success', 'value': vote_result}

    return JsonResponse(response)
