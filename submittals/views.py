from django.shortcuts import render
from django.shortcuts import render, redirect
# Create your views here.
def submittals_page(request, id):
    return redirect('/')


def submittals_home(request):
    return render(request, "submittals_home.html", {})


def submittals_new(request):
    return redirect('/')



