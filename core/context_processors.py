def site_globals(request):
    unread_notifications = 0
    if request.user.is_authenticated:
        unread_notifications = request.user.notifications.filter(is_read=False).count()
    return {"unread_notifications": unread_notifications}
