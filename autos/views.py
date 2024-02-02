from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from autos.models import *
from employees.models import *
import json

@login_required(login_url='/accounts/login')
def autos_home(request):
    vehicleNotes = VehicleNotes.objects.all()
    notes = []
    for vehicleNote in vehicleNotes:
        d = vehicleNote.date.strftime('%m/%d/%Y')
        n = vehicleNote.note
        u = vehicleNote.user.first_name + ' ' + vehicleNote.user.last_name
        v = vehicleNote.vehicle.id
        notes.append({'date': d, 'note': n, 'name': u, 'id': v})
    send_data = {'vehicles': Vehicle.objects.all(),
                 'maintenance': VehicleMaintenance.objects.all(),
                 'requiredMaintenance': RequiredMaintenance.objects.all(),
                 'vehicleNotes': notes,
                 'employees': Employees.objects.all()}
    if request.method == 'POST':
        if "notes" in request.POST:
            vehicle = Vehicle.objects.get(id=int(request.POST['vehicleId']))
            try:
                VehicleNotes.objects.create(vehicle=vehicle,
                                            user=request.user,
                                            note=request.POST['notes'])
            except Exception as e:
                print('unable to save vehicle notes', e)
        else:
            employee = Employees.objects.get(id=int(request.POST['driver']))
            try:
                vehicle = Vehicle.objects.get(vin_number=request.POST['vin'])
                vehicle.current_driver = employee
                vehicle.vin_number = request.POST['vin']
                vehicle.date_purchased = request.POST['datePurchased']
                vehicle.mileage = request.POST['mileage']
                vehicle.save()
            except:
                Vehicle.objects.create(current_driver= employee,
                                     vin_number=request.POST['vin'],
                                     date_purchased=request.POST['datePurchased'],
                                     mileage=request.POST['mileage'])

    return render(request, "autos_home.html", send_data)
