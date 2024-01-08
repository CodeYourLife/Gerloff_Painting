from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from autos.models import *
from employees.models import *

@login_required(login_url='/accounts/login')
def autos_home(request):
    send_data = {'vehicles': Vehicle.objects.all(),
                 'maintenance': VehicleMaintenance.objects.all(),
                 'requiredMaintenance': RequiredMaintenance.objects.all(),
                 'vehicleNotes': VehicleNotes.objects.all(),
                 'employees': Employees.objects.all()}
    if request.method == 'POST':
        employee = Employees.objects.get(id=int(request.POST['driver']))
        Vehicle.objects.create(current_driver= employee,
                             vin_number=request.POST['vin'],
                             date_purchased=request.POST['datePurchased'],
                             mileage=request.POST['mileage'],
                             notes=request.POST['notes'])
    if request.method == 'PUT':
        print('update an auto. in progress')
    return render(request, "autos_home.html", send_data)
