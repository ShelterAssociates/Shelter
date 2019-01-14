

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

		final_grand_total = Number(final_grand_total.toFixed(2));
		$("#id_final_total").val(final_grand_total);
	}
	
	$(".form-row>div>input").on('change',function(e){
		calculateGrandTotal();

	});

	$(document).on('change',$(".field-quantity>input, .field-rate>input, .field-tax>input, .vLargeTextField"),function(e){
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
		var hh_count = JSON.parse($("#id_invoiceitems_set-"+index+"-household_numbers").val()).length;
		var total = (hh_count*quantity*rate) + (hh_count*quantity*rate*tax)/100;
		total = Number(total.toFixed(2));
		$("#id_invoiceitems_set-"+index+"-total").val(total) ;
		calculateGrandTotal();
		
		if(document.getElementById("id_count_household"+index)){

			var newdiv = document.getElementById("id_count_household"+index);
			newdiv.innerText = "Total Number of Households = " + hh_count;
			
		}
		else{
			
			var newdiv = document.createElement("DIV");
			newdiv.setAttribute("id","id_count_household"+index);
			newdiv.appendChild(document.createTextNode("Total Number of Households = " + hh_count));
			$(".field-household_numbers")[index].appendChild(newdiv);
		}
		
	});

	$(".field-quantity").each(function(v,input){
		$(input).find('input').trigger('change');
	});


 });
