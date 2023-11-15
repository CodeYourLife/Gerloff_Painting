import random
from django.shortcuts import render
from employees.models import *
from django.shortcuts import render, redirect
from django.contrib.auth.models import User, auth
from console.misc import Email

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
        employee.email = request.POST['email']
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

def forgotPassword(request):
    return render(request, "forgot_password.html")

def login(request):
    send_data = {}
    if request.method == 'POST':
        if 'register' in request.POST:
            return render(request, 'verify_pin.html')
        elif 'forgot' in request.POST:
            # send email to user
            try:
                username = request.POST['username']
                forgottenUser = User.objects.get(username=username)
                employee = Employees.objects.get(user=forgottenUser.id)
                Email.sendEmail("Forgot Password Alert", f"Someone requested their password. If this is not you, please contact your admin. Go to this page forgot_password.com and use this passcode to reset your password {employee.pin}.", [employee.email], False)
                send_data['message'] = "Email sent to user with their password"
            except Exception as e:
                send_data['message'] = "Unable to send email, check username and try again or contact your admin"
                print('could not send email', e)
            send_data['username'] = request.POST['username']
            send_data['password'] = request.POST['password']
            return render(request, "login.html", send_data)
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
