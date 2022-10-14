import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..forms import PostForm, CommentForm
from ..models import Post, Group

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)

User = get_user_model()


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='author')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.author,
            text='Тестовый текст',
            group=cls.group,
        )
        cls.form = PostForm()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.author)

    def test_create_post(self):
        """Валидная форма создает запись в Post."""
        posts_count = Post.objects.count()
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
        form_data = {
            'text': 'Тестовый текст 1',
            'group': PostFormTests.group.id,
            'image': uploaded,
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
        )
        self.assertEqual(Post.objects.count(), posts_count + 1)
        self.assertRedirects(response, reverse(
            'posts:profile',
            kwargs={'username': PostFormTests.author.username}
        ))
        self.assertTrue(Post.objects.filter(
            author=PostFormTests.author,
            text='Тестовый текст 1',
            group=PostFormTests.group.id
        ).exists())

    def test_edit_post(self):
        """Валидная форма, отправленная со страницы редактирования поста
        изменяет запись в базе данных.
        """
        posts_count = Post.objects.count()
        form_data = {
            'text': 'Тестовый текст 2',
        }
        response = self.authorized_client.post(
            reverse('posts:post_edit', args=(PostFormTests.post.id,)),
            data=form_data,
        )
        self.assertRedirects(
            response,
            reverse('posts:post_detail', args=(PostFormTests.post.id,)),
        )
        self.assertEqual(Post.objects.count(), posts_count)
        self.assertTrue(Post.objects.filter(
            id=PostFormTests.post.id,
            author=PostFormTests.author,
            text='Тестовый текст 2',
            group=None,
        ).exists())


class CommentFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='author')
        cls.post = Post.objects.create(
            author=cls.author,
            text='Тестовый текст',
        )
        cls.form = CommentForm()

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.author)

    def test_add_comment(self):
        """Валидная форма, отправленная авторизованным клиентом
         создает комментарий к посту.
         """

        comments_count = self.post.comments.count()
        form_data = {'text': 'Тестовый комментарий 1', }
        response = self.authorized_client.post(
            reverse(
                'posts:add_comment',
                kwargs={'post_id': CommentFormTests.post.id}
            ),
            data=form_data,
        )
        self.assertEqual(self.post.comments.count(), comments_count + 1)
        self.assertRedirects(response, reverse(
            'posts:post_detail',
            kwargs={'post_id': CommentFormTests.post.id}
        ))
        self.assertTrue(self.post.comments.filter(
            post=CommentFormTests.post,
            author=CommentFormTests.author,
            text='Тестовый комментарий 1',
        ).exists())
