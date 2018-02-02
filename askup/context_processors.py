from .utils.general import extract_notification_from_request


def notifications_processor(request):
    """Context processor that adds a notification's variable to all template contexts."""
    notification = extract_notification_from_request(request)
    return {
        'notification_class': notification[0],
        'notification_text': notification[1],
    }
