from .models import ActivityLog

ACTION_VERBS = {
    "created": "enviou",
    "updated": "editou",
    "finalized": "finalizou",
}


def log_activity(request, directorate, action_type, resource_type, resource_name, url=None):
    profile = getattr(request.user, "profile", None)
    user_name = profile.display_name if profile else (request.user.get_short_name() or request.user.username)
    ActivityLog.objects.create(
        user_id=request.user.pk,
        user_name=user_name,
        directorate=directorate,
        directorate_name=directorate.name if directorate else "",
        action_type=action_type,
        resource_type=resource_type,
        resource_name=resource_name,
        details={"url": url} if url else {},
    )
