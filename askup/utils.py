import logging

from django.contrib.auth.models import User
from django.core.handlers.wsgi import WSGIRequest
from django.db import connection
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse

log = logging.getLogger(__name__)


def do_redirect_unauthenticated(user):
    """Return redirect in case of unauthenticated user and return False otherwise."""
    if not user.is_authenticated():
        logging.info('Unauthenticated user tried to perform unauthorized action')
        return redirect(reverse('askup:sign_in'))
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


def user_group_required(*required_groups):
    """
    Decorate a view function to check if user belongs to one of the groups passed as an arguments.

    Can decorate a simple view function as well as dispatch method of generic view class.
    """
    def wrapper(func):
        def wrapped_function(*args, **kwargs):
            request = args[0] if isinstance(args[0], WSGIRequest) else args[0].request
            user = request.user
            auth_check_result = do_redirect_unauthenticated(user)

            if auth_check_result:
                return auth_check_result

            if check_user_has_groups(user, required_groups):
                return func(*args, **kwargs)

            return redirect(reverse('askup:organizations'))

        return wrapped_function

    return wrapper


def check_user_has_groups(user, required_groups):
    """Check if user has required groups."""
    if type(required_groups) is str:
        required_groups = [required_groups]

    required_groups_lower = set(name.lower() for name in required_groups)
    user_groups = set(name.lower() for name in user.groups.values_list('name', flat=True))

    if required_groups_lower.intersection(user_groups):
        return True

    logging.info('User tried to perform unauthorized action')
    return False


def get_user_score_by_id(user_id):
    """
    Return total score of the user by id.

    Summarizes all the vote_value of the user questions to count a score.
    """
    with connection.cursor() as cursor:
        cursor.execute('select sum(vote_value) from askup_question where user_id = %s', (user_id,))
        return cursor.fetchone()[0] or 0

    return 0


def get_user_questions_count(user_id):
    """Return total questions number for the user."""
    user = get_object_or_404(User, pk=user_id)

    if check_user_has_groups(user, 'admins'):
        return get_admin_questions_count()

    if check_user_has_groups(user, 'teachers'):
        return get_teacher_questions_count(user_id)

    return get_student_questions_count(user_id)


def get_student_questions_count(user_id):
    """Return total questions number of the student."""
    with connection.cursor() as cursor:
        cursor.execute('select count(id) from askup_question where user_id = %s', (user_id,))
        return cursor.fetchone()[0] or 0

    return 0


def get_teacher_questions_count(user_id):
    """
    Return total questions number for the teacher.

    Counts all questions of organizations assigned to the teacher.
    """
    with connection.cursor() as cursor:
        cursor.execute(
            'select sum(aq.questions_count) from askup_qset_users as aqu' +
            ' inner join askup_qset aq on aq.id = aqu.qset_id' +
            ' where aq.parent_qset_id is null and aqu.user_id = %s',
            (user_id,)
        )
        return cursor.fetchone()[0] or 0

    return 0


def get_admin_questions_count():
    """
    Return total questions number for the admin.

    Counts all questions of every organization.
    """
    with connection.cursor() as cursor:
        cursor.execute(
            'select sum(aq.questions_count) from askup_qset as aq' +
            ' where aq.parent_qset_id is null'
        )
        return cursor.fetchone()[0] or 0

    return 0


def get_user_answers_count(user_id):
    """Return total answers number for the user."""
    user = get_object_or_404(User, pk=user_id)

    if check_user_has_groups(user, 'admins'):
        return get_admin_answers_count()

    if check_user_has_groups(user, 'teachers'):
        return get_teacher_answers_count(user_id)

    return get_student_answers_count(user_id)


def get_student_answers_count(user_id):
    """Return total answers number of the student."""
    with connection.cursor() as cursor:
        cursor.execute('select count(id) from askup_answer where user_id = %s', (user_id,))
        return cursor.fetchone()[0] or 0

    return 0


def get_teacher_answers_count(user_id):
    """
    Return total answers number for the teacher.

    Counts all answers of organizations assigned to the teacher.
    """
    with connection.cursor() as cursor:
        cursor.execute(
            'select count(aa.id) from askup_qset_users as aqu ' +
            'inner join askup_qset as aq on aq.top_qset_id = aqu.qset_id ' +
            'inner join askup_question as aque on aque.qset_id = aq.id ' +
            'inner join askup_answer as aa on aa.question_id = aque.id ' +
            'where aq.parent_qset_id is not null and aqu.user_id = %s',
            (user_id,)
        )
        return cursor.fetchone()[0] or 0

    return 0


def get_admin_answers_count():
    """
    Return total answers number for the admin.

    Counts all answers of every organization.
    """
    with connection.cursor() as cursor:
        cursor.execute('select count(id) from askup_answer')
        return cursor.fetchone()[0] or 0

    return 0
