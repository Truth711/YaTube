from django.core.paginator import Paginator
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import cache_page
from .models import Post, Group, User, Follow
from .forms import PostForm, CommentForm


PAGINATOR_AMOUNT = 10


def paginator(request, post_list, amount):

    paginator_ = Paginator(post_list, amount)
    page_number = request.GET.get('page')
    page_obj = paginator_.get_page(page_number)
    return page_obj


@cache_page(20, key_prefix='index_page')
def index(request):

    post_list = Post.objects.all()
    page_obj = paginator(request, post_list, PAGINATOR_AMOUNT)
    context = {
        'page_obj': page_obj,
    }
    return render(request, 'posts/index.html', context)


def group_posts(request, slug):

    group = get_object_or_404(Group, slug=slug)
    post_list = group.posts.all()
    page_obj = paginator(request, post_list, PAGINATOR_AMOUNT)
    context = {
        'group': group,
        'page_obj': page_obj,
    }
    return render(request, 'posts/group_list.html', context)


def profile(request, username):

    author = get_object_or_404(User, username=username)
    post_list = author.posts.all()
    page_obj = paginator(request, post_list, PAGINATOR_AMOUNT)
    following = (request.user.is_authenticated and Follow.objects.filter(
        user=request.user,
        author=author
    ).exists())
    context = {
        'following': following,
        'author': author,
        'page_obj': page_obj,
    }
    return render(request, 'posts/profile.html', context)


def post_detail(request, post_id):

    post = get_object_or_404(Post, id=post_id)
    comments = post.comments.select_related('author').all()
    # Стоит ли добавить select_related('author') в index, group_posts, profile?
    # В шаблонах этих страниц используется post.author.get_full_name а в
    # контексте передается только список постов.
    form = CommentForm()
    context = {
        'post': post,
        'comments': comments,
        'form': form,
    }
    return render(request, 'posts/post_detail.html', context)


@login_required
def post_create(request):

    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
    )
    if form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        return redirect('posts:profile', request.user)

    return render(request, 'posts/create_post.html', {'form': form})


@login_required
def post_edit(request, post_id):

    post = get_object_or_404(Post, id=post_id)

    if request.user != post.author:
        return redirect('posts:post_detail', post_id)

    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
        instance=post)
    if form.is_valid():
        form.save()
        return redirect('posts:post_detail', post_id)

    context = {'post': post, 'form': form, 'is_edit': True}

    return render(request, 'posts/create_post.html', context)


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('posts:post_detail', post_id=post_id)


@login_required
def follow_index(request):
    following_set = Follow.objects.filter(user=request.user)
    author_set = [x.author for x in following_set]
    post_list = Post.objects.filter(author__in=author_set)
    page_obj = paginator(request, post_list, PAGINATOR_AMOUNT)
    context = {
        'page_obj': page_obj,
    }
    return render(request, 'posts/follow.html', context)


@login_required
def profile_follow(request, username):
    author = get_object_or_404(User, username=username)
    if author != request.user and not Follow.objects.filter(
            user=request.user, author=author):
        Follow.objects.create(user=request.user, author=author)
    return redirect('posts:profile', username)


@login_required
def profile_unfollow(request, username):
    author = get_object_or_404(User, username=username)
    following = Follow.objects.filter(user=request.user, author=author)
    following.delete()
    return redirect('posts:profile', username)
