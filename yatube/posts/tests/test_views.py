import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.cache import cache
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django import forms

from ..models import Post, Group

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)
EXPECTED_COMMENTS_NUM = 0
EXPECTED_OBJECTS_NUM = 1
ALL_PAGES = 13
FIRST_PAGE = 10
SECOND_PAGE = 3


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='author')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        image = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00'
            b'\x01\x00\x00\x00\x00\x21\xf9\x04'
            b'\x01\x0a\x00\x01\x00\x2c\x00\x00'
            b'\x00\x00\x01\x00\x01\x00\x00\x02'
            b'\x02\x4c\x01\x00\x3b'
        )
        uploaded = SimpleUploadedFile(
            name='small.jpg',
            content=image,
            content_type='image/image'
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
            group=cls.group,
            image=uploaded,
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        cache.clear()
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(PostPagesTests.user)
        self.another_user = User.objects.create_user(username='another_user')
        self.another_authorized_client = Client()
        self.another_authorized_client.force_login(self.another_user)

    def test_pages_uses_correct_template_and_show_correct_context(self):
        """URL-адрес использует соответствующий шаблон"""
        templates_page_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:group_posts', kwargs={'slug': self.group.slug}):
                'posts/group_list.html',
            reverse('posts:profile',
                    kwargs={'username': self.user.username}
                    ):
                'posts/profile.html',
            reverse('posts:post_detail', kwargs={'post_id': self.post.id}):
                'posts/post_detail.html',
            reverse('posts:post_create'): 'posts/create_post.html',
            reverse('posts:post_edit', kwargs={'post_id': self.post.pk}):
                'posts/create_post.html',
        }
        for reverse_name, template in templates_page_names.items():
            with self.subTest(template=template):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_page_obj_is_as_expected(self):
        """В шаблоны передается ожидаемое количество объектов."""
        reverse_names_list = [
            reverse('posts:index'),
            reverse('posts:group_posts', kwargs={'slug': self.group.slug}),
            reverse('posts:profile', kwargs={'username': self.user.username})
        ]
        for reverse_name in reverse_names_list:
            response = self.authorized_client.get(reverse_name)
            self.assertEqual(
                len(response.context['page_obj']), EXPECTED_OBJECTS_NUM
            )

    def _assert_post_attribs(self, post):
        """Проверка post на соответствие ожиданию."""
        self.assertEqual(post.id, self.post.pk)
        self.assertEqual(post.author, PostPagesTests.user)
        self.assertEqual(post.group, PostPagesTests.group)
        self.assertEqual(post.image, PostPagesTests.post.image)

    def test_index_page_show_correct_context(self):
        """Шаблон index сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:index'))
        post = response.context['page_obj'][0]
        self._assert_post_attribs(post)

    def test_group_posts_page_show_correct_context(self):
        """Шаблон group_list сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:group_posts', kwargs={'slug': self.group.slug})
        )
        post = response.context['page_obj'][0]
        self._assert_post_attribs(post)

        group = response.context['group']
        self.assertEqual(group.title, self.group.title)
        self.assertEqual(group.slug, self.group.slug)
        self.assertEqual(group.description, self.group.description)

    def test_profile_page_show_correct_context(self):
        """Шаблон profile сформирован с правильным контекстом."""
        response = self.another_authorized_client.get(reverse(
            'posts:profile',
            kwargs={'username': PostPagesTests.user.username})
        )
        post = response.context['page_obj'][0]
        self._assert_post_attribs(post)

        author = response.context['author']
        self.assertEqual(author.id, PostPagesTests.user.id)
        self.assertEqual(author.username, PostPagesTests.user.username)

        following = response.context['following']
        self.assertFalse(following)

    def test_post_detail_pages_show_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post.id})
        )
        post = response.context['post']
        self._assert_post_attribs(post)

    def _assert_form_fields(self, response):
        """Проверка form на соответствие ожиданию."""
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context['form'].fields[value]
                self.assertIsInstance(form_field, expected)

    def test_create_post_page_show_correct_context(self):
        """Шаблон create_post сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:post_create'))
        self._assert_form_fields(response)

    def test_edit_post_page_show_correct_context(self):
        """Шаблон create_post сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:post_edit', kwargs={'post_id': self.post.id})
        )
        self._assert_form_fields(response)

    def test_post_appears_on_pages(self):
        """Если при создании поста указать группу, то этот пост появляется
        на страницах из списка reverse_names_list и не появляется в группе,
        отличной от указанной.
        """
        reverse_names_list = [
            reverse('posts:index'),
            reverse('posts:group_posts', kwargs={'slug': self.group.slug}),
            reverse('posts:profile', kwargs={'username': self.user.username})
        ]
        for reverse_name in reverse_names_list:
            response = self.authorized_client.get(reverse_name)
            self.assertEqual(
                len(response.context['page_obj']), EXPECTED_OBJECTS_NUM
            )
        Group.objects.create(
            title='Пустая группа',
            slug='empty-slug',
            description='Пустое описание',
        )
        Post.objects.create(
            author=PostPagesTests.user,
            text='Тестовый пост',
            group=PostPagesTests.group,
        )
        cache.clear()
        for reverse_name in reverse_names_list:
            response = self.authorized_client.get(reverse_name)
            self.assertEqual(
                len(response.context['page_obj']), EXPECTED_OBJECTS_NUM + 1
            )
        response = self.authorized_client.get(
            reverse('posts:group_posts', kwargs={'slug': 'empty-slug'})
        )
        self.assertEqual(len(response.context['page_obj']), 0)

    def test_comment_appears_on_pages(self):
        """Новый комментарий появляется на странице поста."""
        response = self.authorized_client.get(reverse(
                'posts:post_detail',
                kwargs={'post_id': PostPagesTests.post.id}
            ))
        self.assertEqual(
            len(response.context['comments']), EXPECTED_COMMENTS_NUM
        )
        form_data = {'text': 'Тестовый комментарий 1', }
        self.authorized_client.post(reverse(
            'posts:add_comment',
            kwargs={'post_id': PostPagesTests.post.id}
        ),
            data=form_data,)
        response = self.authorized_client.get(reverse(
            'posts:post_detail',
            kwargs={'post_id': PostPagesTests.post.id}
        ))
        self.assertEqual(
            len(response.context['comments']), EXPECTED_COMMENTS_NUM + 1
        )

    def test_cache_index(self):
        """index кэшируется."""
        response1 = self.authorized_client.get(
            reverse('posts:index')).content
        Post.objects.create(
            text='Тестовый текст',
            author=self.user,
            group=self.group
        )
        response2 = self.authorized_client.get(
            reverse('posts:index')).content
        self.assertEqual(response1, response2)
        cache.clear()
        response3 = self.authorized_client.get(
            reverse('posts:index')).content
        self.assertNotEqual(response3, response1)

    def test_follow_and_unfollow_works_correct_for_authorized(self):
        """Авторизованный пользователь может подписаться на
        другого пользователя и отписаться от него.
        """
        self.another_authorized_client.get(reverse(
            'posts:profile_follow',
            kwargs={'username': PostPagesTests.user.username})
        )
        self.assertTrue(
            self.another_user.follower.filter(author=PostPagesTests.user))
        self.another_authorized_client.get(reverse(
            'posts:profile_unfollow',
            kwargs={'username': PostPagesTests.user.username})
        )
        self.assertFalse(
            self.another_user.follower.filter(author=PostPagesTests.user))

    def test_post_appears_on_follow_index_page(self):
        """Новая запись пользователя появляется в ленте тех,
        кто на него подписан и не появляется в ленте тех, кто не подписан.
        """
        self.another_authorized_client.get(reverse(
            'posts:profile_follow',
            kwargs={'username': PostPagesTests.user.username})
        )
        response1 = self.another_authorized_client.get(reverse(
            'posts:follow_index',
        ))
        self.assertIn(PostPagesTests.post, response1.context['page_obj'])
        self.another_authorized_client.get(reverse(
            'posts:profile_unfollow',
            kwargs={'username': PostPagesTests.user.username})
        )
        response2 = self.another_authorized_client.get(reverse(
            'posts:follow_index',
        ))
        self.assertNotIn(PostPagesTests.post, response2.context['page_obj'])


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.guest_user = Client()
        cls.user = User.objects.create_user(username='author')
        cls.group = Group.objects.create(
            title='Тестовый пост',
            description='Тестовое описание',
            slug='test-slug'
        )

    def setUp(self):
        cache.clear()
        bulk_list = []
        for post_temp in range(ALL_PAGES):
            bulk_list.append(Post(
                text=f'text{post_temp}', author=self.user, group=self.group
            ))
        Post.objects.bulk_create(bulk_list)

    def _test_pagination(self, additional_params, expected_count):
        templates_pages_dict = {
            'posts/index.html': reverse(
                'posts:index'
            ) + additional_params,
            'posts/group_list.html': reverse(
                'posts:group_posts',
                kwargs={'slug': self.group.slug}
            ) + additional_params,
            'posts/profile.html': reverse(
                'posts:profile',
                kwargs={'username': self.user}
            ) + additional_params,
        }
        for template, reverse_name in templates_pages_dict.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.client.get(reverse_name)
                self.assertEqual(
                    len(response.context['page_obj']), expected_count
                )

    def test_first_page_ten_records(self):
        self._test_pagination("", FIRST_PAGE)

    def test_second_page_three_records(self):
        self._test_pagination("?page=2", SECOND_PAGE)
