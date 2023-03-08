from django.shortcuts import render
from django.shortcuts import render, redirect
from console.models import *
import json
from django.core.serializers.json import DjangoJSONEncoder
from datetime import date
# Create your views here.
def submittals_page(request, id):
    return redirect('/')


def submittals_home(request):
    return render(request, "submittals_home.html", {})


def submittals_new(request):
    jobs = Jobs.objects.filter(status="Open")
    send_data = {}
    if request.method == 'POST':
        if 'job_select' in request.POST:
            jobs = Jobs.objects.filter(job_number=request.POST['select_job'])
            send_data['job_selected'] = Jobs.objects.get(job_number=request.POST['select_job'])
            if Wallcovering.objects.filter(job_number = request.POST['select_job']).exists():
                wallcovering = Wallcovering.objects.filter(job_number = request.POST['select_job']).values('id','code','vendor__company_name','pattern')
                wallcovering_json = json.dumps(list(wallcovering), cls=DjangoJSONEncoder)
                send_data['wallcovering'] = wallcovering_json
            if Submittals.objects.filter(job_number = request.POST['select_job']).exists():
                submittal = Submittals.objects.filter(job_number = request.POST['select_job']).order_by('submittal_number').last()
                next_submittal_number = int(submittal.submittal_number) + 1
            else:
                next_submittal_number = 1
            send_data['next_submittal_number'] = next_submittal_number
        if 'add_submittal' in request.POST:
            if 'other_item' in request.POST or 'wc_item' in request.POST:
                submittal = Submittals.objects.create(job_number = Jobs.objects.get(job_number=request.POST['select_job']),description = request.POST['description'],submittal_number=request.POST['submittal_number'],date_sent=date.today())
                if 'other_item' in request.POST:
                    items = request.POST.getlist('other_item')
                    quantity = request.POST.getlist('other_quantity')
                    for x in range(0, len(items)):
                        SubmittalItems.objects.create(submittal = submittal, description = items[x], quantity = quantity[x])
                if 'wc_item' in request.POST:
                    items = request.POST.getlist('wc_item')
                    quantity = request.POST.getlist('wc_quantity')
                    wc = request.POST.getlist('select_wc')
                    for x in range(0, len(items)):
                        SubmittalItems.objects.create(submittal = submittal, description = items[x], quantity = quantity[x],wallcovering_id=Wallcovering.objects.get(id=request.POST['select_wc']))


    send_data["jobs"]=jobs

    return render(request, "submittals_new.html", send_data)



