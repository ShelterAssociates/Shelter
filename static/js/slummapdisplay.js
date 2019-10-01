$(document).ready(function(){
    if(window.location !== window.parent.location) {
        $('#navbar').hide();
    }
    function add_cards(name, data){
        var card = $("div[name=section_card_clone]")[0].outerHTML;
        card = $(card).attr('name','card').removeClass('hide');
        card.find(".city_name")[0].innerHTML = name;
        card.find(".total-score")[0].innerHTML = ''+parseInt(data['totalscore_percentile__avg'])+'%';
        card.find(".number-of-slums")[0].innerHTML = data['slum_count'] + " / "+data['total_slum_count'];
        card.find(".household-count")[0].innerHTML = data['household_count__sum'];
        card.find('.dashboard-url')[0].href = "/dashboard/"+ data['city_id'];
        card.find('.gis-url')[0].href = "/"+data['city_id'];
        $(".cards").append(card);
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
