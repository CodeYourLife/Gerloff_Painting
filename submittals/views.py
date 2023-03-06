from django.shortcuts import render
from django.shortcuts import render, redirect
from console.models import *
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
                wallcovering = Wallcovering.objects.filter(job_number = request.POST['select_job'])
                send_data['wallcovering'] = wallcovering
                if Submittals.objects.filter(job_number = request.POST['select_job']).exists():
                    submittal_number = Submittals.objects.filter(job_number = request.POST['select_job']).order_by('submittal_number').last() +1
                else:
                    submittal_number = 1
                send_data['submittal_number'] = submittal_number
    send_data["jobs"]=jobs

    return render(request, "submittals_new.html", send_data)



