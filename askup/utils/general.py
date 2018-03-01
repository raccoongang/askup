import base64
import binascii
import json
import logging
from smtplib import SMTPException

from django.conf import settings
from django.contrib.auth.models import User
from django.core.mail.message import EmailMessage
from django.db import connection
from django.shortcuts import get_object_or_404

log = logging.getLogger(__name__)


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

    if check_user_has_groups(user, 'admin'):
        return get_admin_questions_count()

    if check_user_has_groups(user, 'teacher'):
        return get_teacher_questions_count(user_id)

    return get_student_questions_count(user_id)


def get_student_questions_count(user_id):
    """Return total questions count of the student."""
    with connection.cursor() as cursor:
        cursor.execute('select count(id) from askup_question where user_id = %s', (user_id,))
        return cursor.fetchone()[0] or 0

    return 0


def get_user_place_in_rank_list(user_id):
    """
    Return a rank list place of the user by id.
    """
    with connection.cursor() as cursor:
        cursor.execute(
            '''
                select rank from
                    (
                        select
                            au.id as user_id,
                            rank() over (
                                order by sum(coalesce(aq.vote_value, 0)) desc,
                                min(au.id) asc
                            ) as rank
                        from auth_user as au
                        left join askup_question aq on aq.user_id = au.id
                        group by au.id
                    ) as ranked
                    where ranked.user_id = %s
            ''',
            (user_id,)
        )
        result = cursor.fetchone()
        return (result and result[0]) or 0

    return 0


def get_user_correct_answers_count(user_id):
    """
    Return total amount of the correct answers of the user by id.
    """
    with connection.cursor() as cursor:
        cursor.execute('select count(id) from askup_answer where self_evaluation = 2 and user_id = %s', (user_id,))
        return cursor.fetchone()[0] or 0

    return 0


def get_user_incorrect_answers_count(user_id):
    """
    Return total amount of the incorrect answers of the user by id.
    """
    with connection.cursor() as cursor:
        cursor.execute(
            'select count(id) from askup_answer where self_evaluation in (0, 1) and user_id = %s',
            (user_id,)
        )
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

    if check_user_has_groups(user, 'admin'):
        return get_admin_answers_count()

    if check_user_has_groups(user, 'teacher'):
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


def send_feedback(from_email, subject, message):
    """Send a feedback from the <from_email> sender to all the admin users in the system."""
    admins = tuple(user.email for user in User.objects.filter(groups__name='Admin'))

    if admins:
        body = "Subject:\n{0}\n\nMessage:\n{1}".format(subject, message)
        send_feedback_to_recipient(admins, body, from_email)
        return True

    send_feedback_received_notification(from_email)
    logging.warning("The system didn't find any of admins to send a feedback form to.")
    return False


def send_feedback_to_recipient(admins, body, from_email):
    """Actually send a feedback email to recipients list serially."""
    for to_email in admins:
        try:
            send_mail(
                "Feedback from the web-site",
                body,
                settings.DEFAULT_FROM_EMAIL,
                (to_email,),
                reply_to=('AskUp support <{}>'.format(from_email),)
            )
        except SMTPException:
            log.exception(
                "Exception caught on email send:\n{}\n{}\n{}\n{}\n{}\n".format(
                    "Feedback from the web-site",
                    body,
                    settings.DEFAULT_FROM_EMAIL,
                    (to_email,),
                    ('AskUp support {}'.format(from_email),)
                )
            )


def send_feedback_received_notification(user_email):
    """
    Send a feedback notification email to the user.
    """
    body = "Hello.\n\nWe have received a message from you and will reply soon.\n\nThank you!"

    try:
        send_mail(
            "We have received your feedback",
            body,
            settings.DEFAULT_FROM_EMAIL,
            (user_email,),
        )
    except SMTPException:
        log.exception(
            "Exception caught on email send:\n{}\n{}\n{}\n{}\n".format(
                "We have received your feedback",
                body,
                settings.DEFAULT_FROM_EMAIL,
                (user_email,),
            )
        )


def send_mail(subject, message, from_email, recipient_list, reply_to=None):
    """
    Send mail with the specific parameters.

    Easy wrapper for sending a single message to a recipient list. All members
    of the recipient list will see the other recipients in the 'To' field.

    If auth_user is None, the EMAIL_HOST_USER setting is used.
    If auth_password is None, the EMAIL_HOST_PASSWORD setting is used.

    Note: The API for this method is frozen. New code wanting to extend the
    functionality should use the EmailMessage class directly.
    """
    mail = EmailMessage(subject, message, from_email, recipient_list, reply_to=reply_to)
    return mail.send()


def add_notification_to_url(notification, url):
    """Add a base64-encoded notification parameter to the url."""
    if notification is None:
        return url

    prefix = '&' if url.find('?') > -1 else '?'
    return '{0}{1}notification={2}'.format(
        url,
        prefix,
        base64.encodestring(json.dumps(notification).encode()).decode("utf-8")
    )


def extract_notification_from_request(request):
    """Extract and return a base64-encoded notification parameter from the request."""
    encoded = request.GET.get('notification') or request.POST.get('notification')

    if not encoded:
        return ('', '')

    try:
        notification = json.loads(base64.b64decode(encoded))
    except (json.JSONDecodeError, binascii.Error):
        notification = ('', '')

    return notification


def parse_response_url_to_parameters(response):
    """Parse response url to parameter pair strings "name=value"."""
    url_parts = response.url.split('?')

    if len(url_parts) < 2:
        return url_parts[0], []

    query_string = url_parts[1] if len(url_parts) > 1 else ''
    parameters = query_string.split('&') if query_string else []
    return url_parts[0], parameters


def get_student_last_week_questions_count(user_id):
    """Return last week questions count of the student."""
    with connection.cursor() as cursor:
        cursor.execute(
            """
                select count(id)
                from askup_question
                where user_id = %s and created_at >= now() - interval '1 week'
            """,
            (user_id,)
        )
        return cursor.fetchone()[0] or 0

    return 0


def get_student_last_week_votes_value(user_id):
    """Return last week thumbs ups student received."""
    with connection.cursor() as cursor:
        cursor.execute(
            """
                select sum(av.value)
                from askup_question as aq
                inner join askup_vote as av on av.question_id = aq.id
                where
                    aq.user_id = %s and
                    av.created_at >= now() - interval '1 week'
            """,
            (user_id,)
        )
        return cursor.fetchone()[0] or 0

    return 0


def get_student_last_week_correct_answers_count(user_id):
    """Return last week correct answers of the student."""
    with connection.cursor() as cursor:
        cursor.execute(
            """
                select count(id)
                from askup_answer
                where
                    self_evaluation = 2 and
                    user_id = %s and
                    created_at >= now() - interval '1 week'
            """,
            (user_id,)
        )
        return cursor.fetchone()[0] or 0

    return 0


def get_student_last_week_incorrect_answers_count(user_id):
    """Return last week correct answers of the student."""
    with connection.cursor() as cursor:
        cursor.execute(
            """
                select count(id)
                from askup_answer
                where self_evaluation in (0, 1)
                    and user_id = %s
                    and created_at >= now() - interval '1 week'
            """,
            (user_id,)
        )
        return cursor.fetchone()[0] or 0

    return 0
