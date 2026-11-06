from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from .forms import RegisterForm, ProfileForm, RoleForm
from .models import User
from .permissions import admin_required, operator_required
from publishing.models import Article, ArticleBookmark
from analyses.models import AnalysisRequest, AnalysisBookmark
from marketdata.models import Symbol

def home(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    articles = Article.objects.filter(status=Article.Status.PUBLISHED).select_related('author', 'symbol')[:4]
    analyses = AnalysisRequest.objects.filter(status=AnalysisRequest.Status.PUBLISHED).select_related('symbol', 'created_by')[:3]
    return render(request, 'home.html', {'articles': articles, 'analyses': analyses})

def register(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    form = RegisterForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save(commit=False)
        user.role = User.Role.USER  # نقش اپراتور از فرم عمومی قابل انتخاب نیست.
        user.save()
        login(request, user)
        messages.success(request, 'حساب کاربری شما ساخته شد.')
        return redirect('dashboard')
    return render(request, 'accounts/register.html', {'form': form})

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    error = ''
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user is not None and user.is_active:
            login(request, user)
            next_url = request.GET.get('next', '')
            if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
                return redirect(next_url)
            return redirect('dashboard')
        error = 'نام کاربری یا رمز عبور نادرست است، یا حساب غیرفعال شده است.'
    return render(request, 'accounts/login.html', {'error': error})

@login_required
@require_POST
def logout_view(request):
    logout(request)
    messages.info(request, 'از حساب خارج شدید.')
    return redirect('home')

@login_required
def profile(request):
    form = ProfileForm(request.POST or None, instance=request.user)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'پروفایل ذخیره شد.')
        return redirect('profile')
    return render(request, 'accounts/profile.html', {'form': form})

@login_required
def dashboard(request):
    context = {
        'published_articles': Article.objects.filter(status=Article.Status.PUBLISHED).count(),
        'published_analyses': AnalysisRequest.objects.filter(status=AnalysisRequest.Status.PUBLISHED).count(),
        'symbols_count': Symbol.objects.filter(is_active=True).count(),
        'recent_articles': Article.objects.filter(status=Article.Status.PUBLISHED).select_related('symbol')[:5],
        'recent_analyses': AnalysisRequest.objects.filter(status=AnalysisRequest.Status.PUBLISHED).select_related('symbol')[:5],
    }
    if request.user.is_operator:
        context.update({
            'my_drafts': Article.objects.filter(author=request.user, status__in=[Article.Status.DRAFT, Article.Status.PENDING]).count(),
            'my_analyses': AnalysisRequest.objects.filter(created_by=request.user).count(),
            'pending_reviews': AnalysisRequest.objects.filter(status=AnalysisRequest.Status.PENDING_REVIEW).count(),
        })
    return render(request, 'accounts/dashboard.html', context)

@operator_required
def operator_dashboard(request):
    return render(request, 'accounts/operator_dashboard.html', {
        'my_articles': Article.objects.filter(author=request.user).count(),
        'my_analyses': AnalysisRequest.objects.filter(created_by=request.user).count(),
        'pending': AnalysisRequest.objects.filter(status=AnalysisRequest.Status.PENDING_REVIEW).count(),
        'recent_activity': AnalysisRequest.objects.filter(created_by=request.user).select_related('symbol')[:5],
    })

@admin_required
def manage_users(request):
    users = User.objects.all().order_by('-date_joined')
    if request.method == 'POST':
        target = get_object_or_404(User, pk=request.POST.get('user_id'))
        if target.pk == request.user.pk:
            messages.error(request, 'نقش یا وضعیت حساب خودتان را از این صفحه تغییر ندهید.')
            return redirect('manage_users')
        form = RoleForm(request.POST, instance=target)
        if form.is_valid():
            form.save()
            messages.success(request, f'دسترسی {target.username} به‌روزرسانی شد.')
            return redirect('manage_users')
        messages.error(request, 'اطلاعات ارسالی معتبر نیست.')
    rows = [{'user': u, 'form': RoleForm(instance=u)} for u in users]
    return render(request, 'accounts/manage_users.html', {'rows': rows})


@login_required
def saved_items(request):
    article_items = ArticleBookmark.objects.filter(user=request.user).select_related('article', 'article__symbol')
    analysis_items = AnalysisBookmark.objects.filter(user=request.user).select_related('analysis', 'analysis__symbol')
    return render(request, 'accounts/saved_items.html', {'article_items': article_items, 'analysis_items': analysis_items})
