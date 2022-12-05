from django.utils import timezone
from django.views import generic
from .models import Jobs, Clients
from django.contrib.auth.models import User, auth
from django.shortcuts import render, redirect


class IndexView(generic.ListView):
    template_name = 'console/index.html'

    def get_queryset(self):
        return;


class JobListView(generic.ListView):
    template_name = 'console/super_job_list.html'
    context_object_name = 'jobs'

    def get_queryset(self):
        return Jobs.objects.all().order_by('-booked_date')[0:2000]


class OpenItemsView(generic.ListView):
    template_name = 'console/open_items.html'

    def get_queryset(self):
        return;


class ProjectScheduleView(generic.ListView):
    template_name = 'console/project_schedule.html'

    def get_queryset(self):
        return;


class InventoryControlView(generic.ListView):
    template_name = 'console/inventory_control.html'

    def get_queryset(self):
        return;


class WallcoveringView(generic.ListView):
    template_name = 'console/wallcovering.html'

    def get_queryset(self):
        return;


class GoToJobFinderView(generic.ListView):
    template_name = 'console/go_to_job_finder.html'

    def get_queryset(self):
        return;


class BookNewJobView(generic.ListView):
    template_name = 'console/book_new_job.html'
    context_object_name = 'clients'

    def get_queryset(self):
        # return Clients.objects.all().order_by('-company').d[0:2000]
        return Clients.objects.order_by('company').distinct('company')[0:2000]

    context_object_name1 = 'PMs'
    def get_queryset(self):
        # return Clients.objects.all().order_by('-company').d[0:2000]
        return Clients.objects.order_by('company')[0:2000]


# def book_new_job(request):
#     client = Clients.objects.all()
#     return render(request, 'test.html', {'client': client})


def register(request):
    if request.method == 'POST':
        job_number1 = request.POST['job_number']
        job_name1 = request.POST['job_name']

        job= Jobs(id=3,job_number=job_number1, job_name=job_name1)
        job.save();
        response = redirect('/')
        return response

