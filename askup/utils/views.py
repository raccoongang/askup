from datetime import timedelta
import logging

from django.core.cache import cache
from django.core.handlers.wsgi import WSGIRequest
from django.db.models import F, Max
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from askup.forms import AnswerModelForm, FeedbackForm, QsetModelForm, QuestionModelForm
from askup.models import Answer, Organization, Qset, QsetUserSubscription, Question
from askup.utils.general import (
    add_notification_to_url,
    check_user_has_groups,
    compose_user_full_name_from_object,
    get_checked_user_organization_by_id,
    get_first_user_organization,
    get_organization_subjects,
    get_real_questions_queryset,
    get_student_last_week_correct_answers_count,
    get_student_last_week_incorrect_answers_count,
    get_student_last_week_questions_count,
    get_student_last_week_votes_value,
    get_user_correct_answers_count,
    get_user_incorrect_answers_count,
    get_user_organizations_for_filter,
    get_user_place_in_rank_list,
    get_user_profile_rank_list_and_total_users,
    get_user_score_by_id,
    get_user_subjects,
    send_feedback,
)
from askup.utils.models import check_user_and_create_question


log = logging.getLogger(__name__)
QUESTION_DELETED_TEXT = 'This question was deleted since you\'ve opened it! Redirecting you to {}'
QSET_QUESTION_FILTERS = {
    'all': ('All', 'All the questions'),
    'mine': ('Mine', 'My question'),
    'others': ('Others', 'The questions of the others'),
    'unanswered': ('Unanswered', 'The questions that I didn\'t answer before'),
    'incorrect': ('Incorrect', 'The questions that I was incorrectly answered last time'),
    'last_7_days': ('Last 7 days', 'The questions that were created in the last 7 days'),
}


def do_redirect_unauthenticated(user, back_url):
    """Return redirect in case of unauthenticated user and return False otherwise."""
    if not user.is_authenticated():
        logging.info('Unauthenticated user tried to perform unauthorized action')
        return redirect('{0}?next={1}'.format(reverse('askup:sign_in'), back_url))
    else:
        return False


def check_self_for_redirect_decorator(func):
    """
    Redirect on self._redirect presence.

    Can decorate a dispatch() view class method to redirect request if self._redirect is present.
    """
    def wrapper(*args, **kwargs):
        func_result = func(*args, **kwargs)
        redirect = check_self_for_redirect(args[0])
        return redirect or func_result

    return wrapper


def check_self_for_redirect(obj):
    """Check if object has a _redirect property and return it if found."""
    redirect = getattr(obj, '_redirect', None)
    return redirect or False


def user_group_required(*required_groups):
    """
    Decorate a view function to check if user belongs to one of the groups passed as an arguments.

    Can decorate a simple view function as well as dispatch method of generic view class.
    """
    def wrapper(func):
        def wrapped_function(*args, **kwargs):
            request = args[0] if isinstance(args[0], WSGIRequest) else args[0].request
            user = request.user
            auth_check_result = do_redirect_unauthenticated(user, request.get_full_path())

            if auth_check_result:
                return auth_check_result

            if check_user_has_groups(user, required_groups):
                set_group_properties_to_request(request)
                return func(*args, **kwargs)

            return redirect(reverse('askup:organizations'))

        return wrapped_function

    return wrapper


def set_group_properties_to_request(request, groups_to_set=('admin', 'teacher', 'student')):
    """Set _is_<group> like properties to the request object for later usage in view etc."""
    for group in groups_to_set:
        setattr(request, '_is_{}'.format(group), check_user_has_groups(request.user, group))


def qset_update_form_template(request, form, qset):
    """Compose and return the qset update form template."""
    return render(
        request,
        'askup/qset_form.html',
        {
            'form': form,
            'main_title': 'Edit subject',
            'submit_label': 'Save',
            'breadcrumbs': qset.get_parents()
        }
    )


def delete_qset_by_form(form, qset):
    """Perform a form validation and delete qset."""
    if form.is_valid():  # checks the CSRF
        parent = qset.parent_qset
        qset.delete()
        redirect_url = 'askup:organization' if parent.parent_qset_id is None else 'askup:qset'
        return redirect(reverse(redirect_url, kwargs={'pk': parent.id}))

    return None


def compose_qset_form(request, parent_qset_id):
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


def compose_question_form_and_create(request, qset_id):
    """Compose form and create question on validation success."""
    user = request.user
    form = None
    notification = ('', '')

    if request.method == 'POST':
        form = compose_question_create_form(request, user, qset_id)
        obj = question_create_form_validate(form, user)
        qset_id = obj and obj.qset_id
        form, notification = compose_question_creation_notification(obj, form)

    if form is None:
        form = compose_question_create_form(
            request, user, qset_id, clean_form=True
        )

    return form, notification


def compose_question_creation_notification(obj, form):
    """Compose question creation notification."""
    if obj:
        form = None
        url = reverse('askup:qset', kwargs={'pk': obj.qset_id})
        message = (
            'Your question has been submitted! ' +
            'View it <a href="{0}" class="bu">here</a> ' +
            'or create a new question below'
        )
        notification = ('success', message.format(url))
    else:
        notification = ('danger', 'Question wasn\'t created')

    return form, notification


def question_create_form_validate(form, user):
    """Validate the form and return question on success or None on failure."""
    if form.is_valid():
        qset = get_object_or_404(Qset, pk=form.cleaned_data.get('qset').id)
        text = form.cleaned_data.get('text')
        answer_text = form.cleaned_data.get('answer_text')
        blooms_tag = form.cleaned_data.get('blooms_tag')
        return check_user_and_create_question(user, qset, text, answer_text, blooms_tag)

    return None


def compose_question_create_form(request, user, qset_id, clean_form=False):
    """Compose create question form."""
    if request.method == 'POST' and clean_form is False:
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


def question_vote(user, question_id, value):
    """Provide a general question vote functionality."""
    question = get_object_or_404(Question, pk=question_id)

    if user.id == question.user_id:
        response = {
            'result': 'error',
            'message': 'You cannot vote for your own questions'
        }
        return JsonResponse(response)

    is_admin = check_user_has_groups(user, 'admin')

    if not is_admin and user not in question.qset.top_qset.users.all():
        response = {
            'result': 'error',
            'message': 'You have no permissions to vote for this question'
        }
        return JsonResponse(response)

    vote_result, message = question.vote(user.id, value)

    if vote_result is False:
        response = {'result': 'error', 'message': message}
    else:
        response = {'result': 'success', 'message': message, 'value': vote_result}

    return JsonResponse(response)


def validate_answer_form_and_create(form, request, question):
    """
    Validate answer form and create an Answer object on success.

    Returns response dictionary to pass to the JsonResponse after.
    """
    response = {'result': 'success'}
    user = request.user

    if form.is_valid():
        text = form.cleaned_data.get('text')
        is_admin = check_user_has_groups(request.user, 'admin')

        if not is_admin and user not in question.qset.top_qset.users.all():
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
        response['evaluation_urls'] = get_evaluation_urls(request, question.qset_id, answer.id)
    else:
        response['result'] = 'error'

    return response


def get_evaluation_urls(request, qset_id, answer_id):
    """
    Get the evaluation urls to send to the client side in the question answer form.
    """
    filter_value = request.GET.get('filter', '')

    if filter_value:
        query_args_string = '?filter={}'.format(clean_filter_parameter(filter_value))
    else:
        query_args_string = ''

    urls = {}

    for evaluation, url_name in Answer.EVALUATIONS:
        urls[url_name] = '{}{}'.format(
            reverse(
                'askup:answer_evaluate',
                kwargs={
                    'qset_id': qset_id,
                    'answer_id': answer_id,
                    'evaluation': evaluation,
                },
            ),
            query_args_string,
        )
    return urls


def validate_and_send_feedback_form(request, next_page):
    """Compose form and create question on validation success."""
    user = request.user
    subject = request.GET.get('subject', '')
    form = FeedbackForm(
        request.POST or None,
        user=user,
        subject=subject,
    )

    if request.method == 'POST':
        if form.is_valid():
            email = form.cleaned_data.get('email')
            subject = form.cleaned_data.get('subject')
            text = form.cleaned_data.get('message')
            send_feedback(email, subject, text)
            return None, redirect(
                add_notification_to_url(
                    ('success', 'Thank you for your feedback!'),
                    next_page or reverse('index'),
                )
            )

    return form, None


def get_clean_filter_parameter(request):
    """Return a clean user filter value."""
    get_parameter = request.GET.get('filter')
    return clean_filter_parameter(get_parameter)


def clean_filter_parameter(parameter):
    """
    Return a clean filter parameter.
    """
    allowed_filters = QSET_QUESTION_FILTERS.keys()
    return 'all' if parameter not in allowed_filters else parameter


def apply_filter_to_queryset(user_id, filter, queryset):
    """Return a queryset with user filter applied."""
    if filter in ('mine', 'others'):
        return apply_mine_or_others_filter(user_id, filter, queryset)

    if filter == 'unanswered':
        return queryset.filter(answer__isnull=True)

    if filter == 'incorrect':
        return queryset.annotate(last_answer_date=Max('answer__created_at')).filter(
            answer__created_at=F('last_answer_date'),
            answer__self_evaluation__lte=1,  # only "wrong" or sort-of "answers"
        )

    if filter == 'last_7_days':
        return queryset.filter(
            created_at__gte=(
                timezone.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(weeks=1)
            )
        )

    return queryset


def apply_mine_or_others_filter(user_id, filter, queryset):
    """
    Apply the "mine" or the "others" user filters to the given queryset.
    """
    if filter == 'mine':
        return queryset.filter(user_id=user_id)

    return queryset.exclude(user_id=user_id)


def do_user_checks_and_evaluate(user, answer, evaluation, qset_id):
    """
    Do user checks and evaluate answer for the answer evaluation view.
    """
    evaluation_int = int(evaluation)
    is_admin = check_user_has_groups(user, 'admin')
    user_permitted = Organization.objects.filter(qset__in=[qset_id], users__in=[user.id]).exists()

    if not is_admin and not user_permitted:
        return False

    # <answer> can be passed into this function as None if it was deleted in pair with the
    # question it belongs before the evaluation request was sent
    if evaluation_int in next(zip(*Answer.EVALUATIONS)) and answer:
        answer.self_evaluation = evaluation_int
        answer.save()

    return True


def select_user_organization(user_id, requested_organization_id, viewer_id=None):
    """
    Select the organization for the user profile view.

    May return organization object or None.
    If organization_id is None, then returns a first organization from the user relations.
    If user has no organizations in related then returns None.
    """
    if requested_organization_id:
        return get_checked_user_organization_by_id(user_id, requested_organization_id, viewer_id)

    return get_first_user_organization(user_id, viewer_id)


def get_user_profile_context_data(request, profile_user, user_id, selected_organization, viewer_id):
    """
    Return the context data used in the user profile view template.
    """
    context_data = {
        'profile_user': profile_user,
        'full_name': compose_user_full_name_from_object(profile_user),
        'viewer_user_id': request.user.id,
        'is_owner': user_id == request.user.id,
        'is_student': check_user_has_groups(profile_user, 'student'),
        'user_organizations': get_user_organizations_for_filter(profile_user.id, viewer_id),
        'rank_list': tuple(),
        'rank_list_total_users': 0,
        'own_subjects': get_user_subjects(selected_organization, user_id),
        'selected_organization': selected_organization,
        'select_url_name': 'askup:{}'.format(request.resolver_match.url_name),
    }
    context_data.update(get_user_organization_statistics(user_id, selected_organization))
    return context_data


def get_my_subscriptions_context_data(request, profile_user, user_id, selected_organization, viewer_id):
    """
    Return the context data used in the user profile view template.
    """
    context_data = {
        'profile_user': profile_user,
        'full_name': compose_user_full_name_from_object(profile_user),
        'viewer_user_id': request.user.id,
        'is_owner': user_id == request.user.id,
        'is_student': check_user_has_groups(profile_user, 'student'),
        'user_organizations': get_user_organizations_for_filter(profile_user.id, viewer_id),
        'rank_list': tuple(),
        'rank_list_total_users': 0,
        'organization_subjects': get_organization_subjects(selected_organization, user_id),
        'selected_organization': selected_organization,
        'select_url_name': 'askup:{}'.format(request.resolver_match.url_name),
    }
    context_data.update(get_user_organization_statistics(user_id, selected_organization))
    return context_data


def get_user_profile_rank_list_context_data(
    request, profile_user, user_id, selected_organization, viewer_id
):
    """
    Return the context data used in the user profile rank list view template.
    """
    rank_list, total_users = get_user_profile_rank_list_and_total_users(
        profile_user.id, request.user.id, selected_organization.id
    )
    context_data = {
        'profile_user': profile_user,
        'full_name': compose_user_full_name_from_object(profile_user),
        'viewer_user_id': request.user.id,
        'is_owner': user_id == request.user.id,
        'is_student': check_user_has_groups(profile_user, 'student'),
        'user_organizations': get_user_organizations_for_filter(profile_user.id, viewer_id),
        'rank_list': rank_list,
        'rank_list_total_users': total_users,
        'own_subjects': tuple(),
        'selected_organization': selected_organization,
        'select_url_name': 'askup:{}'.format(request.resolver_match.url_name),
    }
    context_data.update(get_user_organization_statistics(user_id, selected_organization))
    return context_data


def get_user_organization_statistics(user_id, organization):
    """
    Return a dictionary with the statistics parameters to pass into the user_profile template.
    """
    return {
        'user_rank_place': get_user_place_in_rank_list(organization, user_id),
        'own_score': get_user_score_by_id(user_id, organization=organization),
        'own_correct_answers': get_user_correct_answers_count(user_id, organization=organization),
        'own_incorrect_answers': get_user_incorrect_answers_count(user_id, organization=organization),
        'own_last_week_questions': get_student_last_week_questions_count(
            user_id, organization=organization
        ),
        'own_last_week_thumbs_up': get_student_last_week_votes_value(
            user_id, organization=organization
        ),
        'own_last_week_correct_answers': get_student_last_week_correct_answers_count(
            user_id, organization=organization
        ),
        'own_last_week_incorrect_answers': get_student_last_week_incorrect_answers_count(
            user_id, organization=organization
        ),
    }


def get_next_quiz_question(user_id, filter, qset_id, is_quiz_start):
    """
    Get next quiz question id from the db/cache.

    May return question_id or None (if there are no existent questions in cached list).
    """
    cache_key = 'quiz_user_{}_qset_{}'.format(user_id, qset_id)
    cached_quiz_questions = None if is_quiz_start else cache.get(cache_key)

    if cached_quiz_questions is None:
        questions_queryset = get_real_questions_queryset(qset_id)
        questions_queryset = apply_filter_to_queryset(user_id, filter, questions_queryset)
        cached_quiz_questions = list(questions_queryset.values_list("id", flat=True))

    if not cached_quiz_questions:
        cache.delete(cache_key)
        return None

    next_question_id = pop_next_existent_question_id_from_list(cached_quiz_questions)
    cache.set(cache_key, cached_quiz_questions)  # Setting the cache for the default time
    return next_question_id  # may return None if no any existent questions were in cached list


def pop_next_existent_question_id_from_list(question_ids):
    """
    Pop every next inexistent question id in the list until you find the existent one.

    Returns first existent question_id if found, otherwise returns None.
    """
    while question_ids:
        next_question_id = question_ids.pop(0)

        if Question.objects.filter(id=next_question_id).exists():
            return next_question_id


def get_redirect_on_answer_fail(request, qset_id, filter, is_quiz):
    """
    Redirect to a backup question if answering question is failing due to deletion of question.

    Returns HttpResponseRedirect to the qset where question was located, to the next question
    in the quiz or to the organizations list.
    """
    if request.method == 'GET':
        # Case, when the question is not in viewer's organization and viewer isn't admin
        return redirect(reverse('askup:organizations'))

    if is_quiz:
        return get_json_redirect_next_quiz_question(request.user.id, qset_id, filter)

    return get_json_redirect_qset(qset_id)


def get_json_redirect_next_quiz_question(user_id, qset_id, filter):
    """
    Return the json object with redirect to the next question in the quiz.
    """
    next_question_id = get_next_quiz_question(user_id, filter, qset_id, False)

    if next_question_id is None:
        return get_json_redirect_qset(qset_id)

    redirect_url = reverse(
        'askup:question_answer',
        kwargs={'question_id': next_question_id, 'qset_id': qset_id}
    )
    notification = QUESTION_DELETED_TEXT.format('the next one in the Quiz...')
    return JsonResponse({
        'result': 'error',
        'redirect_url': redirect_url,
        'notification': notification,
    })


def get_json_redirect_qset(qset_id):
    """
    Return the json object with redirect to the qset.
    """
    notification = QUESTION_DELETED_TEXT.format('the correspondent subject...')
    return JsonResponse({
        'result': 'error',
        'redirect_url': reverse('askup:qset', kwargs={'pk': qset_id}),
        'notification': notification,
    })


def do_make_answer_form(request, question):
    """Compose and return answer form."""
    if request.method == 'POST':
        return AnswerModelForm(request.POST, parent_qset_id=question.qset_id)
    else:
        return AnswerModelForm(parent_qset_id=question.qset_id)


def get_question_to_answer(request, question_id):
    """
    Return a question corresponding to the user and question_id.

    If user has no permissions to the organization of this questions - return None.
    """
    question_queryset = Question.objects.filter(id=question_id)

    if not check_user_has_groups(request.user, 'admin'):
        question_queryset = question_queryset.filter(qset__top_qset__users__id=request.user.id)

    return question_queryset.first()


def create_destroy_subscription(subject_id, user_id, subscribe):
    """
    Create or destroy subscription object for specified user to the specified subject.

    @param subject_id: int
    @param user_id: int
    @param subscribe: str
    """
    if subscribe == 'subscribe':
        QsetUserSubscription.objects.get_or_create(qset_id=subject_id, user_id=user_id)
    else:
        subscription = QsetUserSubscription.objects.filter(qset_id=subject_id, user_id=user_id).first()

        if subscription:
            subscription.delete()
