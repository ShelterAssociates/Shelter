function populate_top_bar(data){
  let total_slums = 0, total_households = 0, total_population = 0, total_toilets = 0, total_impact = 0;

  function formatNumber(value) {
    var number = parseInt(value, 10);
    if (isNaN(number)) {
      return '0';
    }
    return number.toLocaleString('en-IN');
  }

  //1282 - Sangli, 3952-Pune, 14- Donje
   if(Object.keys(data).length > 1)
  {
    total_toilets = 1282+3952+14;
  }
  $.each(data, function(key, value){
    total_slums += value.slum_count;
    total_households += value['household_count__sum'] == null ? 0 : value['household_count__sum'];
    total_population += value['slum_population__sum'] == null ? 0 : value['slum_population__sum'];
    total_toilets += value['count_of_toilets_completed__sum'] == null ? 0 : value['count_of_toilets_completed__sum'];
    //total_impact += value['people_impacted__sum'] == null ? 0 : value['people_impacted__sum'];
  });
  $('.total-slums').html(formatNumber(total_slums));
  $('.total-households').html(formatNumber(total_households));
  $('.total-population').html(formatNumber(total_population));
  $('.total-toilets').html(formatNumber(total_toilets));
  //total_impact = ''+total_impact;
  //$('.total-impact').html('');
  //for(i=0; i<total_impact.length; i++){
  //  $('.total-impact').append('<li><span>'+total_impact[i]+'</span></li>');
  //}

}
