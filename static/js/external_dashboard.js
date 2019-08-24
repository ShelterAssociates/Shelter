
let map_data = [];
let map = null;

style_value ={
  color : "#3232FF",
  opacity : 0.9,
  weight : 2,
  fillColor : "#A3A3FF",
  fillOpacity : 0.6,
}

scores = [0.5, 0.4, 0.3, 0.25, 0.2, 0.15, 0.1];

function getColor(d) {
    return d > 0.5 ? '#800026' :
           d > 0.4  ? '#BD0026' :
           d > 0.3  ? '#E31A1C' :
           d > 0.25  ? '#FC4E2A' :
           d > 0.2   ? '#FD8D3C' :
           d > 0.15   ? '#FEB24C' :
           d > 0.1   ? '#FED976' :
                      '#FFEDA0';
}

var MapLoad = (function() {
  function MapLoad(data){
        this.data = data;
        this.shape = null;
   }

  MapLoad.prototype.map_render = function(){
    let geo_data = {
      "type": "FeatureCollection",
      "features": this.data
    };
    this.shape = L.geoJson(geo_data, {style: function(feature){
        style_value['fillColor'] = style_value['color'] = getColor(feature.properties.score.General);
        return style_value;
    },  onEachFeature:this.onEachFeature});
  }
  MapLoad.prototype.onEachFeature = function(feature, layer){
    var properties = feature.properties;
    // Build the label / tooltip content…
    var content = [];
    for (var key in properties) {

      if (typeof properties[key] == "object")
      {
//        content.push(key +":");
//        for (var key1 in properties[key]) {
//            content.push('&nbsp;&nbsp;'+key1 + ' : '+ properties[key][key1]);
//        }
      }
      else{
        content.push(key + ': ' + properties[key]);
      }

    }
    layer.bindPopup(content.join('<br>'),{autoPan:false});
    layer.on({
       'mouseover': function (ev) {
                        this.openPopup();
                     },
       'mouseout' : function(ev){
                        this.closePopup();
                    }
    });
  }
  MapLoad.prototype.show_all = function(selected_level='General',flag_only_border=false){
    map.addLayer(this.shape);
    this.shape.eachLayer(function (layer) {
        style_value['fillColor'] = style_value['color'] = getColor(layer.feature.properties.score[selected_level]);
        if (flag_only_border == true){
          style_value['fillOpacity'] = 0;
          //style_value['weight'] = 4;
//          style_value['fillColor'] = style_value['color'] = "#fff";
        }
        else{
          //style_value['weight'] = 2;
          style_value['fillOpacity'] = 0.6;
        }
        layer.setStyle(style_value);
    });
  }

  MapLoad.prototype.hide_all = function(){
     map.removeLayer(this.shape);
  }

   return MapLoad;
}());

function initMap(){
    let center_data = {
      "Navi Mumbai":new L.LatLng(19.09118307623272, 73.0159571631209),
      "Thane":new L.LatLng(19.215441921044757, 72.98368482425371),
      "Sangli":new L.LatLng(16.850235500492538, 74.60914487360401),
      "Kolhapur":new L.LatLng(16.700800029695312, 74.23729060058895),
      "PCMC":new L.LatLng(18.640083, 73.825560),
      "Pune":new L.LatLng(18.51099762698481, 73.86055464212859),
      "Panvel":new L.LatLng(19.051509, 73.109058)
    };
    var pos = new L.LatLng(18.640083, 73.825560);
    if ($('#city_name').val() in center_data)
    {
        pos = center_data[$('#city_name').val()];
    }
    map = new L.Map('map', {
        center: pos,
        zoom: 12,
        zoomSnap: 0.25,
        markerZoomAnimation:false
    });

    var legend = L.control({position: 'bottomright'});

    legend.onAdd = function (map) {

      var div = L.DomUtil.create('div', 'info legend'),
        labels = [];

      // loop through our density intervals and generate a label with a colored square for each interval
      for (var i = 0; i < scores.length; i++) {
        div.innerHTML +=
          '<i style="background:' + getColor(scores[i]) + '"></i> ' +
          scores[i] + (scores[i + 1] ? ' &ndash; ' + scores[i + 1] + '<br>' : '+');
      }

      return div;
    };
    legend.addTo(map);
    var ggl = L.gridLayer.googleMutant({type: 'satellite' }).addTo(map);
    initMap12();
}

function initMap12() {

    $(".overlay").show();
    var city_id = $("#city_id").val();
    var city_name = $("#city_name").val();
    $.ajax({
        url : "/admin/slummapdisplay/" + city_id + "/",
        type : "GET",
        contenttype : "json",
        success : function(json) {
            let data = json['content'];
            data = parse_custom_fields(data);
            map_data[0] = new MapLoad(Object.values(Object.keys(data).map(function(k,i){ return data[k]['lat']})));
            map_data[0].map_render();
            map_data[0].show_all()

            elect_data = [];
            slum_data = [];
            $.each(data, function(k3,v3){
            $.each(v3.content, function(k,v){
              elect_data.push(v['lat']);
              $.each(v.content, function(k1,v1){
                slum_data.push(v1['lat']);
              });
            });
            });
            map_data[1] = new MapLoad(elect_data);
            map_data[1].map_render();

            map_data[2] = new MapLoad(slum_data);
            map_data[2].map_render();

            $(".overlay").hide();
        }
    });
}

function parse_custom_fields(data){
    $.each(data, function(key,value){
     value['lat'] = { 'geometry':value['lat'],
       'type':'Feature',
       'properties' : {'name':key, 'score':{ 'General' : scores[Math.floor(Math.random() * scores.length)],
                                              'Toilet' : scores[Math.floor(Math.random() * scores.length)],
                                              'Gutter' : scores[Math.floor(Math.random() * scores.length)],
                                              'Drainage' : scores[Math.floor(Math.random() * scores.length)],
                                              'Road':scores[Math.floor(Math.random() * scores.length)],
                                              'Water': scores[Math.floor(Math.random() * scores.length)],
                                              'Waste' : scores[Math.floor(Math.random() * scores.length)]}},
     }
     $.each(value.content, function(k1,v1){

        v1['lat'] = { 'geometry':v1['lat'],
         'type':'Feature',
         'properties' : {'name':k1, 'score':{'General' : scores[Math.floor(Math.random() * scores.length)],
                                              'Toilet' : scores[Math.floor(Math.random() * scores.length)],
                                              'Gutter' : scores[Math.floor(Math.random() * scores.length)],
                                              'Drainage' : scores[Math.floor(Math.random() * scores.length)],
                                              'Road':scores[Math.floor(Math.random() * scores.length)],
                                              'Water': scores[Math.floor(Math.random() * scores.length)],
                                              'Waste' : scores[Math.floor(Math.random() * scores.length)]}},
       }

       $.each(v1.content, function(k2,v2){
        v2['lat'] = { 'geometry':v2['lat'],
         'type':'Feature',
         'properties' : {'name':k2, 'score':{'General' : scores[Math.floor(Math.random() * scores.length)],
                                              'Toilet' : scores[Math.floor(Math.random() * scores.length)],
                                              'Gutter' : scores[Math.floor(Math.random() * scores.length)],
                                              'Drainage' : scores[Math.floor(Math.random() * scores.length)],
                                              'Road':scores[Math.floor(Math.random() * scores.length)],
                                              'Water': scores[Math.floor(Math.random() * scores.length)],
                                              'Waste' : scores[Math.floor(Math.random() * scores.length)]}},
        }
       });
     });
    });
  return data;
}

$(document).ready(function(){
  function changeMap(level, level_tag){
    map_data[0].hide_all();
    map_data[1].hide_all();
    map_data[2].hide_all();
    if (level != 0)
    {
      map_data[0].show_all(level_tag, true);
    }
    map_data[level].show_all(level_tag);
  }
  $('input[type=radio][name=level]').change(function() {
    let level = $(this).val();
    let level_tag = $("#levels_tag").val();
    changeMap(level, level_tag);
  });

  $("#levels_tag").change(function(){
    let level_tag = $(this).val();
    let level = $('input[type=radio][name=level]:checked').val();
    changeMap(level, level_tag);
  });
});