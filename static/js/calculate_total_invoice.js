

$(document).ready(function(){
	
	

	function calculateGrandTotal(){
		var grand_total = 0;

		$(".field-total>input").each(function(v,input){
			grand_total += parseFloat($(input).val());

		});

		$("#id_total").val(grand_total);
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
		calculateGrandTotal();
	});

	$(".field-quantity").each(function(v,input){
		$(input).find('input').trigger('change');
	});


 });
