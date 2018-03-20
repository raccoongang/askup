import logging

from django.core.handlers.wsgi import WSGIRequest
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from askup.forms import FeedbackForm, QsetModelForm, QuestionModelForm
from askup.models import Answer, Qset, Question
from askup.utils.general import (
    add_notification_to_url,
    check_user_has_groups,
    send_feedback,
)
from askup.utils.models import check_user_and_create_question


log = logging.getLogger(__name__)


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
        response['qset_id'] = question.qset_id
        response['answer_id'] = answer.id
    else:
        response['result'] = 'error'

    return response


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
                    next_page or '/',
                )
            )

    return form, None


def get_clean_filter_parameter(request):
    """Return a clean user filter value."""
    allowed_filters = ('all', 'mine', 'other')
    get_parameter = request.GET.get('filter')
    return 'all' if get_parameter not in allowed_filters else get_parameter


def apply_filter_to_queryset(request, filter, queryset):
    """Return a queryset with user filter applied."""
    if filter == 'mine':
        return queryset.filter(user_id=request.user.id)

    if filter == 'other':
        return queryset.exclude(user_id=request.user.id)

    return queryset


def do_user_checks_and_evaluate(user, answer, evaluation):
    """Do user checks and evaluate answer for the answer evaluation view."""
    evaluation_int = int(evaluation)
    is_admin = check_user_has_groups(user, 'admin')

    if not is_admin and user not in answer.question.qset.top_qset.users.all():
        return False

    if evaluation_int in tuple(zip(*Answer.EVALUATIONS))[0] and answer:
        answer.self_evaluation = evaluation_int
        answer.save()

    return True
