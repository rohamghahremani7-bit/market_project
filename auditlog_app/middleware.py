from .models import ActivityEvent

class ActivityLogMiddleware:
    """ثبت حداقلی درخواست‌های تغییردهنده؛ داده‌های POST و رمزها هرگز ذخیره نمی‌شوند."""
    SAFE_METHODS = {'GET', 'HEAD', 'OPTIONS'}
    EXCLUDED_PREFIXES = ('/static/', '/media/', '/__debug__/')
    def __init__(self, get_response):
        self.get_response = get_response
    def __call__(self, request):
        response = self.get_response(request)
        if request.method not in self.SAFE_METHODS and not request.path.startswith(self.EXCLUDED_PREFIXES) and response.status_code < 400:
            user = request.user if getattr(request, 'user', None) and request.user.is_authenticated else None
            forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
            ip = forwarded.split(',')[0].strip() if forwarded else request.META.get('REMOTE_ADDR')
            try:
                ActivityEvent.objects.create(user=user, action='HTTP_CHANGE', method=request.method,
                    path=request.path[:500], ip_address=ip or None, status_code=response.status_code,
                    user_agent=request.META.get('HTTP_USER_AGENT', '')[:300])
            except Exception:
                # خطای ثبت گزارش نباید درخواست اصلی را از کار بیندازد.
                pass
        return response
