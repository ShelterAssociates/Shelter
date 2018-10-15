$(document).ready(function(){
	$(".field-quantity, .field-rate, .field-tax").change(function(){
		var quantity = 0.0;
		var rate = 0.0;
		var tax = 0.0;
		index = $(this).parents('tr').index();
		q_value = $("#id_invoiceitems_set-"+index+"-quantity").val();
		r_value = $("#id_invoiceitems_set-"+index+"-rate").val();
		t_value = $("#id_invoiceitems_set-"+index+"-tax").val();
		if( q_value!= '' && !isNaN(q_value)){
			quantity = parseInt($("#id_invoiceitems_set-"+index+"-quantity").val());
		}
		if ( r_value!= '' && !isNaN(r_value)){	
			 rate = parseInt($("#id_invoiceitems_set-"+index+"-rate").val());
		}
		if(t_value != '' && !isNaN(t_value)){
		 	tax = parseInt($("#id_invoiceitems_set-"+index+"-tax").val());
		}

		
		var total = (quantity*rate) + (quantity*rate*tax)/100;
		$("#id_invoiceitems_set-"+index+"-total").val(total) ;
			
		
	});
 });
