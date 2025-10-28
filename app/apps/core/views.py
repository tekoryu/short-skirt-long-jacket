from django.shortcuts import render
from django.contrib.auth.decorators import login_required


def main_page(request):
    """Main page view with top bar and user menu"""
    return render(request, 'core/main.html')


@login_required
def settings(request):
    """Settings page view"""
    return render(request, 'core/settings.html')
