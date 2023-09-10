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
    print('hello')
    if request.method == 'POST':
        firstName = request.POST['firstName']
        lastName = request.POST['lastName']
        print('here', firstName, lastName)

