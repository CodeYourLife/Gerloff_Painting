import random
from django.shortcuts import render
from employees.models import *
from django.shortcuts import render, redirect
from django.contrib.auth.models import User, auth

def registration(request):
    send_data = {}
    if request.method == 'POST':
        if User.objects.filter(username=request.POST['username']).exists():
            send_data['message'] = "Username already exists"
            send_data['username'] = request.POST['username']
            send_data['password'] = request.POST['password']
            send_data['phonenumber'] = request.POST['phonenumber']
            send_data['email'] = request.POST['email']
            return render(request, "registration.html", send_data)
        user = User.objects.create_user(username=request.POST['username'],
                                        email=request.POST['email'],
                                        password=request.POST['password'])
        employee = Employees.objects.get(id=request.POST['selected_employee'])
        employee.user = user
        employee.phone = request.POST['phonenumber']
        employee.nickname = request.POST['nickname']
        user.first_name = employee.first_name
        user.last_name = employee.last_name
        user.save()
        employee.save()
        return render(request, "login.html", send_data)
    return render(request, "registration.html", send_data)

def verifyPin(request):
    if request.method == 'POST':
        send_data = {}
        if Employees.objects.filter(pin=request.POST['pin']).exists():
            selected_employee = Employees.objects.get(pin=request.POST['pin'])
            send_data['selected_employee'] = selected_employee
            return render(request, "registration.html", send_data)
        else:
            send_data['message'] = "PIN NOT CORRECT"
            return render(request, "verify_pin.html", send_data)

def login(request):
    send_data = {}
    if request.method == 'POST':
        if 'register' in request.POST:
            return render(request, 'verify_pin.html')
        else:
            username = request.POST['username']
            password = request.POST['password']
            try:
                user = auth.authenticate(username=username, password=password)
                if user is not None:
                    auth.login(request, user)
                    return redirect("/")
            except Exception as e:
                print('invalid credentials', e)
            send_data['message'] = "Invalid credentials"
            send_data['username'] = request.POST['username']
            send_data['password'] = request.POST['password']
            return render(request, "login.html", send_data)
    else:
        return render(request, 'login.html')

def logout(request):
    auth.logout(request)
    return redirect("/")
