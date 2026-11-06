from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from accounts.permissions import operator_required
from .forms import ArticleForm
from .models import Article, ArticleBookmark
from marketdata.models import Symbol

@operator_required
def article_create(request):
    form = ArticleForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        article = form.save(commit=False)
        article.author = request.user
        choice = form.cleaned_data['publication_choice']
        require_approval = getattr(settings, 'ARTICLE_REQUIRE_ADMIN_APPROVAL', False)
        article.status = Article.Status.DRAFT if choice == 'DRAFT' else (Article.Status.PENDING if require_approval else Article.Status.PUBLISHED)
        if article.status == Article.Status.PUBLISHED:
            article.published_at = timezone.now()
        article.save()
        messages.success(request, 'مطلب به‌صورت پیش‌نویس ذخیره شد.' if article.status == Article.Status.DRAFT else ('مطلب برای تأیید مدیر ارسال شد.' if article.status == Article.Status.PENDING else 'مطلب منتشر شد.'))
        return redirect('article_detail', slug=article.slug)
    return render(request, 'publishing/article_form.html', {'form': form})

def article_list(request):
    qs = Article.objects.filter(status=Article.Status.PUBLISHED).select_related('author', 'symbol')
    symbol = request.GET.get('symbol')
    direction = request.GET.get('direction')
    if symbol:
        qs = qs.filter(symbol__code=symbol.upper())
    if direction in Article.Direction.values:
        qs = qs.filter(direction=direction)
    return render(request, 'publishing/article_list.html', {'articles': qs, 'symbols': Symbol.objects.filter(is_active=True), 'selected_symbol': symbol or '', 'selected_direction': direction or ''})

def article_detail(request, slug):
    article = get_object_or_404(Article.objects.select_related('author', 'symbol'), slug=slug)
    if article.status != Article.Status.PUBLISHED and not (request.user.is_authenticated and (request.user.is_admin_role or request.user == article.author)):
        return redirect('article_list')
    bookmarked = request.user.is_authenticated and ArticleBookmark.objects.filter(user=request.user, article=article).exists()
    return render(request, 'publishing/article_detail.html', {'article': article, 'bookmarked': bookmarked})

@login_required
@require_POST
def article_bookmark(request, pk):
    article = get_object_or_404(Article, pk=pk, status=Article.Status.PUBLISHED)
    bookmark, created = ArticleBookmark.objects.get_or_create(user=request.user, article=article)
    if not created:
        bookmark.delete()
        messages.info(request, 'مطلب از نشان‌شده‌ها حذف شد.')
    else:
        messages.success(request, 'مطلب ذخیره شد.')
    return redirect('article_detail', slug=article.slug)


@operator_required
def operator_articles(request):
    qs = Article.objects.select_related('author', 'symbol')
    if not request.user.is_admin_role:
        qs = qs.filter(author=request.user)
    return render(request, 'publishing/operator_articles.html', {'articles': qs})

@operator_required
def article_edit(request, pk):
    article = get_object_or_404(Article, pk=pk)
    if article.author_id != request.user.pk and not request.user.is_admin_role:
        messages.error(request, 'اجازه ویرایش این مطلب را ندارید.')
        return redirect('operator_articles')
    initial_choice = 'PUBLISH' if article.status in {Article.Status.PUBLISHED, Article.Status.PENDING} else 'DRAFT'
    form = ArticleForm(request.POST or None, request.FILES or None, instance=article, initial={'publication_choice': initial_choice})
    if request.method == 'POST' and form.is_valid():
        article = form.save(commit=False)
        choice = form.cleaned_data['publication_choice']
        if choice == 'DRAFT':
            article.status = Article.Status.DRAFT
            article.published_at = None
        elif settings.ARTICLE_REQUIRE_ADMIN_APPROVAL:
            article.status = Article.Status.PENDING
            article.published_at = None
        else:
            article.status = Article.Status.PUBLISHED
            article.published_at = article.published_at or timezone.now()
        article.save()
        messages.success(request, 'مطلب به‌روزرسانی شد.')
        return redirect('operator_articles')
    return render(request, 'publishing/article_form.html', {'form': form, 'editing': True, 'article': article})

@operator_required
def article_delete(request, pk):
    article = get_object_or_404(Article, pk=pk)
    if article.author_id != request.user.pk and not request.user.is_admin_role:
        messages.error(request, 'اجازه حذف این مطلب را ندارید.')
        return redirect('operator_articles')
    if request.method == 'POST':
        article.delete()
        messages.success(request, 'مطلب حذف شد.')
        return redirect('operator_articles')
    return render(request, 'publishing/article_confirm_delete.html', {'article': article})
