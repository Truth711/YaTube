from django.shortcuts import render
from http import HTTPStatus


def page_not_found(request, exception):
    return render(request, 'core/404.html',
                  {'path': request.path}, status=HTTPStatus.NOT_FOUND)


def csrf_failure(request, reason=''):
    return render(request, 'core/403.html')


def internal_server_error(request, reason=''):
    return render(request, 'core/500.html')
