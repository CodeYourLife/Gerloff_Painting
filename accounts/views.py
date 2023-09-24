import random
from django.shortcuts import render
from employees.models import *
from django.shortcuts import render, redirect
from django.contrib.auth.models import User, auth

def registration(request):
    send_data = {}
    if request.method == 'POST':
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
    #send_data['employees']=Employees.objects.filter(active = True)
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

# def addEmployee(request):
#     send_data = {}
#     #send_data['employees']=Employees.objects.filter(active = True)
#     return render(request, "add_employee.html", send_data)

# def addNewEmployee(request):
#     #
#     if request.method == 'POST':
#         firstName = request.POST['firstName']
#         lastName = request.POST['lastName']
#         user = User.objects.create_user(username=firstName,password=lastName)
#         randomPin = random.randint(1000,9999)
#         gerloffPaintingUser = GPUserAccount.objects.create(user=user, pin=randomPin)
#     return render(request, "add_employee.html", {'user': gerloffPaintingUser})

def login(request):
    if request.method == 'POST':
        if 'register' in request.POST:
            return render(request, 'verify_pin.html')
        else:
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
