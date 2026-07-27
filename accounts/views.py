import random
from django.shortcuts import render
from employees.models import *
from django.shortcuts import render, redirect
from django.contrib.auth.models import User, auth
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction
from console.misc import Email
from console.random_password_generator import RandomPasswordGenerator
from subcontractors.models import Subcontractors, Subcontractor_Employees
from datetime import datetime,timedelta
from django.conf import settings
import os
from .identity_email import (
    EMAIL_IN_USE_MESSAGE,
    employee_for_unique_identity_email,
    identity_email_is_available,
    normalize_identity_email,
)


def _get_client_ip(request):
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _record_login_attempt(request, username, user, result, failure_reason=""):
    LoginAttempt.objects.create(
        username=username or "",
        user=user,
        result=result,
        failure_reason=failure_reason,
        ip_address=_get_client_ip(request),
        user_agent=(request.META.get("HTTP_USER_AGENT") or "")[:500],
    )


def _resolve_login_user(identifier):
    matching_user = User.objects.filter(username__iexact=identifier).first()
    if matching_user is not None:
        return matching_user, Employees.objects.filter(user=matching_user).first()

    employee = employee_for_unique_identity_email(identifier)
    if employee is not None and employee.user_id:
        return employee.user, employee

    return None, None


def registration(request):
    selected_employee_id = request.session.get("registration_employee_id")
    employee = None
    if str(selected_employee_id or "").isdigit():
        employee = Employees.objects.filter(id=selected_employee_id).first()

    if employee is None:
        request.session.pop("registration_employee_id", None)
        return render(request, "verify_pin.html", {
            "message": (
                "Please enter your employee PIN again before registering."
            ),
        })

    send_data = {"selected_employee": employee}
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = normalize_identity_email(request.POST.get('email'))
        send_data.update({
            "username": username,
            "phonenumber": request.POST.get('phonenumber', ''),
            "email": email,
            "nickname": request.POST.get('nickname', ''),
        })
        username_exists_in_django_users = User.objects.filter(username__iexact=username).exists() if username else False
        username_exists_in_subcontractors = Subcontractors.objects.filter(username__iexact=username).exists() if username else False
        username_exists_in_subcontractor_employees = Subcontractor_Employees.objects.filter(username__iexact=username).exists() if username else False

        if not username or username_exists_in_django_users or username_exists_in_subcontractors or username_exists_in_subcontractor_employees:
            send_data['message'] = "USERNAME ALREADY IN USE. Please choose a different username."
            return render(request, "registration.html", send_data)

        try:
            validate_email(email)
        except ValidationError:
            send_data['message'] = "Please enter a valid email address."
            return render(request, "registration.html", send_data)

        if not identity_email_is_available(email, exclude_instance=employee):
            send_data['message'] = EMAIL_IN_USE_MESSAGE
            return render(request, "registration.html", send_data)

        with transaction.atomic():
            user = User.objects.create_user(
                username=username,
                email=email,
                password=request.POST['password'],
            )
            employee.user = user
            employee.phone = request.POST.get('phonenumber', '')
            employee.nickname = request.POST.get('nickname', '')
            employee.email = email
            user.first_name = employee.first_name
            user.last_name = employee.last_name
            user.save()
            employee.save()
        request.session.pop("registration_employee_id", None)
        return render(request, "login.html", send_data)
    return render(request, "registration.html", send_data)

def verifyPin(request):
    if request.method == 'POST':
        send_data = {}
        selected_employee = Employees.objects.filter(
            pin=request.POST.get('pin')
        ).first()
        if selected_employee is not None:
            request.session["registration_employee_id"] = selected_employee.id
            send_data['selected_employee'] = selected_employee
            return render(request, "registration.html", send_data)
        else:
            request.session.pop("registration_employee_id", None)
            send_data['message'] = "PIN NOT CORRECT"
            return render(request, "verify_pin.html", send_data)
    return render(request, "verify_pin.html")

def forgotPassword(request):
    send_data = {}
    if request.method == 'POST':
        try:
            temporaryPassword = request.POST['temporary']
            password = request.POST['password']
            tempPasswordObject = TemporaryPassword.objects.filter(password=temporaryPassword, is_active=True).first()
            if tempPasswordObject is not None:
                tempPasswordTime = str(tempPasswordObject.expiration).split('.')[0]
                tempPasswordTime = datetime.strptime(tempPasswordTime, '%Y-%m-%d %H:%M:%S')
                if tempPasswordTime < datetime.now():
                    send_data['message'] = "Your temporary password has expired. Please go to login and select forgot password to generate another."
                else:
                    u = User.objects.get(id=tempPasswordObject.user.id)
                    u.set_password(password)
                    u.save()
                    TemporaryPassword.objects.filter(user=u.id).update(is_active=False)
                    send_data['message'] = "Password updated. You can now login with the updated password."
            else:
                send_data['message'] = "The temporary password you entered does not match our records or the password you entered is no longer active. Please go to login and select forgot password to generate another or try again."
        except Exception as e:
            print('unable to update password', e)
    return render(request, "forgot_password.html", send_data)

def login(request):
    send_data = {}
    if request.method == 'POST':
        if 'register' in request.POST:
            return render(request, 'verify_pin.html')
        elif 'forgot' in request.POST:
            # send email to user
            try:
                identifier = request.POST['username'].strip()
                forgottenUser, employee = _resolve_login_user(identifier)
                if forgottenUser is None or employee is None:
                    raise User.DoesNotExist
                randomPassword = RandomPasswordGenerator().getRandomPassword()
                expiration = datetime.now() + timedelta(hours=1)
                #make all other temporary passwords non active
                TemporaryPassword.objects.filter(user=forgottenUser.id).update(is_active=False)
                #create a new temporary password
                TemporaryPassword.objects.create(user=forgottenUser, expiration= expiration, password=randomPassword)
                Email.sendEmail("Forgot Password Alert", f"Someone requested their password. If this is not you, please contact your admin. Go to this page http://184.183.68.156/accounts/forgot_password and use this temporary passcode to reset your password {randomPassword} that will expire after one hour from this email's receipt.", [employee.email], False,"bridgette@gerloffpainting.com")
                send_data['message'] = "Email sent to user with their password"
            except Exception as e:
                send_data['message'] = "Unable to send email, check username and try again or contact your admin"
                print('could not send email', e)
            send_data['username'] = request.POST['username']
            return render(request, "login.html", send_data)
        else:
            username = request.POST['username'].strip()
            password = request.POST['password']
            try:
                matching_user, employee = _resolve_login_user(username)
                auth_username = matching_user.username if matching_user else username
                user = auth.authenticate(username=auth_username, password=password)
                if user is not None:
                    if employee is not None and not employee.active:
                        _record_login_attempt(
                            request,
                            username,
                            user,
                            LoginAttempt.RESULT_FAILED,
                            LoginAttempt.FAILURE_INACTIVE_USER
                        )
                        send_data['message'] = "Invalid credentials"
                        send_data['username'] = request.POST['username']
                        return render(request, "login.html", send_data)
                    auth.login(request, user)
                    return redirect("/")
                if matching_user is None:
                    failure_reason = LoginAttempt.FAILURE_USERNAME_NOT_FOUND
                elif not matching_user.is_active:
                    failure_reason = LoginAttempt.FAILURE_INACTIVE_USER
                else:
                    failure_reason = LoginAttempt.FAILURE_PASSWORD_INCORRECT

                _record_login_attempt(
                    request,
                    username,
                    matching_user,
                    LoginAttempt.RESULT_FAILED,
                    failure_reason
                )
            except Exception as e:
                print('invalid credentials', e)
            send_data['message'] = "Invalid credentials"
            send_data['username'] = request.POST['username']
            return render(request, "login.html", send_data)
    else:
        return render(request, 'login.html')

def logout(request):
    auth.logout(request)
    return redirect("/")


@login_required(login_url='/accounts/login')
def login_attempt_log(request):
    attempts = LoginAttempt.objects.select_related("user").all()[:500]
    return render(request, "login_attempt_log.html", {
        "attempts": attempts,
    })
