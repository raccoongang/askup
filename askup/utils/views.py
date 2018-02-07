import logging

from django.core.handlers.wsgi import WSGIRequest
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse

from .general import add_notification_to_url, check_user_has_groups, send_feedback
from .models import check_user_and_create_question


log = logging.getLogger(__name__)


def do_redirect_unauthenticated(user, back_url):
    """Return redirect in case of unauthenticated user and return False otherwise."""
    if not user.is_authenticated():
        logging.info('Unauthenticated user tried to perform unauthorized action')
        return redirect('{0}?next={1}'.format(reverse('askup:sign_in'), back_url))
    else:
        return False


def redirect_unauthenticated(func):
    """
    Decorate a view function to redirect requests of unauthenticated users.

    Can decorate a simple view function as well as dispatch method of generic view class.
    """
    def wrapper(*args, **kwargs):
        if isinstance(args[0], WSGIRequest):
            request = args[0]
        else:
            request = args[0].request

        return do_redirect_unauthenticated(request.user) or func(*args, **kwargs)

    return wrapper


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

    if redirect:
        return redirect
    else:
        return False


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
                return func(*args, **kwargs)

            return redirect(reverse('askup:organizations'))

        return wrapped_function

    return wrapper


def delete_qset_by_form(form, qset):
    """Perform a form validation and delete qset."""
    if form.is_valid():  # checks the CSRF
        parent = qset.parent_qset
        qset.delete()
        redirect_url = 'askup:organization' if parent.parent_qset_id is None else 'askup:qset'
        return redirect(reverse(redirect_url, kwargs={'pk': parent.id}))

    return None


def compose_qset_form(request, parent_qset_id, qset_model_form_class):
    """Compose qset form and return it."""
    if request.method == 'POST':
        return qset_model_form_class(
            request.POST or None,
            user=request.user,
            qset_id=parent_qset_id
        )
    else:
        return qset_model_form_class(
            user=request.user,
            qset_id=parent_qset_id
        )


def compose_question_form_and_create(
    request, qset_id, question_model_form_class, question_class, qset_class
):
    """Compose form and create question on validation success."""
    user = request.user

    if request.method == 'POST':
        form = compose_question_create_form(request, user, qset_id, question_model_form_class)

        if form.is_valid():
            qset = get_object_or_404(qset_class, pk=form.cleaned_data.get('qset').id)
            text = form.cleaned_data.get('text')
            answer_text = form.cleaned_data.get('answer_text')
            blooms_tag = form.cleaned_data.get('blooms_tag')

            return check_user_and_create_question(user, qset, text, answer_text, blooms_tag)
    else:
        form = compose_question_create_form(request, user, qset_id, question_model_form_class)

    return form, None


def compose_question_create_form(request, user, qset_id, question_model_form_class):
    """Compose create question form."""
    if request.method == 'POST':
        return question_model_form_class(
            request.POST,
            user=user,
            qset_id=qset_id,
        )
    else:
        return question_model_form_class(
            initial={'qset': qset_id},
            user=user,
            qset_id=qset_id,
        )


def question_vote(user, question_id, value, question_class):
    """Provide a general question vote functionality."""
    question = get_object_or_404(question_class, pk=question_id)

    if user.id == question.user_id:
        return redirect(reverse('askup:organizations'))

    is_admin = check_user_has_groups(user, 'admin')

    if not is_admin and user not in question.qset.top_qset.users.all():
        return redirect(reverse('askup:organizations'))

    vote_result = question.vote(user.id, value)

    if vote_result is False:
        response = {'result': 'error'}
    else:
        response = {'result': 'success', 'value': vote_result}

    return JsonResponse(response)


def validate_answer_form_and_create(form, request, question, answer_class):
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

        answer = answer_class.objects.create(
            text=text,
            question_id=question.id,
            user_id=user.id
        )
        response['answer_id'] = answer.id
    else:
        response['result'] = 'error'

    return response


def validate_and_send_feedback_form(request, form_class, next_page):
    """Compose form and create question on validation success."""
    user = request.user
    form = form_class(
        request.POST or None,
        user=user,
    )

    if request.method == 'POST':
        if form.is_valid():
            email = form.cleaned_data.get('email')
            subject = form.cleaned_data.get('subject')
            text = form.cleaned_data.get('text')
            send_feedback(email, subject, text)
            return None, redirect(
                add_notification_to_url(
                    ('success', 'Thank you for your feedback'),
                    next_page or '/',
                )
            )

    return form, None
