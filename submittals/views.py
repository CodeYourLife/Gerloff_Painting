from django.shortcuts import render
from django.shortcuts import render, redirect
from console.models import *
import json
from django.core.serializers.json import DjangoJSONEncoder
from datetime import date
# Create your views here.

def submittals_item_close(request,id):
    item = SubmittalItems.objects.get(id=id)
    item.is_closed = True
    item.save()
    return redirect('submittals_page', id=item.submittal.id)

def submittals_page(request, id):
    selected_submittal = Submittals.objects.get(id=id)
    if request.method == 'POST':
        if 'approved' in request.POST:
            selected_submittal.is_closed = True
            selected_submittal.status = "Approved"
            selected_submittal.save()
            SubmittalNotes.objects.create(submittal=selected_submittal, date=date.today(), user=request.user.first_name,
                                          note="Approved")
        if 'comments' in request.POST:
            selected_submittal.is_closed = True
            selected_submittal.status = "See Comments"
            selected_submittal.save()
            SubmittalNotes.objects.create(submittal=selected_submittal, date=date.today(), user=request.user.first_name,
                                          note="Returned. See Comments")
        if 'main_note_add' in request.POST:
            SubmittalNotes.objects.create(submittal=selected_submittal, date=date.today(), user=request.user.first_name,
                                          note=request.POST['new_note'])
        for x in request.POST:
            if x[0:4] == 'note':
                print(x[0:4])
                print(x[4:len(x)])
                item_number = x[4:len(x)]
                selected_item = SubmittalItems.objects.get(id=item_number)
                selected_item.notes = request.POST['new_note'+x[4:len(x)]]
                selected_item.save()
    selected_job = selected_submittal.job_number
    send_data = {}
    send_data['notes']=SubmittalNotes.objects.filter(submittal=selected_submittal)
    send_data['selected_submittal']=selected_submittal
    send_data['selected_job'] =selected_job
    send_data['items'] = SubmittalItems.objects.filter(submittal=selected_submittal)
    send_data['job_submittals'] = Submittals.objects.filter(job_number = selected_job.job_number)
    if not SubmittalItems.objects.filter(submittal=selected_submittal,is_closed = False).exists():
        send_data['still_open']= True
    return render(request, "submittals_page.html", send_data)


def submittals_home(request):
    send_data = {}
    send_data['submittals'] = Submittals.objects.filter(job_number__status = "Open").order_by('job_number','submittal_number')
    return render(request, "submittals_home.html", send_data)


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
                SubmittalNotes.objects.create(submittal=submittal, date = date.today(),user = request.user.first_name,note ="Sent! - " + request.POST['new_note'])
                if 'other_item' in request.POST:
                    items = request.POST.getlist('other_item')
                    quantity = request.POST.getlist('other_quantity')
                    notes = request.POST.getlist('other_note')
                    for x in range(0, len(items)):
                        SubmittalItems.objects.create(submittal = submittal, description = items[x], quantity = quantity[x],notes = notes[x])
                if 'wc_item' in request.POST:
                    items = request.POST.getlist('wc_item')
                    quantity = request.POST.getlist('wc_quantity')
                    wc = request.POST.getlist('select_wc')
                    notes = request.POST.getlist('wc_note')
                    for x in range(0, len(items)):
                        SubmittalItems.objects.create(submittal = submittal, description = items[x], quantity = quantity[x],wallcovering_id=Wallcovering.objects.get(id=request.POST['select_wc']),notes = notes[x])


    send_data["jobs"]=jobs

    return render(request, "submittals_new.html", send_data)



