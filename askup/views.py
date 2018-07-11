"""Askup django views."""
import logging

from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group, User
from django.contrib.sites.shortcuts import get_current_site
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.views import generic

from .forms import (
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
    get_real_questions_queryset,
)
from .utils.views import (
    compose_qset_form,
    compose_question_form_and_create,
    create_destroy_subscription,
    delete_qset_by_form,
    do_make_answer_form,
    do_user_checks_and_evaluate,
    get_clean_filter_parameter,
    get_my_subscriptions_context_data,
    get_next_quiz_question,
    get_question_to_answer,
    get_redirect_on_answer_fail,
    get_user_profile_context_data,
    get_user_profile_rank_list_context_data,
    qset_update_form_template,
    question_vote,
    select_user_organization,
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
def user_profile_view(request, user_id, organization_id=None):
    """Provide the user profile my questions view."""
    profile_user = get_object_or_404(User, pk=user_id)
    viewer_id = None if check_user_has_groups(request.user, 'admin') else request.user.id
    selected_organization = select_user_organization(
        profile_user.id, organization_id, viewer_id
    )

    if organization_id and selected_organization is None:
        # Case, when organization_id is specified in the link and restricted to this user
        return redirect(reverse('askup:user_profile', kwargs={'user_id': profile_user.id}))

    return render(
        request,
        'askup/user_profile.html',
        get_user_profile_context_data(
            request, profile_user, profile_user.id, selected_organization, viewer_id
        ),
    )


@login_required
def my_subscriptions_view(request, organization_id=None):
    """
    Provide the user profile "My Subscriptions" view.
    """
    user = request.user
    viewer_id = None if check_user_has_groups(user, 'admin') else user.id
    selected_organization = select_user_organization(
        user.id, organization_id, viewer_id
    )

    if organization_id and selected_organization is None:
        # Case, when organization_id is specified in the link and restricted to this user
        return redirect(reverse('askup:my_subscriptions'))

    return render(
        request,
        'askup/user_profile.html',
        get_my_subscriptions_context_data(
            request, user, user.id, selected_organization, viewer_id
        ),
    )


@login_required
def user_profile_rank_list_view(request, user_id, organization_id=None):
    """
    Provide the user profile rank list view.
    """
    profile_user = get_object_or_404(User, pk=user_id)
    viewer_id = None if check_user_has_groups(request.user, 'admin') else request.user.id
    selected_organization = select_user_organization(
        profile_user.id, organization_id, viewer_id
    )

    if organization_id and selected_organization is None:
        # Case, when organization_id is specified in the link and restricted to this user
        return redirect(reverse('askup:user_profile_rank_list', kwargs={'user_id': profile_user.id}))

    if selected_organization is None:
        return redirect(reverse('askup:user_profile', kwargs={'user_id': profile_user.id}))

    return render(
        request,
        'askup/user_profile.html',
        get_user_profile_rank_list_context_data(
            request, profile_user, profile_user.id, selected_organization, viewer_id
        ),
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

        return redirect(add_notification_to_url(notification, reverse('index')))

    return(render(request, 'askup/sign_up_activation_invalid.html'))


def login_view(request):
    """Provide the login view and functionality."""
    if request.user.is_authenticated():
        return redirect(reverse('index'))

    form = UserLoginForm(request.POST or None, request=request)
    next_page = request.GET.get('next', reverse('index'))

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
            reverse('index'),
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
    can_edit = False
    questions = Question.objects.filter(qset_id=qset_id, user_id=user_id).order_by(
        '-vote_value', 'text'
    )
    if request.user.id == int(user_id) or check_user_has_groups(request.user, ['admin', 'teacher']):
        can_edit = True

    response = {
        'can_edit': can_edit,
        'questions': list(questions.values_list("id", "qset_id", "text", "vote_value")),
    }
    return JsonResponse(response, safe=False)


@user_group_required('student', 'teacher', 'admin')
def qset_subscription(request, qset_id, subscribe):
    """
    Provide a view for the user to subscribe/unsubscribe to the specified subject.
    """
    if request._is_admin:
        qset = Qset.objects.filter(id=qset_id).first()
    else:
        qset = Qset.objects.filter(id=qset_id, top_qset__users__id=request.user.id).first()

    if qset is None:
        response = {
            'result': 'fail',
            'message': 'You have no permissions to subscribe to this subject',
            'url': reverse('askup:qset_subscription', kwargs={'qset_id': qset_id, 'subscribe': subscribe}),
        }
    else:
        create_destroy_subscription(qset.id, request.user.id, subscribe)
        response = {
            'result': 'success',
            'message': 'You\'ve successfuly subscribed to the subject: {}',
            'url': reverse(
                'askup:qset_subscription',
                kwargs={
                    'qset_id': qset_id,
                    'subscribe': revert_subscribe_command(subscribe),
                }
            ),
        }

    return JsonResponse(response, safe=False)


def revert_subscribe_command(subscribe):
    """
    Revert subscribe command and return it.

    :return: str
    """
    return '{}subscribe'.format('un' if subscribe == 'subscribe' else '')


@login_required
def question_answer(request, question_id, qset_id):
    """Provide a create question view for the student/teacher/admin."""
    log.debug('Got the question answering request for the question_id: %s', question_id)
    is_quiz = bool(request.GET.get('filter'))
    filter = get_clean_filter_parameter(request)
    question = get_question_to_answer(request, question_id)

    if question is None:
        return get_redirect_on_answer_fail(request, qset_id, filter, is_quiz)

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
def answer_evaluate(request, qset_id, answer_id, evaluation):
    """Provide a self-evaluation for the student/teacher/admin."""
    log.debug(
        'Got the "%s" evaluation for the answer_id - %s',
        evaluation,
        answer_id
    )
    filter = request.GET.get('filter', None)
    is_quiz_start = request.GET.get('quiz_start', None)
    answer = Answer.objects.filter(pk=answer_id).first()

    if not do_user_checks_and_evaluate(request.user, answer, evaluation, qset_id):
        return redirect(reverse('askup:organizations'))

    if filter:
        # If it's a Quiz
        filter = get_clean_filter_parameter(request)
        next_question_id = get_next_quiz_question(
            request.user.id, filter, qset_id, is_quiz_start
        )

        if next_question_id:
            return get_quiz_question_redirect(qset_id, next_question_id, filter)

    return redirect(reverse('askup:qset', kwargs={'pk': qset_id}))


def index_view(request):
    """Provide the index view."""
    return render(request, 'askup/index.html')


@login_required
def start_quiz_all(request, qset_id):
    """Provide a start quiz all in qset view for the student/teacher/admin."""
    log.debug('Got the quiz all request for the qset_id: %s', qset_id)
    qset = get_object_or_404(Qset, pk=qset_id)
    filter = get_clean_filter_parameter(request)
    user = request.user
    first_question_id = get_next_quiz_question(
        request.user.id, filter, qset.id, True
    )

    if not check_user_has_groups(user, 'admin') and user not in qset.top_qset.users.all():
        return redirect(reverse('askup:organizations'))

    if first_question_id is None:
        return redirect(
            add_notification_to_url(
                ('danger', 'This subject is unavailable'),
                reverse('askup:organizations'),
            )
        )

    if request.method == 'GET':
        return get_quiz_question_redirect(qset_id, first_question_id, filter)
    else:
        return redirect(reverse('askup:organizations'))


def get_quiz_question_redirect(qset_id, next_question_id, filter):
    """Get quiz question redirect."""
    return redirect(
        '{0}?filter={1}'.format(
            reverse(
                'askup:question_answer',
                kwargs={'question_id': next_question_id, 'qset_id': qset_id}
            ),
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
