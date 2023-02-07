from django.db import models
from django.core.exceptions import ValidationError


def validate_tm_category(value):
	if value == "Labor" or value == "Material" or value == "Equipment" or value == "Inventory" or value == "Bond":
		return value
	else:
		raise ValidationError("Category must be Labor, Material, Equipment, Inventory, or Bond")



class Employees(models.Model):
	id = models.BigAutoField(primary_key=True)
	employee_number = models.IntegerField(default=0)
	title = models.CharField(null=True, max_length=50)
	active = models.BooleanField(default=True)
	first_name = models.CharField(null=True, max_length=50)
	last_name = models.CharField(null=True, max_length=50)
	phone = models.CharField(null=True, max_length=50)
	email = models.EmailField(null=True, blank=True)
	def __str__(self):
		return f"{self.first_name} {self.last_name}"


class Clients(models.Model):
	id = models.BigAutoField(primary_key=True)
	company = models.CharField(null=True, max_length=250)
	bid_fax = models.CharField(null=True, max_length=50)
	bid_email = models.EmailField(null=True, blank=True)
	vendor_code = models.CharField(null=True, max_length=100)
	address = models.CharField(null=True, max_length=100)
	city = models.CharField(null=True, max_length=100)
	state = models.CharField(null=True, max_length=100)
	phone = models.CharField(null=True, max_length=50)
	def __str__(self):
		return f"{self.company}"


class ClientEmployees(models.Model):
	person_pk = models.BigAutoField(primary_key=True)
	id = models.ForeignKey(Clients, on_delete=models.PROTECT)
	name = models.CharField(null=True, max_length=250)
	phone = models.CharField(null=True, max_length=50)
	email = models.EmailField(null=True, blank=True)
	title = models.CharField(null=True, max_length=250)
	def __str__(self):
		return f"{self.name}"



class Jobs(models.Model):
	job_number = models.CharField(null=False, max_length=5, primary_key=True)
	job_name = models.CharField(null=True, max_length=250)
	estimator = models.CharField(null=True, max_length=50)
	foreman = models.CharField(null=True, max_length=50, blank=True)
	superintendent = models.ForeignKey(Employees, on_delete=models.PROTECT, null=True)
	contract_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
	po_number = models.CharField(null=True, max_length=50, blank=True)
	retainage_percentage = models.CharField(null=True, max_length=50, blank=True)
	is_t_m_job = models.BooleanField(default=False)
	t_m_nte_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
	status = models.CharField(null=True, max_length=50) #open,closed
	booked_date = models.DateField(null=True, blank=True)
	booked_by = models.CharField(null=True, max_length=50, blank=True)
	is_wage_scale = models.BooleanField(default=False)
	is_davis_bacon_wages = models.BooleanField(default=False)
	spray_scale = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
	brush_role = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
	address = models.CharField(null=True, max_length=50)
	city = models.CharField(null=True, max_length=20)
	state = models.CharField(null=True, max_length=2)
	start_date = models.DateField(null=True, blank=True)
	duration = models.CharField(null=True, max_length=50, blank=True)
	estimate_number = models.CharField(null=True, max_length=50, blank=True)
	estimate_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
	has_wallcovering = models.BooleanField(default=False)
	has_paint = models.BooleanField(default=False)
	has_owner_supplied_wallcovering = models.BooleanField(default=False)
	painting_budget = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
	wallcovering_budget = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
	is_send_auto_co_emails = models.BooleanField(default=True)
	is_send_auto_submittal_emails = models.BooleanField(default=True)
	notes = models.CharField(null=True, max_length=2000, blank=True)
	approved_change_orders = models.DecimalField(max_digits=10, decimal_places=4, blank=True, null=True)
	final_bill_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
	is_closed = models.BooleanField(default=False)
	labor_done_Date = models.DateField(null=True, blank=True)
	ar_closed_date = models.DateField(null=True, blank=True)
	was_previously_closed = models.BooleanField(default=False)
	previously_closed_date = models.DateField(null=True, blank=True)
	cumulative_costs_at_closing = models.DecimalField(max_digits=9, decimal_places=2, blank=True, null=True)
	contract_status = models.IntegerField()
	insurance_status = models.IntegerField()
	submittals_required = models.IntegerField(null=True)
	has_special_paint = models.IntegerField(null=True)
	client = models.ForeignKey(Clients, related_name="Client", on_delete=models.PROTECT)
	client_Pm = models.ForeignKey(ClientEmployees, related_name="PM", on_delete=models.PROTECT, blank=True, null=True)
	client_Pm_Phone = models.CharField(null=True, max_length=50, blank=True)
	client_Pm_Email = models.EmailField(null=True, blank=True)
	client_Co_Contact = models.ForeignKey(ClientEmployees, related_name="CO", on_delete=models.PROTECT, null=True)
	client_Co_Email = models.EmailField(null=True, blank=True)
	client_Submittal_Contact = models.ForeignKey(ClientEmployees, related_name="Submittals", on_delete=models.PROTECT, null=True)
	client_Submittal_Email = models.EmailField(null=True, blank=True)
	client_Super = models.ForeignKey(ClientEmployees, related_name="Super", on_delete=models.PROTECT, null=True, blank =True)
	client_Super_Phone = models.CharField(max_length=50, blank=True, null=True)
	client_Super_Email = models.EmailField(null=True, blank=True)
	is_on_base = models.BooleanField(default=False)
	unsigned_tickets = models.IntegerField(null=True, blank=True)
	assigned_inventory = models.IntegerField(null=True, blank=True)
	assigned_rentals = models.IntegerField(null=True, blank=True)
	is_bonded = models.BooleanField(default=False)
	is_active = models.BooleanField(default=False)
	start_date_checked = models.DateField(null=True, blank=True)
	def __str__(self):
		return f"{self.job_name}"


class ClientJobRoles(models.Model):
	id = models.BigAutoField(primary_key=True)
	employee = models.ForeignKey(ClientEmployees, on_delete=models.PROTECT, related_name='roles')
	job = models.ForeignKey(Jobs, on_delete=models.PROTECT)
	role = models.CharField(max_length=100) #Submittals, #Change Orders, anything else
	notes = models.CharField(max_length=2000,blank=True)
	def __str__(self):
		return f"{self.job} {self.role} {self.employee}"

class InventoryType(models.Model):
	id = models.BigAutoField(primary_key=True)
	#id = models.IntegerField(primary_key=True)
	type = models.CharField(null=True, max_length=50)
	is_active = models.BooleanField(default=True)
	def __str__(self):
		return f"{self.type}"

class InventoryItems(models.Model):
	id = models.BigAutoField(primary_key=True)
	type = models.ForeignKey(InventoryType,on_delete=models.PROTECT)
	name = models.CharField(null=True, max_length=100)
	def __str__(self):
		return f"{self.type} {self.name}"

class InventoryItems2(models.Model):
	id = models.BigAutoField(primary_key=True)
	type = models.ForeignKey(InventoryItems,on_delete=models.PROTECT)
	name = models.CharField(null=True, max_length=100)
	def __str__(self):
		return f"{self.type} {self.name}"

class InventoryItems3(models.Model):
	id = models.BigAutoField(primary_key=True)
	type = models.ForeignKey(InventoryItems2,on_delete=models.PROTECT)
	name = models.CharField(null=True, max_length=100)
	def __str__(self):
		return f"{self.type} {self.name}"

class InventoryItems4(models.Model):
	id = models.BigAutoField(primary_key=True)
	type = models.ForeignKey(InventoryItems3,on_delete=models.PROTECT)
	name = models.CharField(null=True, max_length=100)
	def __str__(self):
		return f"{self.type} {self.name}"

class StorageLocationType(models.Model):
	id = models.IntegerField(primary_key=True)
	type = models.CharField(null=True, max_length=50)
	is_active = models.BooleanField(default=False)
	def __str__(self):
		return f"{self.type}"


class Checklist(models.Model):
	id = models.BigAutoField(primary_key=True)
	category = models.CharField(null=True, max_length=1000)
	checklist_item = models.CharField(null=True, max_length=2000)
	is_closed = models.BooleanField(default=False)
	job_number = models.ForeignKey(Jobs,on_delete=models.PROTECT)
	notes = models.CharField(null=True, max_length=2500)
	job_start_date_from_schedule = models.DateField(null=True, blank=True)
	cop = models.BooleanField(default=False)
	cop_amount = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)
	cop_sent_date = models.DateField(null=True, blank=True)
	cop_number = models.IntegerField(default=0)
	is_ewt = models.BooleanField(default=False)
	ewt_date = models.DateField(null=True, blank=True)
	is_submittal = models.BooleanField(default=False)
	submittal_number = models.IntegerField(default=0)
	submittal_description = models.CharField(null=True, max_length=2000)
	submittal_date_sent = models.DateField(null=True, blank=True)
	wallcovering_order_date = models.DateField(null=True, blank=True)
	assigned = models.CharField(null=True, max_length=2000)
	def __str__(self):
		return f"{self.job_number} {self.checklist_item}"


def validate_job_notes(value):
	if value == "auto_booking_note" or value == "employee_note" or value == "auto_co_note" or value == "auto_submittal_note" or value == "auto_start_date_note" or value == "daily_report":
		return value
	else:
		raise ValidationError("Category Not Allowed")


class JobNotes(models.Model):
	id = models.BigAutoField(primary_key=True)
	job_number = models.ForeignKey(Jobs,on_delete=models.PROTECT)
	note = models.CharField(null=True, max_length=2000)
	type = models.CharField(null=True, max_length=50,validators = [validate_job_notes])  #booking note, field note, CO note, submittal note, start date note, daily report, etc
	user = models.CharField(null=True, max_length=50) #bridgette joe
	date = models.DateField(null=True, blank=True)
	daily_employee_count = models.IntegerField(default=0)
	note_date = models.DateField(null=True, blank=True) #use if you are having to back date a daily report
	def __str__(self):
		return f"{self.job_number} {self.type}"


class VendorCategory(models.Model): #Equipment Rental, Wallcovering Supplier
	id = models.BigAutoField(primary_key=True)
	category = models.CharField(null=True, max_length=250)
	def __str__(self):
		return f"{self.category}"


class Vendors(models.Model):
	id = models.BigAutoField(primary_key=True)
	company_name = models.CharField(null=True, max_length=250)
	category = models.ForeignKey(VendorCategory,on_delete=models.PROTECT, null=True, blank=True)
	company_phone = models.CharField(null=True, max_length=20, blank=True)
	company_email = models.EmailField(null=True, blank=True)
	def __str__(self):
		return f"{self.company_name}"

class Inventory(models.Model):
	id = models.BigAutoField(primary_key=True)
	number = models.CharField(null=True, max_length=50,blank = True)
	item = models.CharField(null=True, max_length=2000)
	inventory_type = models.ForeignKey(InventoryType,on_delete=models.PROTECT)
	storage_location = models.CharField(null=True, max_length=50, blank=True)
	purchase_date = models.DateField(null=True, blank=True)
	purchase_price = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)
	purchased_from = models.ForeignKey(Vendors,on_delete=models.PROTECT, blank=True, null=True,related_name = 'inventory1')
	purchased_by = models.CharField(null=True, max_length=250, blank=True)
	serial_number = models.CharField(null=True, max_length=250, blank=True)
	po_number = models.CharField(null=True, max_length=250, blank=True)
	is_labeled = models.BooleanField(default=False)
	status = models.CharField(null=True, max_length=250, blank=True) #checked out, missing, available, service
	date_out = models.DateField(null=True, blank=True)
	date_returned = models.DateField(null=True, blank=True)
	job_number = models.ForeignKey(Jobs,on_delete=models.PROTECT, blank=True, null=True)
	# job_number is the foreign key to the job number in Jobs
	notes = models.CharField(null=True, max_length=2000, blank=True)
	service_vendor = models.ForeignKey(Vendors,on_delete=models.PROTECT, blank=True, null=True,related_name = 'inventory2')
	batch = models.CharField(null=True, max_length=50, blank=True) #outgoing or incoming
	def __str__(self):
		return f"{self.inventory_type} {self.item}"


def validate_inventory_notes(value):
	if value == "Returned" or value == "Missing" or value == "Job" or value == "Service" or value == "Misc":
		return value
	else:
		raise ValidationError("Category must be Returned, Missing, Job, Service, or Misc")

class InventoryNotes(models.Model):
	id = models.BigAutoField(primary_key=True)
	inventory_item = models.ForeignKey(Inventory, on_delete=models.PROTECT)
	date = models.DateField(null=True, blank=True)
	user = models.CharField(null=True,max_length=20)
	note = models.CharField(null=True, max_length=2000)
	category = models.CharField(null=True, max_length=2000, validators = [validate_inventory_notes]) #newjob, service, misc, returned
	job_number = models.CharField(null=True,max_length=5, blank = True)
	job_name = models.CharField(null=True, max_length=2000, blank=True) #either job name, or service vendor


class BatchInventory(models.Model):
	id = models.BigAutoField(primary_key=True)
	job_number = models.ForeignKey(Jobs, on_delete=models.PROTECT,related_name = 'batch1')
	date = models.DateField(null=True, blank=True)
	status = models.CharField(null=True,max_length=50) #incoming or outgoing
	current = models.BooleanField(default=False) #true means it is the latest one


class BatchInventoryItems:
	id = models.BigAutoField(primary_key=True)
	batchinventory = models.ForeignKey(BatchInventory, on_delete=models.PROTECT,related_name = 'batchitem1')
	inventory = models.ForeignKey(Inventory, on_delete=models.PROTECT,related_name = 'batchitem2')

class ChangeOrders(models.Model):
	id = models.BigAutoField(primary_key=True)
	job_number = models.ForeignKey(Jobs,on_delete=models.PROTECT)
	cop_number = models.IntegerField(default=0)
	is_t_and_m = models.BooleanField(default=False)
	description = models.CharField(null=True,max_length=700)
	date_sent = models.DateField(null=True, blank=True)
	date_approved = models.DateField(null=True, blank=True)
	gc_number = models.IntegerField(default=0, null=True, blank=True)
	is_approved = models.BooleanField(default=False)
	is_closed = models.BooleanField(default=False)
	notes = models.CharField(null=True,max_length=1000, blank=True)
	is_work_complete = models.BooleanField(default=False)
	is_ticket_signed = models.BooleanField(default=False)
	date_signed = models.DateField(null=True, blank=True)
	date_week_ending= models.DateField(null=True, blank=True)
	ticket_description = models.CharField(null=True,max_length=2000, blank=True)
	materials_used = models.CharField(null=True,max_length=2000, blank=True)
	price = models.DecimalField(max_digits=9, decimal_places=2,null=True)
	full_description = models.CharField(null=True,max_length=2000, blank=True)
	is_approved_to_bill = models.BooleanField(default=False)
	def __str__(self):
		return f"{self.job_number} {self.description}"

	def need_ticket(self):
		if self.is_t_and_m==True and self.is_ticket_signed==False and self.is_closed==False:
			return "Yes"
		else:
			return "No"


class ChangeOrderNotes(models.Model):
	id = models.BigAutoField(primary_key=True)
	cop_number = models.ForeignKey(ChangeOrders, on_delete=models.PROTECT)
	date = models.DateField(null=True, blank=True)
	user = models.CharField(null=True,max_length=20)
	note = models.CharField(null=True, max_length=2000)


class PainterHours(models.Model):
	id = models.BigAutoField(primary_key=True)
	cop_number = models.ForeignKey(ChangeOrders, on_delete=models.PROTECT)
	details = models.CharField(null=False, max_length=2000) #hector was bondoing door frames
	employee = models.ForeignKey(Employees, on_delete=models.PROTECT)
	monday = models.IntegerField(default=0)
	tuesday = models.IntegerField(default=0)
	wednesday = models.IntegerField(default=0)
	thursday = models.IntegerField(default=0)
	friday = models.IntegerField(default=0)
	saturday = models.IntegerField(default=0)
	sunday = models.IntegerField(default=0)
	is_overtime = models.BooleanField(default=False)


class TMPricesMaster(models.Model):
	id = models.BigAutoField(primary_key=True)
	category = models.CharField(null=False, max_length=50, validators = [validate_tm_category]) #labor, material, equipment, bond, inventory
	item = models.CharField(null=False, max_length=50) #painter-hours, latex paint, 19' scissor
	unit = models.CharField(null=False, max_length=50) #gallons, hours
	rate = models.DecimalField(max_digits=9, decimal_places=2)
	def __str__(self):
		return f"{self.item}"


class TMList(models.Model): #one entry for each line item of t&m bill
	id = models.BigAutoField(primary_key=True)
	change_order = models.ForeignKey(ChangeOrders,on_delete=models.PROTECT)
	item = models.CharField(null=False, max_length=50) #painter hours, latex paint
	quantity = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
	units = models.CharField(null=False, max_length=10)
	rate = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
	total = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)
	category = models.CharField(null=False, max_length=50, validators = [validate_tm_category])  #labor, material, equipment, bond, inventory
	notes = models.CharField(null=True, max_length=2000)
	week_ending = models.DateField(null=True)
	def __str__(self):
		return f"{self.change_order} {self.item}"





class VendorContact(models.Model):
	id = models.BigAutoField(primary_key=True)
	company = models.ForeignKey(Vendors, on_delete=models.PROTECT, null=True, blank=True)
	name = models.CharField(null=True, max_length=250)
	email = models.EmailField(null=True, blank=True)
	phone = models.CharField(null=True, max_length=20)
	def __str__(self):
		return f"{self.company} {self.name}"


class Wallcovering(models.Model):
	id = models.BigAutoField(primary_key=True)
	job_number = models.ForeignKey(Jobs,on_delete=models.PROTECT)
	code = models.CharField(null=True, max_length=10) #wc1, etc.
	vendor = models.ForeignKey(Vendors,on_delete=models.PROTECT)
	pattern = models.CharField(null=True, max_length=2000)
	estimated_quantity = models.IntegerField(default=0,blank=True)
	estimated_unit = models.CharField(null=True, max_length=20,blank=True)
	cut_charge = models.CharField(null=True, max_length=1000, blank=True)
	roll_width = models.CharField(null=True, max_length=50, blank=True)
	vertical_repeat = models.CharField(null=True, max_length=50, blank=True)
	is_random_reverse = models.BooleanField(default=False)
	is_repeat = models.BooleanField(default=False)
	notes = models.CharField(null=True, max_length=2000, blank=True)
	qnty_ordered = models.IntegerField(blank=True, null=True)#not used
	qnty_received = models.IntegerField(blank=True, null=True)#not used
	packages_received = models.IntegerField(blank=True, null=True)#not used
	packages_sent = models.IntegerField(blank=True, null=True)#not used

	def __str__(self):
		return f"{self.job_number} {self.code}"

	def quantity_ordered(self):
		totalquantity=0
		for x in OrderItems.objects.filter(wallcovering=self):
			totalquantity = totalquantity + x.quantity
		return totalquantity

	def quantity_received(self):
		totalquantity=0
		for x in OrderItems.objects.filter(wallcovering=self):
			totalquantity = totalquantity + x.quantity_received()
		return totalquantity

	def packages_received(self):
		totalquantity = 0
		for y in Orders.objects.filter(orderitems2__isnull=False, job_number=self.job_number, orderitems2__wallcovering=self).distinct(): #these are all orders with packages
			totalquantity = totalquantity + y.packages_received()
		return totalquantity

	def packages_sent(self):
		totalquantity = 0
		totalquantity = 0
		for y in Orders.objects.filter(orderitems2__isnull=False, job_number=self.job_number, orderitems2__wallcovering=self).distinct(): #these are all orders with packages
			totalquantity = totalquantity + y.packages_sent()
		return totalquantity


class WallcoveringPricing(models.Model):
	id = models.BigAutoField(primary_key=True)
	wallcovering = models.ForeignKey(Wallcovering, on_delete=models.PROTECT)
	quote_date= models.DateField()
	min_yards = models.IntegerField(blank=True, null=True)
	price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
	unit = models.CharField(null=True, max_length=50, blank=True)
	note = models.CharField(null=True, max_length=2000, blank=True)




class Orders(models.Model): #one pattern, one WC1, etc. may be broken up into several packages
	id = models.BigAutoField(primary_key=True)
	po_number = models.CharField(max_length=25)
	job_number = models.ForeignKey(Jobs,on_delete=models.PROTECT)
	vendor = models.ForeignKey(Vendors,on_delete=models.PROTECT, null=True, blank=True)
	description = models.CharField(max_length=2000) #this is for if there are multiple patterns ordered'
	date_ordered = models.DateField(null=True, blank=True)
	partial_receipt = models.BooleanField(default=False)
	notes = models.CharField(null=True, max_length=2000, blank=True) #DONT USE THIS, USE ORDERITEMS
	def __str__(self):
		return f"{self.job_number} {self.description}"

	def quantity_ordered(self):
		totalquantity=0
		for x in Orderitems.objects.filter(order=self):
			totalquantity = totalquantity + x.quantity
		return totalquantity

	def quantity_received(self):
		totalquantity=0
		for x in Orderitems.objects.filter(order=self):
			totalquantity = totalquantity + x.quantity_received()
		return totalquantity
	def packages_received(self):
		totalquantity=0
		for x in Packages.objects.filter(delivery__order=self):
			totalquantity=totalquantity + x.quantity_received
		return totalquantity
	def packages_sent(self):
		totalquantity=0
		for x in OutgoingItem.objects.filter(package__delivery__order=self):
			totalquantity=totalquantity+x.quantity_sent
		return totalquantity


class OrderItems(models.Model): #usually just one of these per order
	id = models.BigAutoField(primary_key=True)
	order = models.ForeignKey(Orders, on_delete=models.PROTECT, related_name = 'orderitems2')
	wallcovering = models.ForeignKey(Wallcovering, on_delete=models.PROTECT, related_name = 'orderitems1', null=True, blank=True)
	quantity = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True,verbose_name='Quantity Ordered')
	unit = models.CharField(null=True, max_length=10)
	price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
	item_description = models.CharField(null=True, max_length=100)
	item_notes = models.CharField(null=True, max_length=1000, blank = True)
	is_satisfied = models.BooleanField(default=False) #all has been received

	def __str__(self):
		return f"{self.item_description}"

	def quantity_received(self):
		totalquantity=0
		for x in ReceivedItems.objects.filter(order_item=self):
			totalquantity=totalquantity+x.quantity
		return totalquantity


class WallcoveringDelivery(models.Model): #one instance when receiving material. actual items listed below
	id = models.BigAutoField(primary_key=True)
	order = models.ForeignKey(Orders, on_delete=models.PROTECT,related_name="foreign_wallcoveringdelivery")
	date = models.DateField(null=True, blank=True)
	notes = models.CharField(null=True, max_length=2000,blank=True) #box, bolt, bucket
	def __str__(self):
		return f"{self.date} {self.order.job_number}"


class ReceivedItems(models.Model):
	id = models.BigAutoField(primary_key=True)
	wallcovering_delivery = models.ForeignKey(WallcoveringDelivery, on_delete=models.PROTECT, related_name="foreign_receiveditems1")
	order_item = models.ForeignKey(OrderItems, on_delete=models.PROTECT,related_name="foreign_receiveditems2")  # j-trim
	quantity = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
	def __str__(self):
		return f"{self.wallcovering_delivery.date} {self.order_item.item_description}"

class Packages(models.Model):
	id = models.BigAutoField(primary_key=True)
	delivery = models.ForeignKey(WallcoveringDelivery, on_delete=models.PROTECT, related_name="foreign_packages")
	type = models.CharField(null=True, max_length=200) #box, bolt, bucket
	contents = models.CharField(null=True, max_length=2000) #Wallprotection, FRP glue,
	quantity_received = models.IntegerField(default=0, verbose_name='Packages Received') #3
	notes = models.CharField(null=True, max_length=2000, blank=True)
	def __str__(self):
		return f"{self.delivery.order.job_number} {self.contents}"
	def total_sent(self):
		totalquantity=0
		for x in OutgoingItem.objects.filter(package=self):
			totalquantity=totalquantity+x.quantity_sent
		return totalquantity


class OutgoingWallcovering(models.Model):
	id = models.BigAutoField(primary_key=True)
	job_number = models.ForeignKey(Jobs, on_delete=models.PROTECT, blank=True, null=True)
	delivered_by = models.CharField(null=True, max_length=200)
	notes = models.CharField(null=True, max_length=2000)
	date = models.DateField(null=True, blank=True)
	def __str__(self):
		return f"{self.job_number} {self.date}"


class OutgoingItem(models.Model):
	id = models.BigAutoField(primary_key=True)
	outgoing_event = models.ForeignKey(OutgoingWallcovering, on_delete=models.PROTECT)
	package = models.ForeignKey(Packages, on_delete=models.PROTECT)
	description = models.CharField(null=True, max_length=200)
	quantity_sent = models.IntegerField(default=0,verbose_name='Packages Sent to Job')
	def __str__(self):
		return f"{self.description}"


class Subcontractors(models.Model):
	id = models.BigAutoField(primary_key=True)
	company = models.CharField(null=True, max_length=250)
	contact = models.CharField(null=True, max_length=250, blank=True)
	phone = models.CharField(null=True, max_length=20, blank=True)
	email = models.EmailField(null=True, blank=True)
	insurance_expire_date = models.DateField(blank=True,null=True)
	is_signed_labor_agreement = models.BooleanField(default=False)
	notes = models.CharField(null=True, max_length=2000, blank=True)
	def __str__(self):
		return f"{self.company}"


	def active_contracts(self):
		totalquantity=0
		for x in Subcontracts.objects.filter(subcontractor=self, is_closed = False):
			totalquantity=totalquantity+1
		return totalquantity

class Subcontracts(models.Model):
	id = models.BigAutoField(primary_key=True)
	job_number = models.ForeignKey(Jobs, on_delete=models.PROTECT)
	subcontractor = models.ForeignKey(Subcontractors, on_delete=models.PROTECT, related_name="subcontract")
	po_number = models.CharField(null=True, max_length=250)
	total_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True) #DONT USE
	notes = models.CharField(null=True, max_length=2000)
	date = models.DateField(null=True, blank=True)
	is_closed = models.BooleanField(default=False)
	is_retainage = models.BooleanField(default=True)
	retainage_percentage = models.DecimalField(max_digits=4, decimal_places=2, blank=True, null=True)
	def __str__(self):
		return f"{self.subcontractor} {self.job_number}"

	def total_billed(self):
		total=0
		for x in SubcontractorInvoice.objects.filter(subcontract=self, is_sent=True):
			total=total + x.final_amount
		return total

	def total_retainage(self):
		total=0
		for x in SubcontractorInvoice.objects.filter(subcontract=self, is_sent=True):
			total = total + x.retainage
		return total

class SubcontractItems(models.Model):
	id = models.BigAutoField(primary_key=True)
	subcontract = models.ForeignKey(Subcontracts, on_delete=models.PROTECT)
	is_closed = models.BooleanField(default=False)
	wallcovering_id = models.ForeignKey(Wallcovering, on_delete=models.PROTECT, null=True, blank=True)
	SOV_description = models.CharField(null=True, max_length=250) #install WC1
	SOV_total = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True) #$1,050 - NOT USING THIS RIGHT NOW
	SOV_is_lump_sum = models.BooleanField(default=False)
	SOV_unit = models.CharField(null=True, max_length=50) #yards, SF, hour, lump sum
	SOV_total_ordered = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)  #1,000 yards.  $15,000 if lump sum.
	SOV_total_authorized = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True) #not used right now
	SOV_quantity_to_date = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True) #not used right now
	SOV_rate = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True) #if lump sum, this is the same as total_ordered
	notes = models.CharField(null=True, max_length=2050, blank=True)
	date = models.DateField()
	def __str__(self):
		return f"{self.subcontract} {self.SOV_description}"

	def total_cost(self):
		totalcost = 0
		if self.SOV_is_lump_sum == True:
			totalcost = self.SOV_rate
		else:
			totalcost = self.SOV_total_ordered * self.SOV_rate
		return totalcost

	def quantity_billed(self):
		totalcost = float(0.00)
		for x in SubcontractorInvoiceItem.objects.filter(sov_item=self, invoice__is_sent=True):
			totalcost = float(totalcost) + float(x.quantity)
		if self.SOV_is_lump_sum == True:
			totalcost = float(totalcost) / float(self.SOV_rate)
		return totalcost

	def total_billed(self):
		totalcost = 0
		for x in SubcontractorInvoiceItem.objects.filter(sov_item=self, invoice__is_sent=True):
			if x.invoice.is_sent == True:
				totalcost = totalcost + x.quantity
		if self.SOV_is_lump_sum == False:
			totalcost = totalcost * self.SOV_rate
		return totalcost
class SubcontractorInvoice(models.Model):
	id = models.BigAutoField(primary_key=True)
	date = models.DateField()
	pay_app_number = models.IntegerField(default=0)
	subcontract = models.ForeignKey(Subcontracts, on_delete=models.PROTECT, related_name="invoice")
	retainage = models.DecimalField(max_digits=10, decimal_places=2, null=True)
	final_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True)
	is_sent = models.BooleanField(default=False)
	notes = models.CharField(null=True, max_length=2000, blank=True) #DONT USE
	def __str__(self):
		return f"{self.subcontract} {self.pay_app_number}"
class SubcontractorInvoiceItem(models.Model):
	id = models.BigAutoField(primary_key=True)
	invoice = models.ForeignKey(SubcontractorInvoice, on_delete=models.PROTECT, related_name="invoice_item")
	sov_item = models.ForeignKey(SubcontractItems, on_delete=models.PROTECT, related_name="invoice_item2")
	quantity = models.DecimalField(max_digits=10, decimal_places=2)
	notes = models.CharField(null=True, max_length=2000, blank=True)
	def __str__(self):
		return f"{self.invoice} {self.sov_item}"
	def total_cost(self):
		totalcost = 0
		if self.sov_item.SOV_is_lump_sum == False:
			totalcost = self.quantity * self.sov_item.SOV_rate
		else:
			totalcost = self.quantity
		return totalcost
class Submittals(models.Model):
	id = models.BigAutoField(primary_key=True)
	job_number = models.ForeignKey(Jobs, on_delete=models.PROTECT)
	description = models.CharField(null=True, max_length=2000)
	submittal_number = models.IntegerField(default=0)
	date_sent = models.DateField(null=True, blank=True)
	date_returned = models.DateField(null=True, blank=True)
	is_closed = models.BooleanField(default=False)
	notes = models.CharField(null=True, max_length=2000, blank=True)
	def __str__(self):
		return f"{self.job_number} {self.description}"


class SubmittalItems(models.Model):
	id = models.BigAutoField(primary_key=True)
	submittal = models.ForeignKey(Submittals, on_delete=models.PROTECT)
	wallcovering_id = models.ForeignKey(Wallcovering, on_delete=models.PROTECT)
	description = models.CharField(null=True, max_length=250)
	quantity = models.IntegerField(default=0)
	is_closed = models.BooleanField(default=False)
	def __str__(self):
		return f"{self.submittal} {self.description}"



class JobNumbers(models.Model):
	letter = models.CharField(null=False, max_length=1)
	number = models.CharField(null=False, max_length=4)


class Rentals(models.Model):
	id = models.BigAutoField(primary_key=True)
	company = models.ForeignKey(Vendors, on_delete=models.PROTECT, null=True, blank=True)
	item = models.CharField(null=True, max_length=250)
	purchase_order = models.CharField(null=True, max_length=250,blank=True)
	on_rent_date = models.DateField(null=True, blank=True)
	off_rent_date = models.DateField(null=True, blank=True)
	off_rent_number = models.CharField(null=True, max_length=250, blank=True)
	notes = models.CharField(null=True, max_length=2000)
	job_number = models.ForeignKey(Jobs, on_delete=models.PROTECT)
	day_price = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
	week_price = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
	month_price = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
	is_closed = models.BooleanField(default=False) #once accounting has invoiced
	def __str__(self):
		return f"{self.job_number} {self.item}"


class Estimates(models.Model):
	id = models.BigAutoField(primary_key=True)
	to_number = models.IntegerField(default=0)
	bid_date = models.DateField(null=True, blank=True)
	take_off_name = models.CharField(null=True, max_length=2000)
	estimator = models.CharField(null=True, max_length=250)
	bidders = models.CharField(null=True, max_length=250)
	has_docs_print = models.BooleanField(default=False)
	#estimate_status = models.enum.EnumField(choices=['Awarded','Bid Sent','Not Bidding', 'In Progress', 'To Joe', 'T/O Done'])
	comments = models.CharField(null=True, max_length=2000)
	addenda = models.IntegerField(default=0)
	site_visit_date = models.DateField(null=True, blank=True)
	client_estimator_name = models.CharField(null=True, max_length=250)
	client_estimator_email = models.EmailField(null=True, blank=True)
	client_phone = models.CharField(null=True, max_length=50)
	send_bids_to_email = models.EmailField(null=True, blank=True)
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

class SubcontractNotes(models.Model):
	id = models.BigAutoField(primary_key=True)
	subcontract = models.ForeignKey(Subcontracts, on_delete=models.PROTECT, related_name="subcontract_notes")
	date = models.DateField(null=True, blank=True)
	user = models.CharField(null=True,max_length=200)
	note = models.CharField(null=True, max_length=2000)
	invoice = models.ForeignKey(SubcontractorInvoice, null=True, on_delete=models.PROTECT, related_name="subcontract_notes2")
