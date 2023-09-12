import random
from django.shortcuts import render
from employees.models import *
from django.shortcuts import render

def registration(request):
    send_data = {}
    #send_data['employees']=Employees.objects.filter(active = True)
    return render(request, "registration.html", send_data)

def verifyPin(request):
    send_data = {}
    #send_data['employees']=Employees.objects.filter(active = True)
    return render(request, "verify_pin.html", send_data)

def addEmployee(request):
    send_data = {}
    #send_data['employees']=Employees.objects.filter(active = True)
    return render(request, "add_employee.html", send_data)

def addNewEmployee(request):
    #
    if request.method == 'POST':
        firstName = request.POST['firstName']
        lastName = request.POST['lastName']
        user = User.objects.create_user(username=firstName,password=lastName)
        randomPin = random.randint(1000,9999)
        gerloffPaintingUser = GPUserAccount.objects.create(user=user, pin=randomPin)
    return render(request, "add_employee.html", {'user': gerloffPaintingUser})

