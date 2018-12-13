

$(document).ready(function(){
	
	

	function calculateGrandTotal(){
		var grand_total = 0;
		var final_grand_total = 0;
		$(".field-total>input").each(function(v,input){
			grand_total += parseFloat($(input).val());

		});

		var round_off = $("#id_roundoff").val();
		if( round_off!= '' && !isNaN(round_off)){
			round_off = parseFloat($("#id_roundoff").val());
		}

		var l_u_charges = $("#id_loading_unloading_charges").val();
		if( l_u_charges!= '' && !isNaN(l_u_charges)){
			l_u_charges = parseFloat($("#id_loading_unloading_charges").val());
		}

		var transport_charges = $("#id_transport_charges").val();
		if( transport_charges!= '' && !isNaN(transport_charges)){
			transport_charges = parseFloat($("#id_transport_charges").val());
		}
		$("#id_total").val(grand_total);
		final_grand_total = grand_total + round_off + l_u_charges + transport_charges;

		$("#id_final_total").val(final_grand_total);
	}
	
	

	$(document).on('change',$(".field-quantity>input, .field-rate>input, .field-tax>input"),function(e){
		var quantity = 0.0;
		var rate = 0.0;
		var tax = 0.0;
		var grand_total = $("#id_total").val();
		index = $(e.target).parent().parent().index();
		q_value = $("#id_invoiceitems_set-"+index+"-quantity").val();
		r_value = $("#id_invoiceitems_set-"+index+"-rate").val();
		t_value = $("#id_invoiceitems_set-"+index+"-tax").val();
		if( q_value!= '' && !isNaN(q_value)){
			quantity = parseFloat($("#id_invoiceitems_set-"+index+"-quantity").val());
		}
		if ( r_value!= '' && !isNaN(r_value)){	
			 rate = parseFloat($("#id_invoiceitems_set-"+index+"-rate").val());
		}
		if(t_value != '' && !isNaN(t_value)){
		 	tax = parseFloat($("#id_invoiceitems_set-"+index+"-tax").val());
		}

		var total = (quantity*rate) + (quantity*rate*tax)/100;
		$("#id_invoiceitems_set-"+index+"-total").val(total) ;
		calculateGrandTotal();
	});

	$(".field-quantity").each(function(v,input){
		$(input).find('input').trigger('change');
	});


 });
