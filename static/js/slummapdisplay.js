$(document).ready(function(){
    function add_cards(name, data){
        var card = $("div[name=section_card_clone]")[0].outerHTML;
        card = $(card).attr('name','card').removeClass('hide');
        card.find(".city_name")[0].innerHTML = name;
        card.find(".total-score")[0].innerHTML = ''+parseInt(data['totalscore_percentile__avg'])+'%';
        card.find(".number-of-slums")[0].innerHTML = data['slum_count'];
        card.find(".household-count")[0].innerHTML = data['household_count__sum'];
        card.find('.dashboard-url')[0].href = "/dashboard/"+ data['city_id'];
        card.find('.gis-url')[0].href = "/"+data['city_id'];
        $(".cards").append(card);
    }

    function populate_top_bar(data){
      let total_slums = 0, total_households = 0, total_population = 0, total_toilets = 1282+3952+14, total_impact = total_toilets*2;
      //1282 - Sangli, 3952-Pune, 14- Donje
      $.each(data, function(key, value){
        total_slums += value.slum_count;
        total_households += value['household_count__sum'] == null ? 0 : value['household_count__sum'];
        total_population += value['slum_population__sum'] == null ? 0 : value['slum_population__sum'];
        total_toilets += value['count_of_toilets_completed__sum'] == null ? 0 : value['count_of_toilets_completed__sum'];
        total_impact += value['people_impacted__sum'] == null ? 0 : value['people_impacted__sum'];
      });
      $('.total-slums').html(''+total_slums);
      $('.total-households').html(''+total_households);
      $('.total-population').html(''+total_population);
      $('.total-toilets').html(''+total_toilets);
      total_impact = ''+total_impact;
      $('.total-impact').html('');
      for(i=0; i<total_impact.length; i++){
        $('.total-impact').append('<li><span>'+total_impact[i]+'</span></li>');
      }

    }

    $.ajax({
       url : "/graphs/card/all/",
        type : "GET",
        contenttype : "json",
        success : function(json) {
          $.each(json['city'], function(key, value){
              if(value['household_count__sum'] > 0){
                add_cards(key, value);
              }
          });
          populate_top_bar(json['city']);
        },
    });
});