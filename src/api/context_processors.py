from .models import Notification

def notifications_context(request):
    """Add notifications to all template contexts"""
    if request.user.is_authenticated:
        notifications = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).order_by('-created_at')[:10]

        notification_count = notifications.count()

        return {
            'user_notifications': notifications,
            'unread_notification_count': notification_count
        }

    return {
        'user_notifications': [],
        'unread_notification_count': 0
    }