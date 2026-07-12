def nav_employee(request):
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {
            "nav_employee": None,
            "nav_show_my_page_button": False,
        }

    from employees.models import Employees

    employee = (
        Employees.objects
        .filter(user=user)
        .select_related("job_title")
        .first()
    )
    is_painter = bool(
        employee and
        employee.job_title and
        employee.job_title.description == "Painter"
    )

    return {
        "nav_employee": employee,
        "nav_show_my_page_button": bool(employee and not is_painter),
    }
