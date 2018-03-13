"""Askup django views."""
import logging

from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group, User
from django.contrib.sites.shortcuts import get_current_site
from django.core.cache import cache
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.views import generic

from .forms import (
    AnswerModelForm,
    OrganizationModelForm,
    QsetDeleteModelForm,
    QsetModelForm,
    QuestionDeleteModelForm,
    QuestionModelForm,
    SignUpForm,
    UserLoginForm,
)
from .mixins.views import (
    CheckSelfForRedirectMixIn,
    ListViewUserContextDataMixIn,
    QsetViewMixIn,
)
from .models import Answer, Organization, Qset, Question
from .tokens import account_activation_token
from .utils.general import (
    add_notification_to_url,
    check_user_has_groups,
    compose_user_full_name_from_object,
    get_real_questions_queryset,
    get_student_last_week_correct_answers_count,
    get_student_last_week_incorrect_answers_count,
    get_student_last_week_questions_count,
    get_student_last_week_votes_value,
    get_user_correct_answers_count,
    get_user_incorrect_answers_count,
    get_user_organizations_string,
    get_user_place_in_rank_list,
    get_user_profile_rank_list_and_total_users,
    get_user_score_by_id,
    get_user_subjects,
)
from .utils.views import (
    apply_filter_to_queryset,
    compose_qset_form,
    compose_question_form_and_create,
    delete_qset_by_form,
    get_clean_filter_parameter,
    qset_update_form_template,
    question_vote,
    user_group_required,
    validate_and_send_feedback_form,
    validate_answer_form_and_create,
)


log = logging.getLogger(__name__)


class OrganizationsView(CheckSelfForRedirectMixIn, generic.ListView):
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

        if check_user_has_groups(user, 'admin'):
            queryset = Qset.objects.filter(parent_qset=None)
        elif user.is_authenticated():
            queryset = Qset.objects.filter(parent_qset=None, top_qset__users=user.id)
        else:
            self._redirect = redirect(
                '{0}?next={1}'.format(
                    reverse('askup:sign_in'),
                    reverse('askup:organizations')
                )
            )
            return []

        if queryset.count() == 1:
            self._redirect = redirect(
                reverse(
                    'askup:organization',
                    kwargs={'pk': queryset.first().id}
                )
            )
            return []

        queryset = queryset.order_by('name')
        return queryset


class OrganizationView(
    CheckSelfForRedirectMixIn,
    ListViewUserContextDataMixIn,
    QsetViewMixIn,
    generic.ListView
):
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

        if check_user_has_groups(user, 'admin'):
            log.debug('Filtered qsets for the superuser by pk=%s', pk)
            return Qset.objects.filter(parent_qset_id=pk).order_by('name')
        elif user.is_authenticated():
            log.debug('Filtered qsets for the %s by pk=%s', user.username, pk)
            return Qset.objects.filter(parent_qset_id=pk, top_qset__users=user.id).order_by('name')
        else:
            return []


class QsetView(ListViewUserContextDataMixIn, QsetViewMixIn, generic.ListView):
    """Handles the Qset list view (subjects only/questions only/mixed)."""

    model = Qset

    def get_template_names(self):
        """
        Get template names to use in the view.

        Overriding the get_template_names of generic.ListView
        """
        if self._current_qset.type == 1:
            return ['askup/qset_subjects_only.html']
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
        context['questions_list'] = self.get_questions_queryset(context)
        self.fill_user_context(context)
        self.fill_qset_context(context)
        self.fill_checkboxes_context(context)
        context['breadcrumbs'] = self._current_qset.get_parents()
        return context

    def get_questions_queryset(self, context):
        """Get questions queryset corresponding to the filter and qset type."""
        if self._current_qset.type == 1:
            # Empty questions queryset if rendering the "qsets only" Qset
            queryset = []
        else:
            queryset = get_real_questions_queryset(self.kwargs.get('pk'))

        queryset = self.process_user_filter(context, queryset)
        return queryset

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


@login_required
def user_profile_view(request, user_id):
    """Provide the user profile my questions view."""
    profile_user = get_object_or_404(User, pk=user_id)
    user_id = int(user_id)
    return render(
        request,
        'askup/user_profile.html',
        {
            'profile_user': profile_user,
            'full_name': compose_user_full_name_from_object(profile_user),
            'viewer_user_id': request.user.id,
            'own_score': get_user_score_by_id(user_id),
            'is_owner': user_id == request.user.id,
            'is_student': check_user_has_groups(profile_user, 'student'),
            'own_correct_answers': get_user_correct_answers_count(user_id),
            'own_incorrect_answers': get_user_incorrect_answers_count(user_id),
            'user_rank_place': get_user_place_in_rank_list(user_id),
            'own_last_week_questions': get_student_last_week_questions_count(user_id),
            'own_last_week_thumbs_up': get_student_last_week_votes_value(user_id),
            'own_last_week_correct_answers': get_student_last_week_correct_answers_count(user_id),
            'own_last_week_incorrect_answers': get_student_last_week_incorrect_answers_count(user_id),
            'user_organizations': get_user_organizations_string(profile_user),
            'rank_list': tuple(),
            'rank_list_total_users': 0,
            'own_subjects': get_user_subjects(user_id),
        },
    )


@login_required
def user_profile_rank_list_view(request, user_id):
    """Provide the user profile rank list view."""
    profile_user = get_object_or_404(User, pk=user_id)
    rank_list, total_users = get_user_profile_rank_list_and_total_users(profile_user.id, request.user.id)
    user_id = int(user_id)
    return render(
        request,
        'askup/user_profile.html',
        {
            'profile_user': profile_user,
            'full_name': compose_user_full_name_from_object(profile_user),
            'viewer_user_id': request.user.id,
            'own_score': get_user_score_by_id(user_id),
            'is_owner': user_id == request.user.id,
            'is_student': check_user_has_groups(profile_user, 'student'),
            'own_correct_answers': get_user_correct_answers_count(user_id),
            'own_incorrect_answers': get_user_incorrect_answers_count(user_id),
            'user_rank_place': get_user_place_in_rank_list(user_id),
            'own_last_week_questions': get_student_last_week_questions_count(user_id),
            'own_last_week_thumbs_up': get_student_last_week_votes_value(user_id),
            'own_last_week_correct_answers': get_student_last_week_correct_answers_count(user_id),
            'own_last_week_incorrect_answers': get_student_last_week_incorrect_answers_count(user_id),
            'user_organizations': get_user_organizations_string(profile_user),
            'rank_list': rank_list,
            'rank_list_total_users': total_users,
            'own_subjects': tuple(),
        },
    )


def sign_up_view(request):
    """
    Provide a sign up view.
    """
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        redirect = validate_sign_up_form_and_create_user(form, request)

        if redirect:
            return redirect
    else:
        form = SignUpForm

    return render(request, 'askup/sign_up_form.html', {'form': form})


def validate_sign_up_form_and_create_user(form, request):
    """
    Validate the Sign Up form and create a user on success.

    Creates a user and emails the activation url to him/her on success.
    """
    if form.is_valid():
        user = form.save(commit=False)
        user.is_active = False
        user.save()
        send_user_an_activation_email(user, request)
        user.groups = [Group.objects.get(name='Student')]
        add_organization_to_user(
            form.cleaned_data['organization'],
            user,
        )

        return redirect('askup:sign_up_activation_sent')


def add_organization_to_user(organization, user):
    """
    Add a non-empty organization to the user.
    """
    if organization:
        user.qset_set.add(organization)


def send_user_an_activation_email(user, request):
    """
    Compose and send an activation email to the specified user.
    """
    current_site = get_current_site(request)
    subject = 'Activate Your AskUp Account'
    message = render_to_string(
        'askup/account_activation_email.html',
        {
            'user': user,
            'domain': current_site.domain,
            'uid': user.id,
            'token': account_activation_token.make_token(user),
        }
    )
    user.email_user(subject, message)


def sign_up_activation_sent(request):
    """
    Show the "Sign Up activation sent" message.
    """
    return render(request, 'askup/sign_up_activation_sent.html')


def sign_up_activate(request, uid, token):
    """
    Activate the user by the link from the registration email.
    """
    try:
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and account_activation_token.check_token(user, token):
        user.is_active = True
        user.profile.email_confirmed = True
        user.save()
        login(request, user)
        organizations = user.qset_set.all().order_by('name')
        organization_text = ''

        if organizations.count():
            organization_text = ' and applied to the organizations: <b>{}</b>'.format(
                '</b>, <b>'.join(tuple(str(org) for org in organizations))
            )

        notification = (
            'success',
            'You\'ve successfuly registered{0}'.format(organization_text)
        )

        return redirect(add_notification_to_url(notification, '/'))

    return(render(request, 'askup/sign_up_activation_invalid.html'))


def login_view(request):
    """Provide the login view and functionality."""
    if request.user.is_authenticated():
        return redirect('/')

    form = UserLoginForm(request.POST or None, request=request)
    next_page = request.GET.get('next', '/')

    if form.is_valid():
        if request.user.is_authenticated():
            return redirect(
                add_notification_to_url(
                    ('success', 'You\'ve successfuly logged in'),
                    next_page,
                )
            )

    return render(request, 'askup/login_form.html', {'form': form})


def logout_view(request):
    """Provide the logout view and functionality."""
    logout(request)
    return redirect(
        add_notification_to_url(
            ('danger', 'You were logged out'),
            '/',
        ),
    )


@user_group_required('admin')
def organization_update(request, pk):
    """Provide the update qset view for the teacher/admin."""
    organization = get_object_or_404(Organization, pk=pk)
    notification = None

    if request.method == 'POST':
        form = OrganizationModelForm(request.POST or None, instance=organization)

        if form.is_valid():
            form.save()
            notification = ('success', 'Organization was successfuly edited')

    url = add_notification_to_url(
        notification,
        reverse('askup:organization', kwargs={'pk': organization.id}),
    )

    return redirect(url)


@login_required
def qset_create(request):
    """Provide the create qset view for the student/teacher/admin."""
    parent_qset_id = request.POST.get('parent_qset')
    parent_qset = get_object_or_404(Qset, pk=parent_qset_id)
    form = compose_qset_form(request, parent_qset_id)

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
            'main_title': 'Create subject:',
            'submit_label': 'Create',
            'breadcrumbs': parent_qset.get_parents()
        }
    )


@user_group_required('teacher', 'admin')
def qset_update(request, pk):
    """Provide the update qset view for the student/teacher/admin."""
    qset = get_object_or_404(Qset, pk=pk)

    if not request._is_admin and request.user not in qset.top_qset.users.all():
        return redirect(reverse('askup:organizations'))

    if request.method == 'GET':
        form = QsetModelForm(user=request.user, instance=qset, qset_id=qset.id)
    else:
        form = QsetModelForm(request.POST or None, user=request.user, instance=qset, qset_id=qset.id)

        if form.is_valid():
            form.save()
            notification = ('success', 'Subject was successfuly saved')
            return redirect(
                add_notification_to_url(
                    notification,
                    reverse('askup:qset', kwargs={'pk': qset.id}),
                )
            )

    return qset_update_form_template(request, form, qset)


@user_group_required('teacher', 'admin')
def qset_delete(request, pk):
    """Provide the delete qset view for the teacher/admin."""
    qset = get_object_or_404(Qset, pk=pk)
    redirect_response = None

    if qset.parent_qset_id is None:
        return redirect(reverse('askup:qset', kwargs={'pk': qset.id}))

    if not request._is_admin and request.user not in qset.top_qset.users.all():
        return redirect(reverse('askup:organizations'))

    if request.method == 'POST':
        redirect_response = delete_qset_by_form(
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


@login_required
def qset_user_questions(request, qset_id, user_id):
    """Provide a create question view for the student/teacher/admin."""
    log.debug(
        'Got the qset user questions request for the qset_id - %s and user_id - %s', qset_id, user_id
    )
    questions = Question.objects.filter(qset_id=qset_id, user_id=user_id).order_by(
        '-vote_value', 'text'
    )
    response = list(questions.values_list("id", "text", "vote_value"))
    return JsonResponse(response, safe=False)


@login_required
def question_answer(request, question_id=None):
    """Provide a create question view for the student/teacher/admin."""
    log.debug('Got the question answering request for the question_id: %s', question_id)
    is_quiz = request.GET.get('filter') is not None
    question = Question.objects.filter(id=question_id).first()

    if question is None:
        return redirect(reverse('askup:organizations'))

    filter = get_clean_filter_parameter(request)
    form = do_make_answer_form(request, question)

    if request.method == 'GET':
        return render(
            request,
            'askup/question_answer.html',
            {
                'form': form,
                'question_id': question.id,
                'question_text': question.text,
                'question_vote_value': question.vote_value,
                'question_answer_text': question.answer_text,
                'filter': filter * is_quiz,
                'breadcrumbs': question.qset.get_parents(True),
            }
        )
    else:
        response = validate_answer_form_and_create(form, request, question)
        return JsonResponse(response)


def do_make_answer_form(request, question):
    """Compose and return answer form."""
    if request.method == 'POST':
        return AnswerModelForm(request.POST or None, parent_qset_id=question.qset_id)
    else:
        return AnswerModelForm(parent_qset_id=question.qset_id)


@login_required
def question_create(request, qset_id=None):
    """Provide a create question view for the student/teacher/admin."""
    log.debug('Got the question creation request for the qset_id: %s', qset_id)

    if qset_id:
        qset = get_object_or_404(Qset, pk=qset_id)
    else:
        qset = None

    form, notification = compose_question_form_and_create(request, qset_id)

    return render(
        request,
        'askup/question_form.html',
        {
            'form': form,
            'main_title': 'Create question:',
            'submit_label': 'Create',
            'breadcrumbs': qset and qset.get_parents(True),
            'notification_class': notification[0],
            'notification_text': notification[1],
        }
    )


@user_group_required('student', 'teacher', 'admin')
def question_edit(request, pk):
    """Provide an edit question view for the student/teacher/admin."""
    question = get_object_or_404(Question, pk=pk)
    user = request.user

    if not request._is_admin and user not in question.qset.top_qset.users.all():
        return redirect(reverse('askup:organizations'))

    if not request._is_admin and not request._is_teacher and user.id != question.user_id:
        return redirect(reverse('askup:organizations'))

    form, redirect_response = do_compose_question_form_and_update(request, question)

    return redirect_response or render(
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
    redirect_response = None

    if request.method == 'POST':
        form = QuestionModelForm(
            request.POST,
            user=request.user,
            instance=question,
            qset_id=question.qset_id,
        )

        if form.is_valid():
            form.save()
            url = add_notification_to_url(
                ('success', 'The question is saved successfuly'),
                reverse('askup:qset', kwargs={'pk': question.qset_id}),
            )
            redirect_response = redirect(url)
    else:
        form = QuestionModelForm(
            user=request.user,
            instance=question,
            qset_id=question.qset_id,
        )

    return form, redirect_response


@user_group_required('student', 'teacher', 'admin')
def question_delete(request, pk):
    """Provide a delete question view for the student/teacher/admin."""
    question = get_object_or_404(Question, pk=pk)
    qset_id = question.qset_id
    user = request.user

    if not request._is_admin and user not in question.qset.top_qset.users.all():
        return redirect(reverse('askup:organizations'))

    if not request._is_admin and not request._is_teacher and user.id != question.user_id:
        return redirect(reverse('askup:organizations'))

    form = do_make_form_and_delete(request, question)

    if form is None:
        redirect_url = add_notification_to_url(
            ('success', 'This question has been deleted successfuly'),
            reverse('askup:qset', kwargs={'pk': qset_id}),
        )
        return redirect(redirect_url)

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
    filter = request.GET.get('filter', None)
    is_quiz_start = request.GET.get('quiz_start', None)
    answer = get_object_or_404(Answer, pk=answer_id)

    if not do_user_checks_and_evaluate(request.user, answer, evaluation):
        return redirect(reverse('askup:organizations'))

    if filter:
        # If it's a Quiz
        filter = get_clean_filter_parameter(request)
        previous_question = answer.question
        qset_id = previous_question.qset_id
        next_question_id = get_next_quiz_question(
            request, filter, qset_id, is_quiz_start
        )

        if next_question_id:
            return get_quiz_question_redirect(next_question_id, filter)

    return redirect(reverse('askup:qset', kwargs={'pk': answer.question.qset_id}))


def get_next_quiz_question(request, filter, qset_id, is_quiz_start):
    """
    Get next quiz question id from the db/cache.
    """
    cache_key = 'quiz_user_{}_qset_{}'.format(request.user.id, qset_id)
    cached_quiz_questions = None if is_quiz_start else cache.get(cache_key)

    if cached_quiz_questions is None:
        questions_queryset = get_real_questions_queryset(qset_id)
        questions_queryset = apply_filter_to_queryset(request, filter, questions_queryset)
        cached_quiz_questions = list(questions_queryset.values_list("id", flat=True))

    if not cached_quiz_questions:
        cache.delete(cache_key)
        return None

    next_question_id = cached_quiz_questions.pop(0)
    cache.set(cache_key, cached_quiz_questions)  # Setting the cache for the 24 hours

    return next_question_id


def do_user_checks_and_evaluate(user, answer, evaluation):
    """Do user checks and evaluate answer for the answer evaluation view."""
    evaluation_int = int(evaluation)
    is_admin = check_user_has_groups(user, 'admin')

    if not is_admin and user not in answer.question.qset.top_qset.users.all():
        return False

    if evaluation_int in tuple(zip(*Answer.EVALUATIONS))[0]:
        answer.self_evaluation = evaluation_int
        answer.save()

    return True


def index_view(request):
    """Provide the index view."""
    log.error("This is an actual error, you see")
    return render(request, 'askup/index.html')


@login_required
def start_quiz_all(request, qset_id):
    """Provide a start quiz all in qset view for the student/teacher/admin."""
    log.debug('Got the quiz all request for the qset_id: %s', qset_id)
    qset = get_object_or_404(Qset, pk=qset_id)
    filter = get_clean_filter_parameter(request)
    user = request.user
    first_question_id = get_next_quiz_question(
        request, filter, qset.id, True
    )

    if not check_user_has_groups(user, 'admin') and user not in qset.top_qset.users.all():
        return redirect(reverse('askup:organizations'))

    if first_question_id is None:
        raise Http404

    if request.method == 'GET':
        return get_quiz_question_redirect(first_question_id, filter)
    else:
        return redirect(reverse('askup:organizations'))


def get_quiz_question_redirect(next_question_id, filter):
    """Get quiz question redirect."""
    return redirect(
        '{0}?filter={1}'.format(
            reverse('askup:question_answer', kwargs={'question_id': next_question_id}),
            filter,
        )
    )


@login_required
def question_upvote(request, question_id):
    """Provide a question up-vote functionality."""
    return question_vote(request.user, question_id, 1)


@login_required
def question_downvote(request, question_id):
    """Provide a question down-vote functionality."""
    return question_vote(request.user, question_id, -1)


def feedback_form_view(request):
    """Provide a feedback form view."""
    next_page = request.GET.get('next', None)
    form, redirect = validate_and_send_feedback_form(request, next_page)

    if redirect:
        return redirect

    return render(
        request,
        'askup/feedback_form.html',
        {
            'form': form,
        }
    )


def public_qsets_view(request):
    """Provide a public qsets view."""
    queryset = Qset.objects.filter(
        parent_qset_id__gt=0,
        for_unauthenticated=True
    )
    return render(
        request,
        'askup/public_qsets.html',
        {
            'object_list': queryset,
        }
    )
