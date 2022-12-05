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
	def __str__(self):
		return f"{self.first_name} {self.last_name}"

class Clients(models.Model):
	id = models.BigAutoField(primary_key=True)
	company = models.CharField(null=True, max_length=250)
	bid_fax = models.CharField(null=True, max_length=50)
	bid_email = models.CharField(null=True, max_length=50)
	vendor_code = models.CharField(null=True, max_length=100)
	address = models.CharField(null=True, max_length=100)
	city = models.CharField(null=True, max_length=100)
	state = models.CharField(null=True, max_length=100)
	phone = models.CharField(null=True, max_length=50)


class Client_Employees(models.Model):
	person_PK = models.BigAutoField(primary_key=True)
	id = models.ForeignKey(Clients, on_delete=models.CASCADE)
	name = models.CharField(null=True, max_length=250)
	phone = models.CharField(null=True, max_length=50)
	email = models.CharField(null=True, max_length=250)
	title = models.CharField(null=True, max_length=250)

class Jobs(models.Model):
	job_number = models.CharField(null=False, max_length=5, primary_key=True)
	job_name = models.CharField(null=True, max_length=250)
	estimator = models.CharField(null=True, max_length=50)
	foreman = models.CharField(null=True, max_length=50)
	superintendent = models.ForeignKey(Employees, on_delete=models.CASCADE, null=True)
	contract_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
	po_number = models.CharField(null=True, max_length=50)
	retainage_percentage = models.CharField(null=True, max_length=50)
	is_t_m_job = models.BooleanField(default=False)
	t_m_nte_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
	status = models.CharField(null=True, max_length=50) #open,closed
	booked_date = models.DateTimeField(null=True, blank=True)
	booked_by = models.CharField(null=True, max_length=50)
	is_wage_scale = models.BooleanField(default=False)
	is_davis_bacon_wages = models.BooleanField(default=False)
	spray_scale = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
	brush_role = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
	address = models.CharField(null=True, max_length=50)
	city = models.CharField(null=True, max_length=20)
	state = models.CharField(null=True, max_length=2)
	start_date = models.DateTimeField(null=True, blank=True)
	duration = models.CharField(null=True, max_length=50)
	estimate_number = models.CharField(null=True, max_length=50)
	estimate_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
	has_wallcovering = models.BooleanField(default=False)
	has_paint = models.BooleanField(default=False)
	has_owner_supplied_wallcovering = models.BooleanField(default=False)
	painting_budget = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
	wallcovering_budget = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
	is_send_auto_co_emails = models.BooleanField(default=True)
	is_send_auto_submittal_emails = models.BooleanField(default=True)
	notes = models.CharField(null=True, max_length=2000)
	approved_change_orders = models.DecimalField(max_digits=10, decimal_places=4, blank=True, null=True)
	final_bill_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
	is_closed = models.BooleanField(default=False)
	labor_done_Date = models.DateTimeField(null=True, blank=True)
	ar_closed_date = models.DateTimeField(null=True, blank=True)
	was_previously_closed = models.BooleanField(default=False)
	previously_closed_date = models.DateTimeField(null=True, blank=True)
	cumulative_costs_at_closing = models.DecimalField(max_digits=9, decimal_places=2, blank=True, null=True)
	contract_status = models.IntegerField()
	insurance_status = models.IntegerField()
	submittals_required = models.IntegerField(null=True)
	has_special_paint = models.IntegerField(null=True)
	client = models.CharField(null=True, max_length=100)
	client_Pm = models.ForeignKey(Client_Employees, related_name="PM", on_delete=models.CASCADE,  null=True)
	client_Pm_Phone = models.CharField(null=True, max_length=50)
	client_Pm_Email = models.CharField(null=True, max_length=100)
	client_Co_Contact = models.ForeignKey(Client_Employees, related_name="CO", on_delete=models.CASCADE, null=True)
	client_Co_Email = models.CharField(null=True, max_length=100)
	client_Submittal_Contact = models.ForeignKey(Client_Employees, related_name="Submittals", on_delete=models.CASCADE, null=True)
	client_Submittal_Email = models.CharField(null=True, max_length=100)
	client_Super = models.ForeignKey(Client_Employees, related_name="Super", on_delete=models.CASCADE, null=True)
	client_Super_Phone = models.CharField(null=True, max_length=50)
	client_Super_Email = models.CharField(null=True, max_length=100)
	is_on_base = models.BooleanField(default=False)
	id = models.ForeignKey(Clients, on_delete=models.CASCADE) #client
	unsigned_tickets = models.IntegerField(null=True, blank=True)
	assigned_inventory = models.IntegerField(null=True, blank=True)
	assigned_rentals = models.IntegerField(null=True, blank=True)
	def __str__(self):
		return f"{self.job_name}"





class Inventory_Type(models.Model):
	id = models.IntegerField(primary_key=True)
	type = models.CharField(null=True, max_length=50)
	is_active = models.BooleanField(default=False)

class Storage_Location_Type(models.Model):
	id = models.IntegerField(primary_key=True)
	type = models.CharField(null=True, max_length=50)
	is_active = models.BooleanField(default=False)


class Checklist(models.Model):
	id = models.BigAutoField(primary_key=True)
	category = models.CharField(null=True, max_length=1000)
	checklist_item = models.CharField(null=True, max_length=2000)
	is_closed = models.BooleanField(default=False)
	job_number = models.ForeignKey(Jobs,on_delete=models.CASCADE)
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
	number = models.CharField(null=True, max_length=50,blank = True)
	item = models.CharField(null=True, max_length=2000)
	inventory_type = models.ForeignKey(Inventory_Type,on_delete=models.CASCADE)
	storage_location = models.CharField(null=True, max_length=50, blank=True)
	purchase_date = models.DateTimeField(null=True, blank=True)
	purchase_price = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)
	purchased_from = models.CharField(null=True, max_length = 2000, blank=True)
	purchased_by = models.CharField(null=True, max_length=250, blank=True)
	serial_number = models.CharField(null=True, max_length=250, blank=True)
	po_number = models.CharField(null=True, max_length=250, blank=True)
	is_labeled = models.BooleanField(default=False)
	status = models.CharField(null=True, max_length=250, blank=True)
	date_out = models.DateTimeField(null=True, blank=True)
	date_returned = models.DateTimeField(null=True, blank=True)
	job_number = models.ForeignKey(Jobs,on_delete=models.CASCADE, blank=True)
	# job_number is the foreign key to the job number in Jobs
	notes = models.CharField(null=True, max_length=2000, blank=True)
	def __str__(self):
		return f"{self.job_number} {self.item}"


class Change_Orders(models.Model):
	id = models.BigAutoField(primary_key=True)
	job_number = models.ForeignKey(Jobs,on_delete=models.CASCADE)
	cop_number = models.IntegerField(default=0)
	is_t_and_m = models.BooleanField(default=False)
	description = models.CharField(null=True,max_length=700)
	date_sent = models.DateTimeField(null=True, blank=True)
	date_approved = models.DateTimeField(null=True, blank=True)
	gc_number = models.IntegerField(default=0, null=True, blank=True)
	is_closed = models.BooleanField(default=False)
	notes = models.CharField(null=True,max_length=1000)
	is_work_complete = models.BooleanField(default=False)
	is_ticket_signed = models.BooleanField(default=False)
	date_signed = models.DateTimeField(null=True, blank=True)
	ticket_processing = models.IntegerField(default=0, null=True, blank=True)
	def __str__(self):
		return f"{self.job_number} {self.description}"


class TM_Prices_Master(models.Model): #use this in case a job has special rates
	id = models.BigAutoField(primary_key=True)
	supervisor_hours = models.DecimalField(max_digits=9, decimal_places=2, blank=True, null=True)
	painter_hours = models.DecimalField(max_digits=9, decimal_places=2, blank=True, null=True)
	painter_hours_ot = models.DecimalField(max_digits=9, decimal_places=2, blank=True, null=True)
	painter_hours_premium_only = models.DecimalField(max_digits=9, decimal_places=2, blank=True, null=True)
	inventory_percentage = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
	bond_percentage = models.DecimalField(max_digits=9, decimal_places=2, blank=True, null=True)
	material1 = models.CharField(null=True, max_length=50)
	price1 = models.DecimalField(max_digits=9, decimal_places=2, blank=True, null=True)
	material2 = models.CharField(null=True, max_length=50)
	price2 = models.DecimalField(max_digits=9, decimal_places=2, blank=True, null=True)
	material3 = models.CharField(null=True, max_length=50)
	price3 = models.DecimalField(max_digits=9, decimal_places=2, blank=True, null=True)
	material4 = models.CharField(null=True, max_length=50)
	price4 = models.DecimalField(max_digits=9, decimal_places=2, blank=True, null=True)
	material5 = models.CharField(null=True, max_length=50)
	price5 = models.DecimalField(max_digits=9, decimal_places=2, blank=True, null=True)
	material6 = models.CharField(null=True, max_length=50)
	price6 = models.DecimalField(max_digits=9, decimal_places=2, blank=True, null=True)
	material7 = models.CharField(null=True, max_length=50)
	price7 = models.DecimalField(max_digits=9, decimal_places=2, blank=True, null=True)
	material8 = models.CharField(null=True, max_length=50)
	price8 = models.DecimalField(max_digits=9, decimal_places=2, blank=True, null=True)
	material9 = models.CharField(null=True, max_length=50)
	price9 = models.DecimalField(max_digits=9, decimal_places=2, blank=True, null=True)
	material10 = models.CharField(null=True, max_length=50)
	price10 = models.DecimalField(max_digits=9, decimal_places=2, blank=True, null=True)
	material11 = models.CharField(null=True, max_length=50)
	price11 = models.DecimalField(max_digits=9, decimal_places=2, blank=True, null=True)
	material12 = models.CharField(null=True, max_length=50)
	price12 = models.DecimalField(max_digits=9, decimal_places=2, blank=True, null=True)
	material13 = models.CharField(null=True, max_length=50)
	price13 = models.DecimalField(max_digits=9, decimal_places=2, blank=True, null=True)


class TM_Prices(models.Model): #use this in case a job has special rates
	id = models.BigAutoField(primary_key=True)
	job_number = models.ForeignKey(Jobs,on_delete=models.CASCADE)
	supervisor_hours = models.DecimalField(max_digits=9, decimal_places=2, blank=True, null=True)
	painter_hours = models.DecimalField(max_digits=9, decimal_places=2, blank=True, null=True)
	painter_hours_ot = models.DecimalField(max_digits=9, decimal_places=2, blank=True, null=True)
	painter_hours_premium_only = models.DecimalField(max_digits=9, decimal_places=2, blank=True, null=True)
	inventory_percentage = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
	bond_percentage = models.DecimalField(max_digits=9, decimal_places=2, blank=True, null=True)
	material1 = models.CharField(null=True, max_length=50)
	price1 = models.DecimalField(max_digits=9, decimal_places=2, blank=True, null=True)
	material2 = models.CharField(null=True, max_length=50)
	price2 = models.DecimalField(max_digits=9, decimal_places=2, blank=True, null=True)
	material3 = models.CharField(null=True, max_length=50)
	price3 = models.DecimalField(max_digits=9, decimal_places=2, blank=True, null=True)
	material4 = models.CharField(null=True, max_length=50)
	price4 = models.DecimalField(max_digits=9, decimal_places=2, blank=True, null=True)
	material5 = models.CharField(null=True, max_length=50)
	price5 = models.DecimalField(max_digits=9, decimal_places=2, blank=True, null=True)
	material6 = models.CharField(null=True, max_length=50)
	price6 = models.DecimalField(max_digits=9, decimal_places=2, blank=True, null=True)
	material7 = models.CharField(null=True, max_length=50)
	price7 = models.DecimalField(max_digits=9, decimal_places=2, blank=True, null=True)
	material8 = models.CharField(null=True, max_length=50)
	price8 = models.DecimalField(max_digits=9, decimal_places=2, blank=True, null=True)
	material9 = models.CharField(null=True, max_length=50)
	price9 = models.DecimalField(max_digits=9, decimal_places=2, blank=True, null=True)
	material10 = models.CharField(null=True, max_length=50)
	price10 = models.DecimalField(max_digits=9, decimal_places=2, blank=True, null=True)
	material11 = models.CharField(null=True, max_length=50)
	price11 = models.DecimalField(max_digits=9, decimal_places=2, blank=True, null=True)
	material12 = models.CharField(null=True, max_length=50)
	price12 = models.DecimalField(max_digits=9, decimal_places=2, blank=True, null=True)
	material13 = models.CharField(null=True, max_length=50)
	price13 = models.DecimalField(max_digits=9, decimal_places=2, blank=True, null=True)
	
class TM_List(models.Model): #one entry for each line item of t&m bill
	id = models.BigAutoField(primary_key=True)
	change_order = models.ForeignKey(Change_Orders,on_delete=models.CASCADE)
	quantity = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
	units = models.CharField(null=False, max_length=10)
	rate = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
	total = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)


class Vendor_Category(models.Model): #rentals, wallcovering
	id = models.BigAutoField(primary_key=True)
	category = models.CharField(null=True, max_length=250)

class Vendors(models.Model):
	id = models.BigAutoField(primary_key=True)
	company_name = models.CharField(null=True, max_length=250)
	category = models.ForeignKey(Vendor_Category,on_delete=models.CASCADE,null=True, blank=True)
	company_phone = models.CharField(null=True, max_length=20)
	company_email = models.CharField(null=True, max_length=100)


class Vendor_Contact(models.Model):
	id = models.BigAutoField(primary_key=True)
	company = models.ForeignKey(Vendors, on_delete=models.CASCADE, null=True, blank=True)
	name = models.CharField(null=True, max_length=250)
	email = models.CharField(null=True, max_length=100)
	phone = models.CharField(null=True, max_length=20)


class Wallcovering(models.Model):
	id = models.BigAutoField(primary_key=True)
	job_number = models.ForeignKey(Jobs,on_delete=models.CASCADE)
	code = models.CharField(null=True, max_length=10) #wc1, etc.
	vendor = models.ForeignKey(Vendors,on_delete=models.CASCADE)
	pattern = models.CharField(null=True, max_length=2000)
	estimated_quantity = models.IntegerField(default=0)
	estimated_unit = models.CharField(null=True, max_length=20)
	pricing1_date = models.DateTimeField(null=True, blank=True)
	pricing1_yards_tier1 = models.IntegerField(default=0)
	pricing1_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
	pricing2_yards_tier1 = models.IntegerField(default=0)
	pricing2_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
	pricing3_yards_tier1 = models.IntegerField(default=0)
	pricing3_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
	cut_charge = models.CharField(null=True, max_length=1000)
	roll_width = models.CharField(null=True, max_length=50)
	vertical_repeat = models.CharField(null=True, max_length=50)
	is_random_reverse = models.BooleanField(default=False)
	is_repeat = models.BooleanField(default=False)
	notes = models.CharField(null=True, max_length=2000)


class Orders(models.Model): #one pattern, one WC1, etc. may be broken up into several packages
	id = models.BigAutoField(primary_key=True)
	po_number = models.IntegerField(default=0)
	job_number = models.ForeignKey(Jobs,on_delete=models.CASCADE, null=True, blank=True)
	vendor = models.ForeignKey(Vendors,on_delete=models.CASCADE, null=True, blank=True)
	description = models.CharField(null=True, max_length=2000)
	date_ordered = models.DateTimeField(null=True, blank=True)
	partial_receipt = models.BooleanField(default=False)
	is_satisfied = models.BooleanField(default=False)
	notes = models.CharField(null=True, max_length=2000)


class Order_Items(models.Model): #usually just one of these per order
	id = models.BigAutoField(primary_key=True)
	order = models.ForeignKey(Orders, on_delete=models.CASCADE, null=True, blank=True)
	wallcovering = models.ForeignKey(Wallcovering, on_delete=models.CASCADE, null=True, blank=True)
	quantity = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
	unit = models.CharField(null=True, max_length=10)
	price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
	item_description = models.CharField(null=True, max_length=100)
	item_notes = models.CharField(null=True, max_length=1000)


class Wallcovering_Delivery(models.Model): #one instance when receiving material. actual items listed below
	id = models.BigAutoField(primary_key=True)
	date = models.DecimalField(max_digits=10, decimal_places=2)
	order = models.ForeignKey(Orders, on_delete=models.CASCADE, blank=True, null=True)
	items = models.ForeignKey(Order_Items, on_delete=models.CASCADE, blank=True, null=True)
	job_number = models.ForeignKey(Jobs, on_delete=models.CASCADE, blank=True, null=True)


class Packages(models.Model):
	id = models.BigAutoField(primary_key=True)
	delivery = models.ForeignKey(Wallcovering_Delivery, on_delete=models.CASCADE)
	order_item = models.ForeignKey(Order_Items, on_delete=models.CASCADE,blank=True, null=True)
	description = models.CharField(null=True, max_length=200)
	quantity_received = models.IntegerField(default=0)
	unit = models.CharField(null=False, max_length=20)
	notes = models.CharField(null=True, max_length=2000)
	job_number = models.ForeignKey(Jobs, on_delete=models.CASCADE, blank=True, null=True)



class Outgoing_Wallcovering(models.Model):
	id = models.BigAutoField(primary_key=True)
	date = models.DecimalField(max_digits=10, decimal_places=2)
	job_number = models.ForeignKey(Jobs, on_delete=models.CASCADE, blank=True, null=True)
	delivered_by = models.CharField(null=True, max_length=200)
	notes = models.CharField(null=True, max_length=2000)


class Outgoing_Item(models.Model):
	id = models.BigAutoField(primary_key=True)
	package = models.ForeignKey(Packages, on_delete=models.CASCADE, blank=True, null=True)
	description = models.CharField(null=True, max_length=200)
	quantity_sent = models.IntegerField(default=0)


class Subcontractors(models.Model):
	id = models.BigAutoField(primary_key=True)
	subcontractor = models.CharField(null=True, max_length=250)
	po_number = models.IntegerField(default=0)
	scope = models.CharField(null=True, max_length=250)
	price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
	#unit = models.EnumField(choices=['LUMP SUM', 'PER YARD'])
	total_ordered = models.IntegerField(default=0)
	total_authorized = models.IntegerField(default=0)


class Subcontracts(models.Model):
	id = models.BigAutoField(primary_key=True)
	job_number = models.ForeignKey(Jobs, on_delete=models.CASCADE)
	subcontractor = models.ForeignKey(Subcontractors, on_delete=models.CASCADE)
	PO_number = models.CharField(null=True, max_length=250)
	total_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
	description = models.CharField(null=True, max_length=250)

class Subcontract_Items(models.Model):
	id = models.BigAutoField(primary_key=True)
	subcontract = models.ForeignKey(Subcontracts, on_delete=models.CASCADE)
	wallcovering_id = models.ForeignKey(Wallcovering, on_delete=models.CASCADE, null=True, blank=True)
	SOV_description = models.CharField(null=True, max_length=250)
	SOV_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
	is_closed = models.BooleanField(default=False)




class Submittals(models.Model):
	id = models.BigAutoField(primary_key=True)
	job_number = models.ForeignKey(Jobs, on_delete=models.CASCADE)
	description = models.CharField(null=True, max_length=2000)
	submittal_number = models.IntegerField(default=0)
	date_sent = models.DateTimeField(null=True, blank=True)
	date_returned = models.DateTimeField(null=True, blank=True)
	is_closed = models.BooleanField(default=False)
	notes = models.CharField(null=True, max_length=2000)
	def __str__(self):
		return f"{self.job_number} {self.description}"


class Submittal_Items(models.Model):
	id = models.BigAutoField(primary_key=True)
	submittal = models.ForeignKey(Submittals, on_delete=models.CASCADE)
	wallcovering_id = models.ForeignKey(Wallcovering, on_delete=models.CASCADE)
	description = models.CharField(null=True, max_length=250)
	quantity = models.IntegerField(default=0)
	is_closed = models.BooleanField(default=False)


class Job_Numbers(models.Model):
	letter = models.CharField(null=False, max_length=1)
	number = models.CharField(null=False, max_length=4)


class Rentals(models.Model):
	id = models.BigAutoField(primary_key=True)
	company = models.ForeignKey(Vendors, on_delete=models.CASCADE, null=True, blank=True)
	item = models.CharField(null=True, max_length=250)
	purchase_order = models.CharField(null=True, max_length=250)
	on_rent_date = models.DateTimeField(null=True, blank=True)
	off_rent_date = models.DateTimeField(null=True, blank=True)
	off_rent_number = models.CharField(null=True, max_length=250)
	notes = models.CharField(null=True, max_length=2000)
	job_number = models.ForeignKey(Jobs, on_delete=models.CASCADE)
	def __str__(self):
		return f"{self.job_name} {self.item}"


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


class Plans(models.Model):
	id = models.BigAutoField(primary_key=True)
	job_number = models.CharField(null=False, max_length=10)
	job_name = models.CharField(null=True, max_length=250)
	description = models.CharField(null=True, max_length=2000)
	estimates_number = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
