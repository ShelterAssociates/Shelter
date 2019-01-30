from __future__ import division

import xlwt
from xlwt import Workbook
import collections
from mastersheet.models import *



def accounts_excel_generation():
    wb = Workbook()
    sheet1 = wb.add_sheet('Sheet1')
    sheet1.write(0, 0,'Date')
    sheet1.write(0, 1,'Invoice No')
    sheet1.write(0, 2,'Name of Vendor')
    sheet1.write(0, 3, 'Donar Name')
    sheet1.write(0, 4, 'City')
    sheet1.write(0, 5, 'Slum')
    sheet1.write(0, 6, 'House No')
    sheet1.write(0, 7, 'Phase I')
    sheet1.write(0, 8, 'Phase II')
    sheet1.write(0, 9, 'Phase III')
    sheet1.write(0, 10, 'Type of Material')
    sheet1.write(0, 11, 'Quantity')
    sheet1.write(0, 12, 'Rate')
    sheet1.write(0, 13, 'Gross Amount')
    sheet1.write(0, 14, 'Tax Rate')
    sheet1.write(0, 15, 'Tax Amount')
    sheet1.write(0, 16, 'Transport Charges')
    sheet1.write(0, 17, 'Unloading Charges')
    sheet1.write(0, 18, 'Amount')

    invoiceItems = InvoiceItems.objects.filter(slum__id = 1094)
    dict_of_dict = collections.defaultdict(dict)


    for i in invoiceItems:
        for j in i.household_numbers:
            try:
                dict_of_dict[(j, i.slum)].update({i.material_type:i})
            except:
                dict_of_dict[(j, i.slum)] = {i.material_type:i}
           
    i = 1
    for k,v in dict_of_dict.iteritems():
        for inner_k, inner_v in v.iteritems():
            print i
            sheet1.write(i, 0, inner_v.invoice.invoice_date)
            sheet1.write(i, 1, inner_v.invoice.invoice_number)
            sheet1.write(i, 2, inner_v.invoice.vendor.name)
            sheet1.write(i, 3, 'Donar Name')
            sheet1.write(i, 4, inner_v.slum.electoral_ward.administrative_ward.city.name.city_name)
            sheet1.write(i, 5, inner_v.slum.name)
            sheet1.write(i, 6, k[0])
            if inner_v.phase == '1':
                sheet1.write(i, 7, 'Phase - I')
            if inner_v.phase == '2':
                sheet1.write(i, 8, 'Phase - II')
            if inner_v.phase == '3':
                sheet1.write(i, 9, 'Phase - III')
           
            sheet1.write(i, 10, inner_k.name)
            sheet1.write(i, 11, inner_v.quantity)
            sheet1.write(i, 12, inner_v.rate)
            sheet1.write(i, 13, inner_v.quantity * inner_v.rate)
            sheet1.write(i, 14, inner_v.tax)
            sheet1.write(i, 15, round((float(inner_v.tax)/100) * float(inner_v.quantity) * float(inner_v.rate) , 2))
            sheet1.write(i, 16, inner_v.invoice.transport_charges)
            sheet1.write(i, 17, inner_v.invoice.loading_unloading_charges)
            sheet1.write(i, 18, inner_v.total)  
            i = i + 1
            print i
        
    wb.save('/home/ubuntu/aa.xlsx')

accounts_excel_generation()