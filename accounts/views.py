import random
from django.shortcuts import render
from employees.models import *
from django.shortcuts import render, redirect
from django.contrib.auth.models import User, auth
from django.contrib.auth.decorators import login_required
from console.misc import Email
from console.random_password_generator import RandomPasswordGenerator
from subcontractors.models import Subcontractors, Subcontractor_Employees
from datetime import datetime,timedelta
from django.conf import settings
import os


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


def registration(request):
    send_data = {}
    if request.method == 'POST':
        username = request.POST['username'].strip()
        username_exists_in_django_users = User.objects.filter(username__iexact=username).exists()
        username_exists_in_subcontractors = Subcontractors.objects.filter(username__iexact=username).exists()
        username_exists_in_subcontractor_employees = Subcontractor_Employees.objects.filter(username__iexact=username).exists()

        if username_exists_in_django_users or username_exists_in_subcontractors or username_exists_in_subcontractor_employees:
            send_data['message'] = "Username already exists"
            send_data['username'] = username
            send_data['password'] = request.POST['password']
            send_data['phonenumber'] = request.POST['phonenumber']
            send_data['email'] = request.POST['email']
            return render(request, "registration.html", send_data)
        user = User.objects.create_user(username=username,
                                        email=request.POST['email'],
                                        password=request.POST['password'])
        employee = Employees.objects.get(id=request.POST['selected_employee'])
        employee.user = user
        employee.phone = request.POST['phonenumber']
        employee.nickname = request.POST['nickname']
        employee.email = request.POST['email']
        user.first_name = employee.first_name
        user.last_name = employee.last_name
        user.save()
        employee.save()
        return render(request, "login.html", send_data)
    return render(request, "registration.html", send_data)

def verifyPin(request):
    if request.method == 'POST':
        send_data = {}
        if Employees.objects.filter(pin=request.POST['pin']).exists():
            selected_employee = Employees.objects.get(pin=request.POST['pin'])
            send_data['selected_employee'] = selected_employee
            return render(request, "registration.html", send_data)
        else:
            send_data['message'] = "PIN NOT CORRECT"
            return render(request, "verify_pin.html", send_data)

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
                username = request.POST['username']
                forgottenUser = User.objects.get(username=username)
                employee = Employees.objects.get(user=forgottenUser)
                randomPassword = RandomPasswordGenerator().getRandomPassword()
                expiration = datetime.now() + timedelta(hours=1)
                #make all other temporary passwords non active
                TemporaryPassword.objects.filter(user=forgottenUser.id).update(is_active=False)
                #create a new temporary password
                TemporaryPassword.objects.create(user=forgottenUser, expiration= expiration, password=randomPassword)
                Email.sendEmail("Forgot Password Alert", f"Someone requested their password. If this is not you, please contact your admin. Go to this page http://184.183.68.156/accounts/forgot_password and use this temporary passcode to reset your password {randomPassword} that will expire after one hour from this email's receipt.", [employee.email], False,"operations@gerloffpainting.com")
                send_data['message'] = "Email sent to user with their password"
            except Exception as e:
                send_data['message'] = "Unable to send email, check username and try again or contact your admin"
                print('could not send email', e)
            send_data['username'] = request.POST['username']
            send_data['password'] = request.POST['password']
            return render(request, "login.html", send_data)
        else:
            username = request.POST['username']
            password = request.POST['password']
            try:
                matching_user = User.objects.filter(username=username).first()
                user = auth.authenticate(username=username, password=password)
                if user is not None:
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
            send_data['password'] = request.POST['password']
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
