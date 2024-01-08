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
        try:
            vehicle = Vehicle.objects.get(vin_number=request.POST['vin'])
            vehicle.current_driver = employee
            vehicle.vin_number = request.POST['vin']
            vehicle.date_purchased = request.POST['datePurchased']
            vehicle.mileage = request.POST['mileage']
            vehicle.notes = request.POST['notes']
            vehicle.save()
        except:
            Vehicle.objects.create(current_driver= employee,
                                 vin_number=request.POST['vin'],
                                 date_purchased=request.POST['datePurchased'],
                                 mileage=request.POST['mileage'],
                                 notes=request.POST['notes'])

    return render(request, "autos_home.html", send_data)
