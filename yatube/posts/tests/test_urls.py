from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from http import HTTPStatus
from django.urls import reverse
from django.core.cache import cache

from ..models import Post, Group

User = get_user_model()


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='author')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
            group=cls.group,
        )

    def setUp(self):
        cache.clear()
        self.guest_client = Client()
        self.user = User.objects.create_user(username='authorized_user')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.author = Client()
        self.author.force_login(PostURLTests.user)

    def test_public_urls_exists_at_desired_location(self):
        """Общедоступные страницы доступны любому пользователю."""
        page_list = [
            '/',
            f'/group/{self.group.slug}/',
            f'/profile/{PostURLTests.user.username}/',
            f'/posts/{self.post.id}/',
        ]
        for page in page_list:
            with self.subTest(page=page):
                response = self.guest_client.get(page)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_non_existing_url_404(self):
        """Запрос к несуществующей странице вернёт ошибку 404."""
        response = self.guest_client.get('/non_existing_url/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_404_uses_correct_template(self):
        """Страница с ошибкой 404 использует соответствующий шаблон."""
        response = self.authorized_client.get('/non_existing_url/')
        self.assertTemplateUsed(response, 'core/404.html')

    def test_create_url_exists_at_desired_location_authorized(self):
        """Страница /create/ доступна авторизованному пользователю."""
        response = self.authorized_client.get('/create/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_post_edit_url_exists_at_desired_location_author(self):
        """Страница /posts/<int:post_id>/edit/ доступна автору поста."""
        response = self.author.get(f'/posts/{self.post.id}/edit/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_create_url_redirect_anonymous_on_login(self):
        """Страница /create/ перенаправит анонимного пользователя
        на страницу логина.
        """
        response = self.guest_client.get('/create/', follow=True)
        self.assertRedirects(response, '/auth/login/?next=/create/')

    def test_post_edit_url_redirect_non_author_on_post_detail(self):
        """Страница /posts/<int:post_id>/edit/ перенаправит пользователя,
        не являющегося автором поста, на страницу /posts/1/.
        """
        response = self.authorized_client.get(
            f'/posts/{self.post.id}/edit/',
            follow=True
        )
        self.assertRedirects(response, f'/posts/{self.post.id}/')

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        url_templates_names = {
            '/': 'posts/index.html',
            f'/group/{self.group.slug}/': 'posts/group_list.html',
            f'/profile/{PostURLTests.user.username}/': 'posts/profile.html',
            f'/posts/{self.post.id}/': 'posts/post_detail.html',
            '/create/': 'posts/create_post.html',
            f'/posts/{self.post.id}/edit/': 'posts/create_post.html',
            '/follow/': 'posts/follow.html',
        }
        for url, template in url_templates_names.items():
            with self.subTest(url=url):
                response = self.author.get(url)
                self.assertTemplateUsed(response, template)

    def test_add_comment_url_exists_at_desired_location_authorized(self):
        """Страница posts/<int:post_id>/comment/ доступна
        авторизованному пользователю.
        """
        form_data = {'text': 'Тестовый комментарий 1', }
        response = self.guest_client.post(
            reverse(
                'posts:add_comment',
                kwargs={'post_id': PostURLTests.post.id}
            ),
            data=form_data,
        )
        self.assertEqual(response.status_code, HTTPStatus.FOUND)

    def test_add_comment_url_redirect_anonymous_on_login(self):
        """Страница posts/<int:post_id>/comment/ перенаправит
        анонимного пользователя на страницу логина.
        """
        form_data = {'text': 'Тестовый комментарий 1', }
        response = self.guest_client.post(
            reverse(
                'posts:add_comment',
                kwargs={'post_id': PostURLTests.post.id}
            ),
            data=form_data,
        )
        self.assertRedirects(response, '/auth/login/?next=/posts/1/comment/')

    def test_login_required_urls_not_available_for_anonymous(self):
        """Страницы comment, follow_index, follow, unfollow недоступны
        для неавторизованного пользователя.
        """
        page_list = [
            f'/posts/{self.post.id}/comment/',
            '/follow/',
            f'/profile/{PostURLTests.user.username}/follow/',
            f'/profile/{PostURLTests.user.username}/unfollow/',
        ]
        for page in page_list:
            with self.subTest(page=page):
                response = self.guest_client.get(page)
                self.assertNotEqual(response.status_code, HTTPStatus.OK)

    def test_login_required_urls_redirects_anonymous_on_login(self):
        """Страницы comment, follow_index, follow, unfollow перенаправляют
        неавторизованного пользователя на страницу логина.
        """
        page_list = [
            f'/posts/{self.post.id}/comment/',
            '/follow/',
            f'/profile/{PostURLTests.user.username}/follow/',
            f'/profile/{PostURLTests.user.username}/unfollow/',
        ]
        for page in page_list:
            with self.subTest(page=page):
                response = self.guest_client.get(page)
                self.assertRedirects(
                    response,
                    f'/auth/login/?next={page}'
                )
