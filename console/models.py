from django.db import models

class Employees(models.Model):
	id = models.BigAutoField(primary_key=True)
	employee_number = models.IntegerField(default=0)
	title = models.CharField(null=True, max_length=50)
	active = models.BooleanField(default=True)
	first_name = models.CharField(null=True, max_length=50)
	last_name = models.CharField(null=True, max_length=50)
	phone = models.CharField(null=True, max_length=50)
	email = models.CharField(null=True, max_length=50)


class Project_Users(models.Model):
	employee_id = models.IntegerField(default=0)
	user_name = models.CharField(null=True, max_length=50)
	position = models.CharField(null=True, max_length=100)
	abbreviation = models.CharField(null=True, max_length=25)
	email = models.CharField(null=True, max_length=50)
	cell_phone = models.CharField(null=True, max_length=50)
	office_extension = models.CharField(null=True, max_length=10)

class Change_Orders(models.Model):
	id = models.BigAutoField(primary_key=True)
	job_number = models.CharField(null=True,max_length=5)
	cop_number = models.IntegerField(default=0)
	is_t_and_m = models.BooleanField(default=True)
	description = models.CharField(null=True,max_length=700)
	date_sent = models.DateTimeField(null=True, blank=True)
	date_approved = models.DateTimeField(null=True, blank=True)
	gc_number = models.IntegerField(default=0)
	closed = models.DateTimeField(null=True, blank=True)
	notes = models.CharField(null=True,max_length=1000)
	ewt_number = models.IntegerField(default=0)
	is_work_complete = models.BooleanField(default=False)
	is_waiting_for_pm = models.BooleanField(default=False)

class Checklist(models.Model):
	id = models.BigAutoField(primary_key=True)
	job_name = models.CharField(null=True,max_length=1000)
	category = models.CharField(null=True, max_length=1000)
	checklist_item = models.CharField(null=True, max_length=2000)
	is_closed = models.BooleanField(default=False)
	job_number = models.CharField(null=True, max_length=10)
	notes = models.CharField(null=True, max_length=2500)
	job_start_date_from_schedule = models.DateTimeField(null=True, blank=True)
	cop = models.BooleanField(default=False)
	cop_amount = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)
	cop_sent_date = models.DateTimeField(null=True, blank=True)
	cop_number = models.IntegerField(default=0)
	is_ewt = models.BooleanField(default=False)
	ewt_date = models.DateTimeField(null=True, blank=True)
	is_submittal = models.BooleanField(default=False)
	submittal_number = models.IntegerField(default=0)
	submittal_description = models.CharField(null=True, max_length=2000)
	submittal_date_sent = models.DateTimeField(null=True, blank=True)
	wallcovering_order_date = models.DateTimeField(null=True, blank=True)
	assigned = models.CharField(null=True, max_length=2000)

class Clients(models.Model):
	id = models.BigAutoField(primary_key=True)
	company = models.CharField(null=True, max_length=250)
	estimator = models.CharField(null=True, max_length=250)
	estimator_phone = models.CharField(null=True, max_length=50)
	estimator_email = models.CharField(null=True, max_length=250)
	bid_fax = models.CharField(null=True, max_length=50)
	bid_email = models.CharField(null=True, max_length=50)
	vendor_code = models.CharField(null=True, max_length=100)


class Estimates(models.Model):
	id = models.BigAutoField(primary_key=True)
	to_number = models.IntegerField(default=0)
	bid_date = models.DateTimeField(null=True, blank=True)
	take_off_name = models.CharField(null=True, max_length=2000)
	estimator = models.CharField(null=True, max_length=250)
	bidders = models.CharField(null=True, max_length=250)
	has_docs_print = models.BooleanField(default=False)
	#estimate_status = models.enum.EnumField(choices=['Awarded','Bid Sent','Not Bidding', 'In Progress', 'To Joe', 'T/O Done'])
	comments = models.CharField(null=True, max_length=2000)
	addenda = models.IntegerField(default=0)
	site_visit_date = models.DateTimeField(null=True, blank=True)
	client_estimator_name = models.CharField(null=True, max_length=250)
	client_estimator_email = models.CharField(null=True, max_length=250)
	client_phone = models.CharField(null=True, max_length=50)
	send_bids_to_email = models.CharField(null=True, max_length=250)
	price = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)
	job_number = models.CharField(null=True, max_length=50)
	wage_rate_spray = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)
	wate_rate_paint = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)
	is_awarded_gc = models.BooleanField(default=False)

class Extra_Work_Tickets(models.Model):
	id = models.BigAutoField(primary_key=True)
	job_number = models.CharField(null=True, max_length=10)
	ewt_number = models.IntegerField(default=0)
	description = models.CharField(null=True, max_length=2000)
	date_added = models.DateTimeField(null=True, blank=True)
	date_returned = models.DateTimeField(null=True, blank=True)
	cop_number = models.IntegerField(default=0)
	notes = models.CharField(null=True, max_length=2000)
	is_closed = models.BooleanField(default=False)

class Incoming_Wall_Covering(models.Model):
	id = models.BigAutoField(primary_key=True)
	job_number = models.CharField(null=True, max_length=10)
	orders_primary_key = models.IntegerField(default=0)
	wallcovering_primary_key = models.IntegerField(default=0)
	package_primary_key = models.IntegerField(default=0)
	package_description = models.CharField(null=True, max_length=2000)
	packages = models.IntegerField(default=0)
	notes = models.CharField(null=True, max_length=2000)
	quantity = models.IntegerField(default=0)

class Inventory_Type(models.Model):
	id = models.IntegerField(primary_key=True)
	type = models.CharField(null=True, max_length=50)
	is_active = models.BooleanField(default=False)

class Storage_Location_Type(models.Model):
	id = models.IntegerField(primary_key=True)
	type = models.CharField(null=True, max_length=50)
	is_active = models.BooleanField(default=False)

class Jobs(models.Model):
	job_number = models.CharField(null=False, max_length=5, primary_key=True)
	job_name = models.CharField(null=True, max_length=250)
	estimator = models.CharField(null=True, max_length=50)
	foreman = models.CharField(null=True, max_length=50)
	superintendent = models.CharField(null=True, max_length=50)
	contract_amount = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)
	po_number = models.CharField(null=True, max_length=50)
	retainage_percentage = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
	is_t_m_job = models.BooleanField(default=False)
	t_m_nte_amount = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)
	status = models.CharField(null=True, max_length=50)
	booked_date = models.DateTimeField(null=True, blank=True)
	booked_by = models.CharField(null=True, max_length=50)
	is_wage_scale = models.BooleanField(default=False)
	is_davis_bacon_wages = models.BooleanField(default=False)
	spray_scale = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
	brush_role = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
	address = models.CharField(null=True, max_length=50)
	city = models.CharField(null=True, max_length=20)
	state = models.CharField(null=True, max_length=2)
	start_date = models.DateTimeField(null=True, blank=True)
	duration = models.CharField(null=True, max_length=50)
	estimate_number = models.CharField(null=True, max_length=50)
	estimate_price = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)
	has_wallcovering = models.BooleanField(default=False)
	has_paint = models.BooleanField(default=False)
	has_owner_supplied_wallcovering = models.BooleanField(default=False)
	painting_budget = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)
	wallcovering_budget = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)
	is_send_auto_co_emails = models.BooleanField(default=False)
	is_send_auto_submittal_emails = models.BooleanField(default=False)
	notes = models.CharField(null=True, max_length=2000)
	approved_change_orders = models.DecimalField(max_digits=9, decimal_places=4, blank=True, null=True)
	final_bill_amount = models.DecimalField(max_digits=9, decimal_places=2, blank=True, null=True)
	is_closed = models.BooleanField(default=False)
	labor_done_Date = models.DateTimeField(null=True, blank=True)
	ar_closed_date = models.DateTimeField(null=True, blank=True)
	was_previously_closed = models.BooleanField(default=False)
	previously_closed_date = models.DateTimeField(null=True, blank=True)
	cumulative_costs_at_closing = models.DecimalField(max_digits=9, decimal_places=2, blank=True, null=True)
	contract_status = models.BooleanField(default=False)
	insurance_status = models.BooleanField(default=False)
	submittals_required = models.BooleanField(default=False)
	has_special_paint = models.IntegerField()


class Job_Notes(models.Model):
	id = models.BigAutoField(primary_key=True)
	job_number = models.ForeignKey(Jobs,on_delete=models.CASCADE)
	note = models.CharField(null=True, max_length=2000)
	type = models.CharField(null=True, max_length=50) #booking note, field note, CO note, submittal note, start date note, daily report, etc
	user = models.CharField(null=True, max_length=50) #bridgette joe
	date = models.DateTimeField(null=True, blank=True)
	daily_employee_count = models.IntegerField(default=0)
	note_date = models.DateTimeField(null=True, blank=True) #use if you are having to back date a daily report


class Inventory(models.Model):
	id = models.BigAutoField(primary_key=True)
	number = models.IntegerField(default=0)
	item = models.CharField(null=True, max_length=2000)
	inventory_type = models.CharField(null=True, max_length=50)
	storage_location = models.CharField(null=True, max_length=50)
	purchase_date = models.DateTimeField(null=True, blank=True)
	purchase_price = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)
	purchased_from = models.CharField(null=True, max_length = 2000)
	purchased_by = models.CharField(null=True, max_length=250)
	serial_number = models.CharField(null=True, max_length=250)
	po_number = models.CharField(null=True, max_length=250)
	is_labeled = models.BooleanField(default=False)
	#status = models.EnumField(choices=['Available','Checked Out', 'Missing'])
	date_out = models.DateTimeField(null=True, blank=True)
	date_returned = models.DateTimeField(null=True, blank=True)
	job_name = models.CharField(null=True, max_length=250)
	job_number = models.ForeignKey(Jobs,on_delete=models.CASCADE)
	# job_number is the foreign key to the job number in Jobs
	notes = models.CharField(null=True, max_length=2000)


class TM_Prices(models.Model):
	id = models.BigAutoField(primary_key=True)
	job_number = models.ForeignKey(Jobs,on_delete=models.CASCADE)
	supervisor = models.CharField(null=True, max_length=50)
	painter_hours = models.IntegerField(default=0)
	painter_hours_ot = models.IntegerField(default=0)
	painter_hours_premium_only = models.IntegerField(default=0)
	inventory_percentage = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
	bond_percentage = models.DecimalField(max_digits=9, decimal_places=2, blank=True, null=True)
	
class TM_List(models.Model):
	id = models.BigAutoField(primary_key=True)
	tm_price_id = models.IntegerField(default=0)
	job_id = models.IntegerField(default=0)
	paint_type = models.CharField(null=True, max_length=50)
	amount = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)

class Client_Information(models.Model):
	id = models.BigAutoField(primary_key=True)
	job_number = models.ForeignKey(Jobs,on_delete=models.CASCADE)
	contractor = models.CharField(null=True, max_length=250)
	office1 = models.CharField(null=True, max_length=250)
	office2 = models.CharField(null=True, max_length=250)
	office3 = models.CharField(null=True, max_length=250)
	co_contact = models.CharField(null=True, max_length=250)
	email1 = models.CharField(null=True, max_length=250)
	submittal_contact = models.CharField(null=True, max_length=250)
	email2 = models.CharField(null=True, max_length=250)
	field = models.CharField(null=True, max_length=250)
	field = models.CharField(null=True, max_length=250)
	field = models.CharField(null=True, max_length=250)

class Orders(models.Model):
	id = models.BigAutoField(primary_key=True)
	po_number = models.IntegerField(default=0)
	item_number = models.CharField(null=True, max_length=50)
	job_number = models.CharField(null=False,max_length=10)
	wallcovering_id = models.IntegerField(default=0)
	code = models.CharField(null=True, max_length=50)
	vendor = models.CharField(null=True, max_length=250)
	description = models.CharField(null=True, max_length=2000)
	date_ordered = models.DateTimeField(null=True, blank=True)
	quantity = models.IntegerField(default=0)
	#unit = models.EnumField(choices=['Yards', 'Feet', 'Misc', 'Ounces', 'Pounds'])
	price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
	extra = models.CharField(null=True, max_length=100)
	is_closed = models.BooleanField(default=False)
	notes = models.CharField(null=True, max_length=2000)

class Outgoing_Wallcovering(models.Model):
	id = models.BigAutoField(primary_key=True)
	job_number = models.CharField(null=False, max_length=10)
	package_id = models.IntegerField(default=0)
	packages_out = models.IntegerField(default=0)
	date_out = models.DateTimeField(null=True, blank=True)
	delivered_by = models.CharField(null=True, max_length=50)
	notes = models.CharField(null=True, max_length=2000)

class Packages(models.Model):
	id = models.BigAutoField(primary_key=True)
	wallcovering_id = models.IntegerField(default=0)
	job_number = models.CharField(null=False, max_length=10)
	package_description = models.CharField(null=True, max_length=1000)
	is_closed = models.BooleanField(default=False)
	job_name = models.CharField(null=True, max_length=100)

class Plans(models.Model):
	id = models.BigAutoField(primary_key=True)
	job_number = models.CharField(null=False, max_length=10)
	job_name = models.CharField(null=True, max_length=250)
	description = models.CharField(null=True, max_length=2000)
	estimates_number = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
	
class Subcontractors(models.Model):
	id = models.BigAutoField(primary_key=True)
	job_number = models.CharField(null=False, max_length=10)
	wallcovering_id = models.IntegerField(default=0)
	subcontractor = models.CharField(null=True, max_length=250)
	po_number = models.IntegerField(default=0)
	scope = models.CharField(null=True, max_length=250)
	price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
	#unit = models.EnumField(choices=['LUMP SUM', 'PER YARD'])
	total_ordered = models.IntegerField(default=0)
	total_authorized = models.IntegerField(default=0)
	
class Submittal_Items(models.Model):
	id = models.BigAutoField(primary_key=True)
	job_number = models.CharField(null=False, max_length=10)
	wallcovering_id = models.IntegerField(default=0)
	item_number = models.IntegerField(default=0)
	cop_primary_key = models.IntegerField(default=0)
	description = models.CharField(null=True, max_length=250)
	quantity = models.IntegerField(default=0)
	#status = models.EnumField(choices=['Approved','Denied','Undecided'])
	is_closed = models.BooleanField(default=False)

class Submittals(models.Model):
	id = models.BigAutoField(primary_key=True)
	job_number = models.CharField(null=False, max_length=10)
	wallcovering_id = models.IntegerField(default=0)
	description = models.CharField(null=True, max_length=2000)
	submittal_number = models.IntegerField(default=0)
	date_sent = models.DateTimeField(null=True, blank=True)
	date_returned = models.DateTimeField(null=True, blank=True)
	#status = models.EnumField(choices=['Approved','Denied','Undecided'])
	notes = models.CharField(null=True, max_length=2000)

class Wallcovering(models.Model):
	id = models.BigAutoField(primary_key=True)
	job_number = models.CharField(null=False, max_length=10)
	code = models.CharField(null=True, max_length=10)
	vendor = models.CharField(null=True, max_length=25)
	description = models.CharField(null=True, max_length=2000)
	estimated = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
	#unit = models.EnumField(choices=['Yards', 'Feet', 'Misc', 'Ounces', 'Pounds'])
	price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
	cut_charge = models.CharField(null=True, max_length=1000)
	width = models.CharField(null=True, max_length=50)
	vertical_repeat = models.CharField(null=True, max_length=50)
	#cut = models.EnumField(choices=['Straight','Random'])
	notes = models.CharField(null=True, max_length=2000)

class Job_Numbers(models.Model):
	letter = models.CharField(null=False, max_length=1)
	number = models.CharField(null=False, max_length=4)
