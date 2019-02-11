$(document).ready(function(){

	

})

function copy_this(e){
		index = $(e).parents('tr').index();
		// console.log($(e).parents('tr').index());
		$(".add-row").children().children()[0].click();
		material_type = $('#id_invoiceitems_set-'+String(index)+'-material_type').find(":selected").val();
		phase = $('#id_invoiceitems_set-'+String(index)+'-phase').find(":selected").val();
		unit = $('#id_invoiceitems_set-'+String(index)+'-unit').find(":selected").val();
		slum = $('#id_invoiceitems_set-'+String(index)+'-slum').val();
		household_numbers = $('#id_invoiceitems_set-'+String(index)+'-household_numbers').val();
		last_row_index = $("#invoiceitems_set-empty").index() - 1;
		$("#id_invoiceitems_set-"+String(last_row_index)+"-material_type option[value='"+material_type+"']").attr('selected' , 'selected');
		$("#id_invoiceitems_set-"+String(last_row_index)+"-phase option[value='"+phase+"']").attr('selected' , 'selected');
		$("#id_invoiceitems_set-"+String(last_row_index)+"-unit option[value='"+unit+"']").attr('selected' , 'selected');
		$("#id_invoiceitems_set-"+String(last_row_index)+"-slum ").val(slum) ;
		$("#id_invoiceitems_set-"+String(last_row_index)+"-household_numbers").val(household_numbers);
		console.log(material_type, phase, unit, last_row_index);
		//$("#id_invoiceitems_set-0-material_type option[value='64']").attr('selected' , 'selected')
}
