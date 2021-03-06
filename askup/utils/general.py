import base64
import binascii
from collections import defaultdict
from datetime import timedelta
import json
import logging
from smtplib import SMTPException

from django.conf import settings
from django.contrib.auth.models import User
from django.core.mail import EmailMultiAlternatives
from django.core.mail.message import EmailMessage
from django.db import connection
from django.db.models import Count, Exists, IntegerField, OuterRef, Subquery, Sum
from django.shortcuts import get_object_or_404
from django.urls.base import reverse
from django.utils import timezone
from django.utils.html import strip_tags

import askup.models


log = logging.getLogger(__name__)
PROFILE_RANK_LIST_ELEMENTS_QUERY = """
    select * from
    (
        select
            rank() over (
                order by
                    sum(aq.vote_value) desc,
                    count(aq.id) asc
            ) as place,
            au.id as id,
            au.username as username,
            au.first_name as first_name,
            au.last_name as first_name,
            count(aq.id) as questions,
            sum(coalesce(aq.vote_value, 0)) as thumbs_up
        from auth_user as au
        inner join askup_question aq on aq.user_id = au.id
        inner join askup_qset aqs on aqs.id = aq.qset_id
        where aqs.top_qset_id = {}
        group by au.id
        order by place, case when au.id = {} then 1 else 0 end desc
    ) as ranked
    {}
"""
PROFILE_RANK_LIST_USER_PLACE_QUERY = """
    select rank from
    (
        select
            rank() over (
                order by
                    sum(aq.vote_value) desc,
                    count(aq.id) asc
            ) as rank,
            au.id as id
        from auth_user as au
        inner join askup_question aq on aq.user_id = au.id
        inner join askup_qset aqs on aqs.id = aq.qset_id
        where aqs.top_qset_id = %s
        group by au.id
    ) as ranked
    where ranked.id = %s
"""


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


def get_user_place_in_rank_list(organization, user_id):
    """
    Return a rank list place of the user by id.
    """
    if not organization:
        return 0

    organization_id = organization if isinstance(organization, int) else organization.id

    with connection.cursor() as cursor:
        cursor.execute(
            PROFILE_RANK_LIST_USER_PLACE_QUERY,
            (organization_id, user_id)
        )
        result = cursor.fetchone()
        return (result and result[0]) or 0


def get_user_profile_rank_list_and_total_users(rank_user_id, viewer_user_id, organization_id):
    """
    Aquire and return a list of rows for the user profile rank list in pair with total ranked users.
    """
    first_items = get_user_profile_rank_list_elements(organization_id, viewer_user_id)
    result_row_datas, user_is_present = compose_user_profile_rank_list_row_data(
        first_items, rank_user_id
    )
    total_users = get_rank_list_users_count(organization_id)

    if user_is_present:
        return result_row_datas, total_users

    result_row_datas += [(0, None, None, None, None)]  # adding an ellipsis row
    user_item = get_user_profile_rank_list_elements(
        organization_id, rank_user_id, 'where ranked.id = %s', (rank_user_id,)
    )
    user_row_data, _ = compose_user_profile_rank_list_row_data(user_item)

    if not user_row_data:
        user_row_data = [(-1, rank_user_id, None, None, None)]  # adding an ellipsis row

    result_row_datas += user_row_data
    return result_row_datas, total_users


def compose_user_profile_rank_list_row_data(rows, user_id_to_check=None):
    """
    Compose user profile rank list row datas from the query result rows.
    """
    items = []
    user_is_present = False

    for place, user_id, username, first_name, last_name, questions, thumbs_up in rows:
        if user_id_to_check == user_id:
            user_is_present = True

        name = compose_user_full_name(username, first_name, last_name)
        items.append((place, user_id, name, questions, thumbs_up))

    return items, user_is_present


def compose_user_full_name_from_object(user):
    """
    Return user's full name representation for the views from the user object.

    Needed because of unrequired first and last names.
    """
    return compose_user_full_name(user.username, user.first_name, user.last_name)


def compose_user_full_name(username, first_name, last_name):
    """
    Return user's full name representation for the views.

    Needed because of unrequired first and last names.
    """
    name = (first_name or last_name) and ' '.join((first_name, last_name))
    return '{} ({})'.format(name, username) if name else username


def get_user_profile_rank_list_elements(organization_id, viewer_user_id, expression='limit 10', args=None):
    """
    Return a rank list place of the user by id.
    """
    if args is None:
        args = []

    with connection.cursor() as cursor:
        cursor.execute(
            PROFILE_RANK_LIST_ELEMENTS_QUERY.format(organization_id, viewer_user_id, expression),
            args
        )
        result = cursor.fetchall()
        return result


def get_rank_list_users_count(organization_id):
    """
    Return a rank list total users count.
    """
    queryset = askup.models.Question.objects.filter(qset__top_qset_id=organization_id)
    result = queryset.aggregate(Count('user_id', distinct=True))
    return result['user_id__count']


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


def get_admin_answers_count():
    """
    Return total answers number for the admin.

    Counts all answers of every organization.
    """
    with connection.cursor() as cursor:
        cursor.execute('select count(id) from askup_answer')
        return cursor.fetchone()[0] or 0


def send_feedback(from_email, subject, message):
    """Send a feedback from the <from_email> sender to all the admin users in the system."""
    admins = tuple(user.email for user in User.objects.filter(groups__name='Admin'))

    if admins:
        body = "Subject:\n{0}\n\nMessage:\n{1}".format(subject, message)
        send_feedback_to_recipient(admins, body, from_email)
        return True

    logging.warning("The system didn't find any of admins to send a feedback form to.")
    return False


def send_feedback_to_recipient(admins, body, from_email):
    """Actually send a feedback email to recipients list serially."""
    for to_email in admins:
        try:
            send_mail(
                "Feedback from the web-site",
                body,
                'AskUp Mailer <mailer@askup.net>',
                (to_email,),
                reply_to=('AskUp mailer <{}>'.format(from_email),)
            )
        except SMTPException:
            log.exception(
                "Exception caught on email send:\n{}\n{}\n{}\n{}\n{}\n".format(
                    "Feedback from the web-site",
                    body,
                    'AskUp Mailer <mailer@askup.net>',
                    (to_email,),
                    ('AskUp mailer {}'.format(from_email),)
                )
            )


def send_subscription_emails():
    """
    Send the scheduled quizes to their recipients.

    Gets all the scheduled quizzes from the db QsetUserSubscription and sends to the users their subscripted quizzes.
    """
    queryset = askup.models.QsetUserSubscription.objects.filter(user__is_active=True)
    queryset = queryset.select_related('user', 'qset')
    count_queryset = askup.models.Question.objects.filter(
        qset_id=OuterRef('qset_id'),
        qset__question__created_at__gte=get_tz_past_datetime(weeks=1),
    )
    count_queryset = count_queryset.annotate(questions_count=Count('*')).values('questions_count')
    queryset = queryset.annotate(recent_questions_count=Subquery(count_queryset[:1], output_field=IntegerField()))
    result = queryset.order_by('user__email', 'qset__name').values_list(
        'user__email', 'user__first_name', 'qset_id', 'qset__name', 'recent_questions_count'
    )
    user_subscriptions, qsets_to_select_questions = get_subscriptions_and_qset_ids(result)
    qset_questions = {}

    for qset_id, recent_questions_count in qsets_to_select_questions.items():
        qset_questions[qset_id] = get_qset_questions_links(qset_id, recent_questions_count)

    if user_subscriptions:
        do_send_subscriptions_to_recipients(user_subscriptions, qset_questions)


def get_subscriptions_and_qset_ids(result):
    """
    Get the user_subscriptions and the qsets_to_select_questions dictionaries.
    """
    qsets_to_select_questions = {}
    user_subscriptions = defaultdict(list)

    for user_email, user_first_name, qset_id, qset_name, recent_questions_count in result:
        if recent_questions_count is None:
            continue

        key = '{}###{}'.format(user_email, user_first_name)
        user_subscriptions[key].append((qset_id, qset_name, recent_questions_count))
        qsets_to_select_questions[qset_id] = recent_questions_count

    return user_subscriptions, qsets_to_select_questions


def get_qset_questions_links(qset_id, total_questions_count):
    """
    Get top 5 subject's questions in a link format.

    :return: html code for the bulleted list of questions
    """
    questions_limit = 5
    questions_queryset = askup.models.Question.objects.filter(
        qset_id=qset_id,
        created_at__gte=get_tz_past_datetime(weeks=1),
    )
    questions_queryset = questions_queryset.order_by('-created_at')[:questions_limit]
    questions = questions_queryset.values('id', 'text')
    question_template = '<li><a href="{}://{}{}" title="{}">{}</a></li>'
    list_items = compose_questions_list(questions, qset_id, total_questions_count, questions_limit, question_template)
    return '\n'.join(list_items)


def compose_questions_list(questions, qset_id, total_questions_count, questions_limit, question_template):
    """
    Compose questions list items to join to the final HTML afterwards.

    :return: list of html items to join.
    """
    list_items = []

    for question in questions:
        list_items.append(
            question_template.format(
                settings.SERVER_PROTOCOL,
                settings.SERVER_HOSTNAME,
                reverse('askup:question_answer', kwargs={'question_id': question['id'], 'qset_id': qset_id}),
                question['text'],
                question['text'],
            )
        )

    if len(list_items):
        if total_questions_count > questions_limit:
            list_items.append('<li>...</li>')

        list_items.insert(0, '<ul>')
        list_items.append('</ul>')

    return list_items


def do_send_subscriptions_to_recipients(users_subscriptions, qset_questions):
    """
    Actually send a feedback email to recipients list serially.
    """
    subscription_link = get_my_subscriptions_link()
    body = (
        "Hello{}!<br/>\n<br/>\nHere are the subjects you've subscribed for," +
        " that have new questions for the last 7 days:<br/>\n<br/>\n{}\n<br/>" +
        "\n<br/>\n<br/>\nYou can manage your subscriptions {}."
    )

    for user_key, subscriptions in users_subscriptions.items():
        to_email, first_name = user_key.split('###')
        first_name_text = ', {}'.format(first_name) if first_name else ''
        body = body.format(
            first_name_text,
            compose_user_subscriptions_html(subscriptions, qset_questions),
            subscription_link,
        )
        do_send_subscription_email(body, to_email)


def do_send_subscription_email(body, to_email):
    """
    Send the subscription email to the specified user.
    """
    try:
        message = EmailMultiAlternatives(
            "Your subscriptions",
            strip_tags(body),
            settings.DEFAULT_FROM_EMAIL,
            [to_email],
            reply_to=[settings.DEFAULT_FROM_EMAIL],
        )
        message.attach_alternative(body, "text/html")
        message.send()
    except SMTPException:
        log.exception(
            "Exception caught on email send:\n{}\n{}\n{}\n{}\n{}\n".format(
                "Your subscriptions",
                body,
                settings.DEFAULT_FROM_EMAIL,
                [to_email],
                [settings.DEFAULT_FROM_EMAIL],
            )
        )


def get_my_subscriptions_link():
    """
    Get my subscriptions section link.
    """
    return '<a href="{}://{}{}" title="My subscriptions">here</a>'.format(
        settings.SERVER_PROTOCOL,
        settings.SERVER_HOSTNAME,
        reverse('askup:my_subscriptions'),
    )


def compose_user_subscriptions_html(subscriptions, qset_questions):
    """
    Compose subjects links html.
    """
    subscription_links = []
    link_template = '<h3><a href="{}://{}{}" target="_blank" title={}>{}</a> ({} new question{})</h3>\n{}'

    for qset_id, qset_name, recent_questions_count in subscriptions:
        url = reverse('askup:qset', kwargs={'pk': qset_id})
        plural_text = '' if recent_questions_count == 1 else 's'
        subscription_links.append(
            link_template.format(
                settings.SERVER_PROTOCOL,
                settings.SERVER_HOSTNAME,
                url,
                qset_name,
                qset_name,
                recent_questions_count,
                plural_text,
                qset_questions[qset_id],
            )
        )

    return '\n'.join(subscription_links)


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


def zero_on_organization_is_none(wrapping_function):
    """
    Check if first parameter is None.

    If so - return 0 and otherwise - execute the wrapped_function.
    """
    def wrapper_function(*args, **kwargs):
        if kwargs['organization'] is None:
            return 0

        return wrapping_function(*args, **kwargs)

    return wrapper_function


@zero_on_organization_is_none
def get_user_score_by_id(user_id, organization=None):
    """
    Return total score of the user by id.

    Summarizes all the vote_value of the user questions to count a score.
    """
    filter_kwargs = {
        'user_id': user_id,
        'qset__top_qset_id': organization.id,
    }
    return get_model_aggregation(
        askup.models.Question,
        filter_kwargs,
        aggregator_function=Sum,
        aggregated_field='vote_value',
    )


@zero_on_organization_is_none
def get_user_correct_answers_count(user_id, organization=None):
    """
    Return total amount of the correct answers of the user by id.
    """
    filter_kwargs = {
        'user_id': user_id,
        'self_evaluation': 2,
        'question__qset__top_qset_id': organization.id,
    }
    return get_model_aggregation(
        askup.models.Answer,
        filter_kwargs,
    )


@zero_on_organization_is_none
def get_user_incorrect_answers_count(user_id, organization=None):
    """
    Return total amount of the incorrect answers of the user by id.
    """
    filter_kwargs = {
        'user_id': user_id,
        'self_evaluation__in': (0, 1),
        'question__qset__top_qset_id': organization.id,
    }
    return get_model_aggregation(
        askup.models.Answer,
        filter_kwargs,
    )


@zero_on_organization_is_none
def get_student_last_week_questions_count(user_id, organization=None):
    """Return last week questions count of the student."""
    filter_kwargs = {
        'user_id': user_id,
        'qset__top_qset_id': organization.id,
        'created_at__gte': get_tz_past_datetime(weeks=1),
    }
    return get_model_aggregation(
        askup.models.Question,
        filter_kwargs,
    )


@zero_on_organization_is_none
def get_student_last_week_votes_value(user_id, organization=None):
    """Return last week thumbs ups student received."""
    filter_kwargs = {
        'user_id': user_id,
        'qset__top_qset_id': organization.id,
        'vote__created_at__gte': get_tz_past_datetime(weeks=1),
    }
    return get_model_aggregation(
        askup.models.Question,
        filter_kwargs,
        aggregator_function=Sum,
        aggregated_field='vote__value',
    )


@zero_on_organization_is_none
def get_student_last_week_correct_answers_count(user_id, organization=None):
    """Return last week correct answers of the student."""
    filter_kwargs = {
        'self_evaluation': 2,
        'user_id': user_id,
        'question__qset__top_qset_id': organization.id,
        'created_at__gte': get_tz_past_datetime(weeks=1),
    }
    return get_model_aggregation(
        askup.models.Answer,
        filter_kwargs,
    )


@zero_on_organization_is_none
def get_student_last_week_incorrect_answers_count(user_id, organization=None):
    """Return last week correct answers of the student."""
    filter_kwargs = {
        'self_evaluation__in': (0, 1),
        'user_id': user_id,
        'question__qset__top_qset_id': organization.id,
        'created_at__gte': get_tz_past_datetime(weeks=1),
    }
    return get_model_aggregation(
        askup.models.Answer,
        filter_kwargs,
    )


def get_model_aggregation(model, filter_kwargs, aggregator_function=Count, aggregated_field='id'):
    """
    Return an aggregation result.

    Example:
        get_model_aggregation(
            organization,
            askup.models.Question,
            {
                'qset_id': 4,
                'user_id': 3,
            },
            Sum,
            'vote_value',
        )

    This example will return the total vote_value of the questions of the user with id = 3 and
    qset_id = 4.
    """
    queryset = model.objects.filter(**filter_kwargs)
    result = queryset.aggregate(aggregator_function(aggregated_field))
    result_key = '{}__{}'.format(aggregated_field, aggregator_function.__name__.lower())
    return result[result_key] or 0


def get_user_organizations_queryset(user_id, viewer_id=None, organization_id=None):
    """
    Return the queryset of sorted by name user organizations.
    """
    user = User.objects.get(pk=user_id)
    is_admin = check_user_has_groups(user, 'admin')
    objects = askup.models.Organization.objects
    queryset = objects.all() if is_admin else objects.filter(users__id=user_id)
    queryset = check_and_apply_organization_filter(queryset, organization_id)

    if viewer_id:
        # If viewer_id is not None, than it's not an admin
        viewer_queryset = askup.models.Organization.objects.filter(users__id=viewer_id)
        viewer_queryset = check_and_apply_organization_filter(viewer_queryset, organization_id)
        queryset = viewer_queryset.intersection(queryset)

    return queryset.order_by('name')


def check_and_apply_organization_filter(queryset, organization_id):
    """
    Apply organization filter to queryset if organization_id is not None.

    If organization_id is not None, it's applying an id filter onto queryset.
    Otherwise - returns the queryset unmodified.
    """
    if organization_id:
        queryset = queryset.filter(id=organization_id)

    return queryset


def get_user_organizations_for_filter(user_id, viewer_id):
    """
    Return user organizations as a list of dictionaries in a sorted manner.
    """
    return list(get_user_organizations_queryset(user_id, viewer_id=viewer_id).values('id', 'name'))


def get_first_user_organization(user_id, viewer_id):
    """
    Check if user is assigned to the specified organization.
    """
    if viewer_id == user_id:
        queryset = get_user_organizations_queryset(user_id)
    else:
        queryset = get_user_organizations_queryset(user_id, viewer_id=viewer_id)

    return queryset.first()


def get_checked_user_organization_by_id(user_id, organization_id, viewer_id):
    """
    Check if an organization is assigned to the specified user and return it on success.

    Return an organization if it belongs to this user and None if it is not.
    """
    queryset = get_user_organizations_queryset(
        user_id, viewer_id=viewer_id, organization_id=organization_id
    )
    return queryset.first()


def get_user_subjects(organization, user_id):
    """
    Return the list of subjects prepared data by the user_id.
    """
    if organization is None:
        return []

    with connection.cursor() as cursor:
        cursor.execute(
            """
                select aqs.id, aqs.name, count(aqu.id) as my_questions_count
                from askup_qset as aqs
                inner join askup_question as aqu on aqu.qset_id = aqs.id
                where aqs.top_qset_id = %s and aqu.user_id = %s
                group by aqs.id
                order by aqs.name
            """,
            (organization.id, user_id)
        )
        return cursor.fetchall()


def get_organization_subjects(organization, user_id):
    """
    Return the list of subjects prepared data by the user_id.
    """
    if organization is None:
        return []

    exists_subquery = askup.models.QsetUserSubscription.objects.filter(qset=OuterRef('pk'), user_id=user_id)
    main_queryset = askup.models.Qset.objects.filter(parent_qset_id=organization.id)
    result = main_queryset.annotate(
        is_subscribed=Exists(exists_subquery)
    ).order_by('-is_subscribed', 'name').values_list('id', 'name', 'is_subscribed')
    return result


def get_real_questions_queryset(qset_id, is_organization_quiz=False):
    """
    Get a questions queryset for the questions type qset (subject) by qset_id.
    """
    if is_organization_quiz:
        return askup.models.Question.objects.filter(qset__top_qset_id=qset_id).order_by('-vote_value', 'text')
    else:
        return askup.models.Question.objects.filter(qset_id=qset_id).order_by('-vote_value', 'text')


def get_tz_past_datetime(**kwargs):
    """
    Get tz-aware datetime value with the timedelta from now to the past.

    In kwargs it receives the parameters that will be passed to the timedelta.
    """
    return timezone.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(**kwargs)
