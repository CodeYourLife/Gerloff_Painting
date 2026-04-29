from console.misc import createfolder, getFilesOrFolders, create_shortcut
from datetime import date
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Max, Q, Prefetch
from django.http import FileResponse, Http404
from django.db.models import Prefetch
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import get_template
from django.utils import timezone
from jobs.models import Jobs
from employees.models import Employees
from .models import *
from xhtml2pdf import pisa
from wallcovering.models import Wallcovering
import os

@login_required(login_url='/accounts/login')
#THIS IS NOT USED RIGHT NOW I DONT THINK
def submittals_item_close(request, id):
    item = SubmittalItems.objects.get(id=id)
    item.is_closed = True
    item.save()
    return redirect('submittals_page', id=item.submittal.id)


@login_required(login_url='/accounts/login')
#THIS IS NOT USED RIGHT NOW I DONT THINK
def submittals_page(request, id):
    selected_submittal = Submittals.objects.get(id=id)
    if request.method == 'POST':
        if 'approved' in request.POST:
            selected_submittal.is_closed = True
            selected_submittal.status = "Approved"
            selected_submittal.save()
            SubmittalNotes.objects.create(submittal=selected_submittal, date=date.today(), user=Employees.objects.get(user=request.user),
                                          note="Approved")
        if 'comments' in request.POST:
            selected_submittal.is_closed = True
            selected_submittal.status = "See Comments"
            selected_submittal.save()
            SubmittalNotes.objects.create(submittal=selected_submittal, date=date.today(), user=Employees.objects.get(user=request.user),
                                          note="Returned. See Comments")
        if 'main_note_add' in request.POST:
            SubmittalNotes.objects.create(submittal=selected_submittal, date=date.today(), user=Employees.objects.get(user=request.user),
                                          note=request.POST['new_note'])
        for x in request.POST:
            if x[0:4] == 'note':

                item_number = x[4:len(x)]
                selected_item = SubmittalItems.objects.get(id=item_number)
                selected_item.notes = request.POST['new_note' + x[4:len(x)]]
                selected_item.save()
    selected_job = selected_submittal.job_number
    send_data = {}
    send_data['notes'] = SubmittalNotes.objects.filter(submittal=selected_submittal)
    send_data['selected_submittal'] = selected_submittal
    send_data['selected_job'] = selected_job
    send_data['items'] = SubmittalItems.objects.filter(submittal=selected_submittal)
    send_data['job_submittals'] = Submittals.objects.filter(job_number=selected_job.job_number)
    if not SubmittalItems.objects.filter(submittal=selected_submittal, is_closed=False).exists():
        send_data['still_open'] = True
    return render(request, "submittals_page.html", send_data)


@login_required(login_url='/accounts/login')
def submittals_home(request):
    send_data = {}
    if request.method == 'POST' and 'add_pending_item' in request.POST:
        description = request.POST.get('pending_description', '').strip()
        notes = request.POST.get('pending_notes', '').strip()
        job_id = request.POST.get('pending_job', '').strip()

        selected_job = Jobs.objects.filter(job_number=job_id, is_closed=False).first()

        if not selected_job:
            messages.error(request, "Please select an open job.")
            return redirect('submittals_home')

        if not description:
            messages.error(request, "Description is required.")
            return redirect('submittals_home')

        item = SubmittalItems.objects.create(
            job_number=selected_job,
            description=description,
            notes=notes,
        )

        if Employees.objects.filter(user=request.user).exists():
            employee = Employees.objects.get(user=request.user)
            SubmittalItemNotes.objects.create(
                submittal=None,
                submittalitem=item,
                date=timezone.now().date(),
                user=employee,
                note="Pending submittal item created. " + notes
            )


    show_closed = request.GET.get('show_closed') == 'on'

    submittals = Submittals.objects.filter(
        job_number__is_closed="False"
    ).order_by('job_number', 'submittal_number')

    if not show_closed:
        submittals = [x for x in submittals if x.status() == "OPEN"]
    else:
        submittals = list(submittals)

    send_data['submittals'] = submittals
    send_data['show_closed'] = show_closed

    pending_items = SubmittalItems.objects.filter(
        Q(submittalapprovals__isnull=True) |
        Q(submittalapprovals__submittal__isnull=True),
        job_number__is_closed=False,
        is_no_longer_used=False,
    ).select_related(
        'job_number',
    ).prefetch_related(
        Prefetch(
            'submittalapprovals_set',
            queryset=SubmittalApprovals.objects.select_related('submittal').order_by('-id'),
            to_attr='all_approvals'
        )
    ).distinct().order_by(
        'job_number',
        'description',
    )

    pending_item_rows = []

    for item in pending_items:
        combined_notes = []

        if item.notes:
            combined_notes.append(item.notes)

        latest_approval_note = None
        if hasattr(item, 'all_approvals'):
            for approval in item.all_approvals:
                if approval.notes:
                    if approval.submittal:
                        latest_approval_note = f"Submittal {approval.submittal.submittal_number}: {approval.notes}"
                    else:
                        latest_approval_note = approval.notes
                    break

        if latest_approval_note:
            combined_notes.append(latest_approval_note)

        pending_item_rows.append({
            'item': item,
            'combined_notes': " | ".join(combined_notes)
        })

    send_data['pending_item_rows'] = pending_item_rows

    send_data['open_jobs'] = Jobs.objects.filter(
        is_closed=False
    ).order_by('job_name')

    return render(request, "submittals_home.html", send_data)


@login_required(login_url='/accounts/login')
def submittals_new(request, job_number):
    job = get_object_or_404(Jobs, job_number=job_number)

    max_number = Submittals.objects.filter(job_number=job).aggregate(
        Max('submittal_number')
    )['submittal_number__max']
    next_submittal_number = 1 if max_number is None else max_number + 1

    #wallcoverings = Wallcovering.objects.all().order_by('pattern')
    employee = Employees.objects.filter(user=request.user).first()

    available_items_without_approvals = SubmittalItems.objects.filter(
        job_number=job,
        is_no_longer_used=False,
        submittalapprovals__isnull=True
    ).order_by('description')

    available_unlinked_approvals = SubmittalApprovals.objects.filter(
        submittal__isnull=True,
        submittalitem__job_number=job,
        submittalitem__is_no_longer_used=False
    ).select_related('submittalitem').order_by('submittalitem__description')

    if request.method == 'POST':
        description = request.POST.get('description', '').strip()
        item_descriptions = request.POST.getlist('item_description')
        item_notes = request.POST.getlist('item_notes')
        item_quantities = request.POST.getlist('item_quantity')
        #item_wallcoverings = request.POST.getlist('item_wallcovering')
        selected_item_ids = request.POST.getlist('existing_item_ids')
        selected_unlinked_approval_ids = request.POST.getlist('existing_unlinked_approval_ids')

        if not description:
            messages.error(request, "Please enter a submittal description.")
            return render(request, 'submittals/submittals_new.html', {
                'job': job,
                'next_submittal_number': next_submittal_number,
            })

        submittal = Submittals.objects.create(
            job_number=job,
            description=description,
            submittal_number=next_submittal_number,
        )
        if employee:
            SubmittalNotes.objects.create(
                submittal=submittal,
                date=timezone.now().date(),
                user=employee,
                note=f"New submittal {submittal.submittal_number} created"
            )
        folder_name = f"{submittal.job_number.job_number} {submittal.submittal_number}"
        base_path = f"submittals/{folder_name}"

        createfolder(base_path)
        createfolder(f"{base_path}/Sent to GC")
        createfolder(f"{base_path}/Approval Documents")
        items_created = 0
        # ===================================
        # CASE 1: EXISTING ITEMS SELECTED
        # ===================================
        if selected_item_ids or selected_unlinked_approval_ids:

            # ---- Items with NO approvals yet ----
            for item_id in selected_item_ids:
                item = SubmittalItems.objects.filter(
                    id=item_id,
                    job_number=job
                ).first()

                if item:
                    SubmittalApprovals.objects.create(
                        submittal=submittal,
                        submittalitem=item,
                        is_approved=None,
                        notes='',
                        quantity=0,
                        date_reviewed=None,
                    )
                    if employee:
                        SubmittalItemNotes.objects.create(
                            submittal=submittal,
                            submittalitem=item,
                            date=timezone.now().date(),
                            user=employee,
                            note=f"New submittal {submittal.submittal_number} created"
                        )

            # ---- Existing approvals NOT yet linked ----
            for approval_id in selected_unlinked_approval_ids:
                approval = SubmittalApprovals.objects.filter(
                    id=approval_id,
                    submittal__isnull=True,
                    submittalitem__job_number=job
                ).first()

                if approval:
                    approval.submittal = submittal
                    approval.save()
                    if employee:
                        SubmittalItemNotes.objects.create(
                            submittal=submittal,
                            submittalitem=approval.submittalitem,
                            date=timezone.now().date(),
                            user=employee,
                            note=f"New submittal {submittal.submittal_number} created"
                        )
        else:
            for i in range(len(item_descriptions)):
                item_description = item_descriptions[i].strip() if i < len(item_descriptions) else ''
                item_note = item_notes[i].strip() if i < len(item_notes) else ''
                item_quantity_raw = item_quantities[i].strip() if i < len(item_quantities) else ''
                #item_wallcovering_id = item_wallcoverings[i].strip() if i < len(item_wallcoverings) else ''

                if not item_description:
                    continue

                #wallcovering_obj = None
                # if item_wallcovering_id:
                #     wallcovering_obj = Wallcovering.objects.filter(id=item_wallcovering_id).first()

                try:
                    quantity = int(item_quantity_raw) if item_quantity_raw else 0
                except ValueError:
                    quantity = 0

                submittal_item = SubmittalItems.objects.create(
                    description=item_description,
                    notes=item_note,
                    job_number=submittal.job_number,
                )

                approval = SubmittalApprovals.objects.create(
                    submittal=submittal,
                    submittalitem=submittal_item,
                    quantity=quantity,
                    is_approved=None,
                    date_reviewed=None,
                    notes='',
                )

                if employee:
                    SubmittalItemNotes.objects.create(
                        submittal=submittal,
                        submittalitem=submittal_item,
                        date=timezone.now().date(),
                        user=employee,
                        note=f"New submittal {submittal.submittal_number} created"
                    )

                items_created += 1

            # if items_created == 0:
            #     submittal.delete()
            #     messages.error(request, "Please add at least one submittal item.")
            #     return render(request, 'submittals_new.html', {
            #         'job': job,
            #         'next_submittal_number': next_submittal_number,
            #         'wallcoverings': wallcoverings,
            #     })

            # if employee:
            #     SubmittalNotes.objects.create(
            #         submittal=submittal,
            #         date=timezone.now().date(),
            #         user=employee,
            #         note=f"New submittal {submittal.submittal_number} created"
            #     )

        messages.success(request, "Submittal created successfully.")
        return redirect('submittal_send', submittal.id)

    return render(request, 'submittals_new.html', {
        'job': job,
        'next_submittal_number': next_submittal_number,
        'available_items_without_approvals':available_items_without_approvals,
        'available_unlinked_approvals':available_unlinked_approvals
    })


@login_required(login_url='/accounts/login')
def submittals_new_selectjob(request):
    if request.method == 'POST':
        job_number = request.POST.get('select_job')
        return redirect('submittals_new', job_number=job_number)
    jobs = Jobs.objects.filter(is_closed=False)
    send_data = {}
    send_data["jobs"] = jobs
    return render(request, "submittals_new_selectjob.html", send_data)



@login_required(login_url='/accounts/login')
def submittal_send(request, submittal_id):
    submittal = get_object_or_404(Submittals, id=submittal_id)
    job = submittal.job_number

    approvals = SubmittalApprovals.objects.filter(
        submittal=submittal
    ).select_related(
        'submittalitem',
        'submittalitem__job_number',
        'submittal',
        'submittal__job_number',
    ).order_by('id')

    item_ids = approvals.values_list('submittalitem_id', flat=True)
    items = SubmittalItems.objects.filter(
        id__in=item_ids
    ).select_related('job_number').order_by('id')

    notes = list(
        SubmittalNotes.objects.filter(submittal=submittal).order_by('id')
    )

    folder_name = f"{job.job_number} {submittal.submittal_number}"
    main_folder_path = os.path.join(settings.MEDIA_ROOT, "submittals", folder_name)
    sent_to_gc_path = os.path.join(main_folder_path, "Sent to GC")
    approval_docs_path = os.path.join(main_folder_path, "Approval Documents")

    main_folder_path2 = rf"\\gp-webserver\trinity\submittals\{job.job_number} {submittal.submittal_number}"
    sent_to_gc_path2 = rf"\\gp-webserver\trinity\submittals\{job.job_number} {submittal.submittal_number}\Sent to GC"
    approval_docs_path2 = rf"\\gp-webserver\trinity\submittals\{job.job_number} {submittal.submittal_number}\Approval Documents"
    os.makedirs(main_folder_path, exist_ok=True)
    os.makedirs(sent_to_gc_path, exist_ok=True)
    os.makedirs(approval_docs_path, exist_ok=True)

    mc_folder_path = None
    if submittal.originated_in_management_console:
        mc_folder_path = (
            r"\\gp2022\company\jobs\open jobs\{job_number} {job_name}\Misc Project Documents\Submittals, Materials\Submittal {submittal_number}"
        ).format(
            job_number=job.job_number,
            job_name=job.job_name,
            submittal_number=submittal.submittal_number,
        )

    base_filename = f"Submittal {submittal.submittal_number} Transmittal"

    def safe_listdir(path, exclude_subfolders=False):
        if not os.path.exists(path):
            return []
        try:
            items_in_dir = sorted(os.listdir(path))
            if exclude_subfolders:
                return [
                    x for x in items_in_dir
                    if os.path.isfile(os.path.join(path, x))
                ]
            return items_in_dir
        except OSError:
            return []

    main_files = safe_listdir(main_folder_path, exclude_subfolders=True)
    sent_to_gc_files = safe_listdir(sent_to_gc_path)
    approval_docs_files = safe_listdir(approval_docs_path)

    employee = Employees.objects.filter(user=request.user).first()

    transmittal_exists = False
    for file in sent_to_gc_files:
        if file.startswith(base_filename) and file.lower().endswith(".pdf"):
            transmittal_exists = True
            break

    if request.method == 'POST':
        # =========================
        # DELETE ROW
        # =========================
        if 'delete_row' in request.POST:
            item_id = request.POST.get('item_id')
            approval_id = request.POST.get('approval_id')

            item = get_object_or_404(
                SubmittalItems,
                id=item_id,
                job_number=job,
            )
            approval = get_object_or_404(
                SubmittalApprovals,
                id=approval_id,
                submittal=submittal,
                submittalitem=item,
            )

            other_approvals_exist = SubmittalApprovals.objects.filter(
                submittalitem=item
            ).exclude(
                id=approval.id
            ).exists()

            if other_approvals_exist:
                approval.delete()

                if employee:
                    SubmittalNotes.objects.create(
                        submittal=submittal,
                        date=timezone.now().date(),
                        user=employee,
                        note=f"Removed item from submittal: {item.description}"
                    )
            else:
                item_description = item.description
                approval.delete()
                item.delete()

                if employee:
                    SubmittalNotes.objects.create(
                        submittal=submittal,
                        date=timezone.now().date(),
                        user=employee,
                        note=f"Deleted item: {item_description}"
                    )

            messages.success(request, "Row deleted.")
            return redirect('submittal_send', submittal.id)
        # =========================
        # ADD NEW ROW
        # =========================
        if 'add_submittal_row' in request.POST:
            new_item = SubmittalItems.objects.create(
                job_number=job,
                description='',
                notes='',
            )

            new_approval = SubmittalApprovals.objects.create(
                submittal=submittal,
                submittalitem=new_item,
                is_approved=None,
                notes='',
                quantity=0,
                date_reviewed=None,
            )

            request.session['new_row_id'] = new_approval.id

            if employee:
                SubmittalNotes.objects.create(
                    submittal=submittal,
                    date=timezone.now().date(),
                    user=employee,
                    note=f"Added new item {new_item.description} to submittal {submittal.submittal_number}"
                )

            messages.success(request, "New row added.")
            return redirect('submittal_send', submittal.id)

        # =========================
        # SAVE / UPDATE ROW
        # =========================
        if 'save_row' in request.POST:
            item_id = request.POST.get('item_id')
            approval_id = request.POST.get('approval_id')

            item = get_object_or_404(
                SubmittalItems,
                id=item_id,
                job_number=job,
            )
            approval = get_object_or_404(
                SubmittalApprovals,
                id=approval_id,
                submittal=submittal,
                submittalitem=item,
            )

            old_is_approved = approval.is_approved
            old_notes = approval.notes or ''

            item.description = request.POST.get('item_description', '').strip()
            item.notes = request.POST.get('item_notes', '').strip()
            item.job_number = job
            item.save()

            qty_raw = request.POST.get('approval_quantity', '').strip()
            try:
                approval.quantity = int(qty_raw) if qty_raw else 0
            except ValueError:
                approval.quantity = 0

            approval.notes = request.POST.get('approval_notes', '').strip()

            is_approved_checked = request.POST.get('is_approved') == 'true'
            is_rejected_checked = request.POST.get('is_rejected') == 'true'
            reject_action = request.POST.get('reject_action', '').strip()

            if is_approved_checked and not is_rejected_checked:
                approval.is_approved = True
                approval.date_reviewed = timezone.now().date()
            elif is_rejected_checked and not is_approved_checked:
                approval.is_approved = False
                approval.date_reviewed = timezone.now().date()
            else:
                approval.is_approved = None

            approval.save()

            note_parts = []

            if approval.is_approved != old_is_approved:
                if approval.is_approved is True:
                    note_parts.append("Approval status changed to Approved")
                elif approval.is_approved is False:
                    note_parts.append("Approval status changed to Rejected")
                else:
                    note_parts.append("Approval status changed to Pending")

            if (approval.notes or '') != old_notes:
                note_parts.append("Approval notes updated- " + approval.notes)

            if note_parts and employee:
                SubmittalItemNotes.objects.create(
                    submittal=submittal,
                    submittalitem=item,
                    date=timezone.now().date(),
                    user=employee,
                    note=". ".join(note_parts)
                )

            if reject_action == 'additional_required':
                SubmittalApprovals.objects.create(
                    submittal=None,
                    submittalitem=item,
                    is_approved=None,
                    notes='Rejected in submittal ' + str(submittal.submittal_number),
                    quantity=approval.quantity,
                    date_reviewed=None,
                )

                if employee:
                    SubmittalNotes.objects.create(
                        submittal=submittal,
                        date=timezone.now().date(),
                        user=employee,
                        note="New pending submittal item created for " + str(item.description),
                    )

            elif reject_action == 'no_longer_needed':
                item.is_no_longer_used = True
                item.save()

                if employee:
                    SubmittalItemNotes.objects.create(
                        submittal=submittal,
                        submittalitem=item,
                        date=timezone.now().date(),
                        user=employee,
                        note="Rejected - item no longer needed on this job"
                    )
                    SubmittalNotes.objects.create(
                        submittal=submittal,
                        date=timezone.now().date(),
                        user=employee,
                        note="Item no longer needed on this job: " + str(item.description),
                    )

            messages.success(request, "Row updated.")
            return redirect('submittal_send', submittal.id)

        # =========================
        # OPEN FILES
        # =========================
        if 'selected_main_file' in request.POST:
            filename = os.path.basename(request.POST.get('selected_main_file', '').strip())
            file_path = os.path.join(main_folder_path, filename)

            if os.path.exists(file_path) and os.path.isfile(file_path):
                return FileResponse(open(file_path, 'rb'), as_attachment=False)

            messages.error(request, "File not found.")
            return redirect('submittal_send', submittal.id)

        if 'selected_sent_to_gc_file' in request.POST:
            filename = os.path.basename(request.POST.get('selected_sent_to_gc_file', '').strip())
            file_path = os.path.join(sent_to_gc_path, filename)

            if os.path.exists(file_path) and os.path.isfile(file_path):
                return FileResponse(open(file_path, 'rb'), as_attachment=False)

            messages.error(request, "File not found.")
            return redirect('submittal_send', submittal.id)

        if 'selected_approval_file' in request.POST:
            filename = os.path.basename(request.POST.get('selected_approval_file', '').strip())
            file_path = os.path.join(approval_docs_path, filename)

            if os.path.exists(file_path) and os.path.isfile(file_path):
                return FileResponse(open(file_path, 'rb'), as_attachment=False)

            messages.error(request, "File not found.")
            return redirect('submittal_send', submittal.id)

        # =========================
        # MARK SENT
        # =========================
        if 'mark_sent' in request.POST:
            submittal.date_sent = timezone.now().date()
            submittal.save()

            if employee:
                SubmittalNotes.objects.create(
                    submittal=submittal,
                    date=timezone.now().date(),
                    user=employee,
                    note=f"Submittal {submittal.submittal_number} marked sent"
                )

            messages.success(request, "Submittal marked sent.")
            return redirect('submittal_send', submittal.id)

        # =========================
        # CREATE TRANSMITTAL PDF
        # =========================
        if 'create_transmittal' in request.POST:
            base_filename = f"Submittal {submittal.submittal_number} Transmittal"
            pdf_filename = f"{base_filename}.pdf"
            pdf_full_path = os.path.join(sent_to_gc_path, pdf_filename)

            version = 2
            while os.path.exists(pdf_full_path):
                pdf_filename = f"{base_filename} V{version}.pdf"
                pdf_full_path = os.path.join(sent_to_gc_path, pdf_filename)
                version += 1

            item_rows = []
            for approval in approvals:
                item_rows.append({
                    'item': approval.submittalitem,
                    'approval': approval,
                })

            logo_path = os.path.join(settings.MEDIA_ROOT, "images/logo.png")

            context = {
                'submittal': submittal,
                'item_rows': item_rows,
                'today': timezone.now().date(),
                'logo_path': logo_path,
            }

            template = get_template('print_submittal_transmittal.html')
            html = template.render(context)

            with open(pdf_full_path, "w+b") as result_file:
                pisa_status = pisa.CreatePDF(html, dest=result_file)

            if pisa_status.err:
                messages.error(request, "There was an error creating the transmittal PDF.")
            else:
                messages.success(request, f"Created {pdf_filename}")

            return redirect('submittal_send', submittal.id)

        # =========================
        # SINGLE FILE UPLOADS
        # =========================
        if 'upload_main_file' in request.FILES:
            upload_file = request.FILES['upload_main_file']
            save_path = os.path.join(main_folder_path, upload_file.name)

            with open(save_path, 'wb+') as destination:
                for chunk in upload_file.chunks():
                    destination.write(chunk)

            messages.success(request, "File uploaded to main submittal folder.")
            return redirect('submittal_send', submittal.id)

        if 'upload_sent_to_gc_file' in request.FILES:
            upload_file = request.FILES['upload_sent_to_gc_file']
            save_path = os.path.join(sent_to_gc_path, upload_file.name)

            with open(save_path, 'wb+') as destination:
                for chunk in upload_file.chunks():
                    destination.write(chunk)

            messages.success(request, "File uploaded to Sent to GC.")
            return redirect('submittal_send', submittal.id)

        if 'upload_approval_file' in request.FILES:
            upload_file = request.FILES['upload_approval_file']
            save_path = os.path.join(approval_docs_path, upload_file.name)

            with open(save_path, 'wb+') as destination:
                for chunk in upload_file.chunks():
                    destination.write(chunk)

            messages.success(request, "File uploaded to Approval Documents.")
            return redirect('submittal_send', submittal.id)

        # =========================
        # BATCH UPLOADS
        # =========================
        main_batch_files = request.FILES.getlist('upload_main_batch')
        if main_batch_files:
            for f in main_batch_files:
                save_path = os.path.join(main_folder_path, f.name)
                with open(save_path, 'wb+') as destination:
                    for chunk in f.chunks():
                        destination.write(chunk)

            messages.success(request, "Files uploaded to main submittal folder.")
            return redirect('submittal_send', submittal.id)

        sent_to_gc_batch_files = request.FILES.getlist('upload_sent_to_gc_batch')
        if sent_to_gc_batch_files:
            for f in sent_to_gc_batch_files:
                save_path = os.path.join(sent_to_gc_path, f.name)
                with open(save_path, 'wb+') as destination:
                    for chunk in f.chunks():
                        destination.write(chunk)

            messages.success(request, "Files uploaded to Sent to GC.")
            return redirect('submittal_send', submittal.id)

        approval_batch_files = request.FILES.getlist('upload_approval_batch')
        if approval_batch_files:
            for f in approval_batch_files:
                save_path = os.path.join(approval_docs_path, f.name)
                with open(save_path, 'wb+') as destination:
                    for chunk in f.chunks():
                        destination.write(chunk)

            messages.success(request, "Files uploaded to Approval Documents.")
            return redirect('submittal_send', submittal.id)

    latest_notes = notes[-4:]
    older_notes = notes[:-4]

    item_rows = []
    for approval in approvals:
        other_submittal_history_exists = SubmittalApprovals.objects.filter(
            submittalitem=approval.submittalitem,
            submittal__isnull=False
        ).exclude(
            submittal=submittal
        ).exists()

        item_rows.append({
            'item': approval.submittalitem,
            'approval': approval,
            'has_history': other_submittal_history_exists,
        })
    new_row_id = request.session.pop('new_row_id', None)
    send_data = {
        'submittal': submittal,
        'item_rows': item_rows,
        'notes': notes,
        'latest_notes': latest_notes,
        'older_notes': older_notes,
        'new_row_id': new_row_id,
        'main_folder_path': main_folder_path2,
        'main_files': main_files,
        'main_file_count': len(main_files),
        'no_main_files': len(main_files) == 0,

        'sent_to_gc_path': sent_to_gc_path2,
        'sent_to_gc_files': sent_to_gc_files,
        'sent_to_gc_file_count': len(sent_to_gc_files),
        'no_sent_to_gc_files': len(sent_to_gc_files) == 0,

        'approval_docs_path': approval_docs_path2,
        'approval_docs_files': approval_docs_files,
        'approval_docs_file_count': len(approval_docs_files),
        'no_approval_docs_files': len(approval_docs_files) == 0,

        'mc_folder_path': mc_folder_path,
        'can_open_folder': True,
        'transmittal_exists': transmittal_exists,
    }

    return render(request, 'submittal_send.html', send_data)

def submittal_item_detail(request, item_id):
    item = get_object_or_404(SubmittalItems, id=item_id)

    if request.method == 'POST':
        if 'mark_no_additional_needed' in request.POST:
            SubmittalApprovals.objects.filter(submittalitem=item,submittal__isnull=True).delete()
            SubmittalItemNotes.objects.create(
                submittal=None,
                submittalitem=item,
                date=timezone.now().date(),
                user=Employees.objects.filter(user=request.user).first(),
                note="Additional Submittal No Longer Required"
            )
            return redirect('submittal_item_detail', item.id)
        # -------------------------------
        # MARK NO LONGER USED
        # -------------------------------
        if 'mark_no_longer_used' in request.POST:
            employee = Employees.objects.filter(user=request.user).first()
            if item.is_no_longer_used:
                item.is_no_longer_used = False
                item.save()
                if employee:
                    SubmittalItemNotes.objects.create(
                        submittal=None,
                        submittalitem=item,
                        date=timezone.now().date(),
                        user=employee,
                        note="Item added back to project"
                    )
                messages.success(request, "Item added back to project!")
            else:
                item.is_no_longer_used = True
                item.save()
                if employee:
                    SubmittalItemNotes.objects.create(
                        submittal=None,
                        submittalitem=item,
                        date=timezone.now().date(),
                        user=employee,
                        note="Item marked as no longer used"
                    )
                messages.success(request, "Item marked as no longer used.")
            return redirect('submittal_item_detail', item.id)


    approvals = SubmittalApprovals.objects.filter(
        submittalitem=item
    ).exclude(submittal=None).select_related(
        'submittal',
        'submittal__job_number',
    ).order_by('id')

    approval_notes = SubmittalItemNotes.objects.filter(
        submittalitem=item
    ).order_by('id')

    unlinked_approvals = SubmittalApprovals.objects.filter(
        submittalitem=item,
        submittal__isnull=True
    ).order_by('id')

    if request.method == 'POST' and 'new_note' in request.POST:
        note_text = request.POST.get('new_note', '').strip()
        employee = Employees.objects.filter(user=request.user).first()

        latest_approval = approvals.last()

        if note_text and employee and latest_approval:
            SubmittalItemNotes.objects.create(
                submittalitem=item,
                date=timezone.now().date(),
                user=employee,
                note=note_text
            )
            messages.success(request, "Note added.")
        else:
            messages.error(request, "Unable to add note.")

        return redirect('submittal_item_detail', item.id)

    send_data = {
        'item': item,
        'approvals': approvals,
        'approval_notes': approval_notes,
        'unlinked_approvals': unlinked_approvals,
    }

    return render(request, 'submittal_item_detail.html', send_data)




def job_submittals_summary(request, job_number):
    job = get_object_or_404(Jobs, job_number=job_number)

    submittals = (
        Submittals.objects
        .filter(job_number=job)
        .order_by("submittal_number")
        .prefetch_related(
            Prefetch(
                "submittalapprovals_set",
                queryset=SubmittalApprovals.objects.select_related("submittalitem").order_by("submittalitem__description"),
                to_attr="approval_rows"
            )
        )
    )

    linked_item_ids = SubmittalApprovals.objects.filter(
        submittal__job_number=job,
        submittal__isnull=False
    ).values_list("submittalitem_id", flat=True)

    not_sent_items = (
        SubmittalItems.objects
        .filter(job_number=job, is_no_longer_used=False)
        .exclude(id__in=linked_item_ids)
        .order_by("description")
    )

    context = {
        "job": job,
        "submittals": submittals,
        "not_sent_items": not_sent_items,
    }

    return render(request, "job_submittals_summary.html", context)