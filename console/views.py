from django.utils import timezone
from django.views import generic
#from .models import Jobs, Clients, Employees, JobNumbers, Checklist, ClientEmployees, JobNotes
from .models import *
from django.contrib.auth.models import User, auth
from django.shortcuts import render, redirect
from json import dumps
import json
from django.core.serializers.json import DjangoJSONEncoder
from datetime import date
from django.contrib import messages
import os
import os.path

def seperate_test(request):
    fileitem = request.FILES['filename']
    print(fileitem)
    fn = os.path.basename(fileitem.name)
    fn2 = os.path.join("C:/Trinity/",fn)
    open(fn2, 'wb').write(fileitem.file.read())
    return redirect('index')
def index(request):

    if request.method == 'POST':
        print(request.POST)
        directory = "GeeksforGeeks"
        parent_dir = "C:/Trinity/"
        path = os.path.join(parent_dir, directory)
        try:
            os.mkdir(path)
        except OSError as error:
            print(error)

    return render(request, 'index.html')


def warehouse_home(request):
    return render(request, 'warehouse_home.html')



# Create your views here.
def register_user(request):
    send_data = {}
    send_data['employees']=Employees.objects.filter(user = None)
    if request.method == 'POST':
        # first_name = request.POST['first_name']
        # last_name = request.POST['last_name']
        username = request.POST['username']
        password1 = request.POST['password1']
        password2 = request.POST['password2']
        email = request.POST['email']
        if password1==password2:
            if User.objects.filter(username=username).exists():
                messages.info(request, 'Username Taken')
                return redirect('register_user')
            else:
                user = User.objects.create_user(username=username, password=password1, email=email, first_name=Employees.objects.get(id=request.POST['select_employee']).first_name,last_name=Employees.objects.get(id=request.POST['select_employee']).last_name, is_active= False)
                user.save();
                employee = Employees.objects.get(id=request.POST['select_employee'])
                employee.user=user
                employee.save()
                return redirect('login')
        else:
            messages.info(request, 'password not matching...')
            return redirect('register_user')

    else:
        return render(request,'register.html',send_data)

def login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = auth.authenticate(username=username, password=password)
        if user is not None:
            auth.login(request, user)
            return redirect("/")
        else:
            messages.info(request,'invalid credentials')
            return redirect('login')
    else:
        return render(request, 'login.html')

def logout(request):
    auth.logout(request)
    return redirect("/")

