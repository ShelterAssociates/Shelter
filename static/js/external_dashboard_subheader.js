function populate_top_bar(data){
  let total_slums = 0, total_households = 0, total_population = 0, total_toilets = 1282+3952+14, total_impact = total_toilets*2;
  //1282 - Sangli, 3952-Pune, 14- Donje
  $.each(data, function(key, value){
    total_slums += value.slum_count;
    total_households += value['household_count__sum'] == null ? 0 : value['household_count__sum'];
    total_population += value['slum_population__sum'] == null ? 0 : value['slum_population__sum'];
    total_toilets += value['count_of_toilets_completed__sum'] == null ? 0 : value['count_of_toilets_completed__sum'];
    //total_impact += value['people_impacted__sum'] == null ? 0 : value['people_impacted__sum'];
  });
  $('.total-slums').html(''+total_slums);
  $('.total-households').html(''+total_households);
  $('.total-population').html(''+total_population);
  $('.total-toilets').html(''+total_toilets);
  //total_impact = ''+total_impact;
  //$('.total-impact').html('');
  //for(i=0; i<total_impact.length; i++){
  //  $('.total-impact').append('<li><span>'+total_impact[i]+'</span></li>');
  //}

}
