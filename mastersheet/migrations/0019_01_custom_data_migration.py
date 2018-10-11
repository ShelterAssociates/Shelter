from mastersheet.models import *
from master.models import *
from django.contrib.auth.models import User

user = User.objects.get(username = 'shelter')   	
vh = VendorHouseholdInvoiceDetail.objects.all()

v = Vendor.objects.all()

for i in v:
 for j in vh:
  if i == j.vendor:
   invoices = Invoice.objects.filter(invoice_number = j.invoice_number)
   if len(invoices) == 0:
    
    mt = MaterialType.objects.get(name = j.vendor.vendor_type.name)
    new_invoice = Invoice(vendor = i, invoice_number = j.invoice_number, created_by = user, modified_by = user)
    new_invoice.save()
    new_invoice_item = InvoiceItems(invoice_item_details = new_invoice, material_type = mt, slum = j.slum, household_numbers = j.household_number, created_by = user, modified_by= user)
    new_invoice_item.save()
    new_invoice.invoiceitems_set.add(new_invoice_item)
   if len(invoices) != 0:
    for k in invoices:
     mt = MaterialType.objects.get(name = j.vendor.vendor_type.name)
     new_invoice_item = InvoiceItems(invoice_item_details = k, material_type = mt, slum = j.slum, household_numbers = j.household_number, created_by = user, modified_by= user)
     new_invoice_item.save()
     print new_invoice_item
     k.invoiceitems_set.add(new_invoice_item)