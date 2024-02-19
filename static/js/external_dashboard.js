let map_data = [];
let map = null;
let exclude_cities = ["Nilgiri District", "Saharanpur"];

style_value = {
  color: "#3232FF",
  opacity: 0.9,
  weight: 2,
  fillColor: "#A3A3FF",
  fillOpacity: 0.4,
};

level_names = ["administrative_ward", "electoral_ward", "slum"];

scores = [0, 25, 50, 75, 100];

function getColor(d) {
  return d < 25
    ? "#ff0000"
    : d < 50
    ? "#ffaa00"
    : d < 75
    ? "#f6ff00"
    : d < 100
    ? "#00ff00"
    : "#0000ff";
}

function get_message(layer) {
  var content = [];
  var properties = layer.feature.properties;
  //content.push("Click on area \"" + properties.name + "\" for details");
  var level_sel = $("#levels_tag").val();
  if (
    properties.scores != undefined &&
    properties.scores[level_sel.toLowerCase()] != "" &&
    !isNaN(parseInt(properties.scores[level_sel.toLowerCase()]))
  ) {
    content.push('Click on area "' + properties.name + '" for details');
    content.push(
      "" +
        level_sel +
        " score: " +
        parseInt(properties.scores[level_sel.toLowerCase()]) +
        "%"
    );
  } else {
    content.push('No data available for "' + properties.name + '"');
  }
  return content.join("<br>");
}

function fun_call() {
  // function to set city level data on onclick of close button at admin, electoral and slum level
  let level = "city";
  let name = $("#city_name").val();
  text =
    "all " +
    $("input[type=radio][name=level]:checked").attr("text").toLowerCase();
  display_cards(name, level);
  $(".chip").css({ "background-color": "#ffffff" }).html(text);
  $(".closebtn").hide();
}

function change_text(name) {
  // function to change the dashboard report text according to selected attributes
  if (name != $("#city_name").val()) {
    var text = $("#levels_tag").val() + "  Report Card for";
    $("#report_selections")
      .html(text)
      .append("<div class='chip' id ='contact-chip'>Add text</div> ");
    $(".chip").html(name).append("<span class='closebtn'>&times</span>");
    $(".closebtn").on({
      click: function () {
        fun_call();
        selected_name = $("#city_name").val();
        set_level = "city";
      },
    });
  } else {
    var vis =
      $("#levels_tag").val() +
      " Report Card for all " +
      $("input[type=radio][name=level]:checked").attr("text").toLowerCase();
    $("#report_selections").html(vis);
    //$(".closebtn").hide();
  }
}

function display_cards(names, level) {
  //function to change card data as per map and drop down section selected
  section = $("#levels_tag").val();
  var section_score =
    card_data[level][names]["scores"][section.toLowerCase() + "_percentile"];
  $("#score_val").html(parseInt(section_score));
  $("#section_cards").html("");
  if (section in card_data[level][names]["cards"]) {
    $.each(card_data[level][names]["cards"][section], function (key, value) {
      if (value == 0 || value == "0.0 %" || value == "NO CTB") {
      } else {
        var section_card = $("div[name=section_card_clone]")[0].outerHTML;
        // section_card.style.backgroundColor = 'Yellow';
        section_card = $(section_card)
          .attr("name", "section_card")
          .removeClass("hide");
        section_card.find("span")[0].innerHTML = value;
        section_card.find("span")[1].innerHTML = Object.values(
          card_data["metadata"]["Cards"][section][key]
        )[0];
        section_card.find("img")[0].src =
          "/static/images/dashboard/" +
          Object.keys(card_data["metadata"]["Cards"][section][key])[0] +
          ".png";
        section_card[0].style.backgroundColor = "#008DD2";
        $("#section_cards").append(section_card);
      }
    });
  }
  $(".takeaways").html("");
  if (section in card_data[level][names]["key_takeaways"]) {
    var data = card_data[level][names]["key_takeaways"][section];
    var name = Object.values(card_data["metadata"]["Keytakeaways"][section]);
    if (data.every((item) => item === 0)) {
      $(".key-values").hide();
    }
    if (
      data.every((item) => item === 0) &&
      $("#levels_tag").val() == "Toilet"
    ) {
      data = document
        .getElementById("section_cards")
        .lastChild.innerHTML.indexOf("CTB usage");
      if (data != -1) {
        $(".key-values").hide();
      } else {
        $(".key-values").show();
        $(".takeaways").append("NO CTB" + "<br>");
      }
    }
    for (i = 0; i <= data.length - 1; i++) {
      if (data[i] > 0) {
        $(".key-values").show();
        $(".takeaways").append(
          String(name[i]).replace("value", data[i]) + "<br>"
        );
      }
    }
  }
}
var MapLoad = (function () {
  function MapLoad(data) {
    this.data = data;
    this.shape = null;
  }

  MapLoad.prototype.map_render = function () {
    let geo_data = {
      type: "FeatureCollection",
      features: this.data,
    };
    this.shape = L.geoJson(geo_data, {
      style: function (feature) {
        if (
          "scores" in feature.properties &&
          feature.properties.scores != undefined
        ) {
          style_value["fillColor"] = style_value["color"] = getColor(
            feature.properties.scores.general
          );
        } else {
          style_value["fillColor"] = style_value["color"] = getColor();
        }
        return style_value;
      },
      onEachFeature: this.onEachFeature,
    });
  };
  MapLoad.prototype.onEachFeature = function (feature, layer) {
    var properties = feature.properties;
    layer.bindPopup(get_message(layer), { autoPan: false });
    layer.on({
      mouseover: function (ev) {
        this.openPopup();
      },
      mouseout: function (ev) {
        this.closePopup();
      },
    });
    var level_sel = $("#levels_tag").val();

    if (
      properties.scores != undefined &&
      properties.scores[level_sel.toLowerCase()] != "" &&
      !isNaN(parseInt(properties.scores[level_sel.toLowerCase()]))
    ) {
      layer.on({
        click: function () {
          //function to set card scores of selected ward on onclick
          let level = $("input[type=radio][name=level]:checked").val();
          selected_name = properties.name;
          set_level = level_names[level];
          display_cards(selected_name, set_level);
          change_text(selected_name);
        },
      });
    }
  };
  MapLoad.prototype.show_all = function (
    selected_level = "general",
    flag_only_border = false
  ) {
    map.addLayer(this.shape);
    this.shape.eachLayer(function (layer) {
      layer.setPopupContent(get_message(layer));
      if (
        "scores" in layer.feature.properties &&
        layer.feature.properties.scores != undefined
      ) {
        style_value["fillColor"] = style_value["color"] = getColor(
          layer.feature.properties.scores[selected_level]
        );
      } else {
        style_value["fillColor"] = style_value["color"] = getColor("");
      }
      if (flag_only_border == true) {
        style_value["fillOpacity"] = 0;
        //style_value['weight'] = 4;
        //          style_value['fillColor'] = style_value['color'] = "#fff";
      } else {
        //style_value['weight'] = 2;
        style_value["fillOpacity"] = 0.4;
      }
      layer.setStyle(style_value);
    });
  };

  MapLoad.prototype.hide_all = function () {
    map.removeLayer(this.shape);
  };
  return MapLoad;
})();

function initMap() {
  let center_data = {
    "Navi Mumbai": new L.LatLng(19.09118307623272, 73.0159571631209),
    Thane: new L.LatLng(19.215441921044757, 72.98368482425371),
    Sangli: new L.LatLng(16.850235500492538, 74.60914487360401),
    Kolhapur: new L.LatLng(16.700800029695312, 74.23729060058895),
    PCMC: new L.LatLng(18.640083, 73.82556),
    Pune: new L.LatLng(18.51099762698481, 73.86055464212859),
    Panvel: new L.LatLng(19.051509, 73.109058),
  };
  var pos = new L.LatLng(18.640083, 73.82556);
  if ($("#city_name").val() in center_data) {
    pos = center_data[$("#city_name").val()];
  }
  map = new L.Map("map", {
    center: pos,
    zoom: 12,
    zoomSnap: 0.25,
    markerZoomAnimation: false,
  });

  var legend = L.control({ position: "bottomright" });

  legend.onAdd = function (map) {
    var div = L.DomUtil.create("div", "info legend"),
      labels = [];
    div.innerHTML = "<b>Percentile score</b><br/>";
    // loop through our density intervals and generate a label with a colored square for each interval
    for (var i = 0; i < scores.length - 1; i++) {
      div.innerHTML +=
        '<i style="height:15px;background:' +
        getColor(scores[i]) +
        '"></i> ' +
        scores[i] +
        (scores[i + 1] ? " &ndash; " + scores[i + 1] + "<br>" : "+");
    }
    div.innerHTML += '<i style="height:15px;background:#0000ff;"></i> No slum';
    return div;
  };
  legend.addTo(map);
  var ggl = L.gridLayer.googleMutant({ type: "satellite" }).addTo(map);
  initMap12();
}

function initMap12() {
  $(".overlay").show();
  var city_id = $("#city_id").val();
  var city_name = $("#city_name").val();
  $.ajax({
    url: "/admin/slummapdisplay/" + city_id + "/",
    type: "GET",
    contenttype: "json",
    success: function (json) {
      let data = json["content"];
      data = parse_custom_fields(data);
      map_data[0] = new MapLoad(
        Object.values(
          Object.keys(data).map(function (k, i) {
            return data[k]["lat"];
          })
        )
      );
      map_data[0].map_render();
      map_data[0].show_all();

      elect_data = [];
      slum_data = [];
      $.each(data, function (k3, v3) {
        $.each(v3.content, function (k, v) {
          elect_data.push(v["lat"]);
          $.each(v.content, function (k1, v1) {
            slum_data.push(v1["lat"]);
          });
        });
      });
      map_data[1] = new MapLoad(elect_data);
      map_data[1].map_render();

      map_data[2] = new MapLoad(slum_data);
      map_data[2].map_render();

      $(".overlay").hide();
    },
  });
}

function parse_custom_fields(data) {
  $.each(data, function (key, value) {
    value["lat"] = {
      geometry: value["lat"],
      type: "Feature",
      properties: { name: key, scores: value["scores"] },
    };
    $.each(value.content, function (k1, v1) {
      v1["lat"] = {
        geometry: v1["lat"],
        type: "Feature",
        properties: { name: k1, scores: v1["scores"] },
      };

      $.each(v1.content, function (k2, v2) {
        v2["lat"] = {
          geometry: v2["lat"],
          type: "Feature",
          properties: { name: k2, scores: v2["scores"] },
        };
      });
    });
  });
  return data;
}

var card_data = {};
$(document).ready(function () {
  function changeMap(level, level_tag) {
    map_data[0].hide_all();
    map_data[1].hide_all();
    map_data[2].hide_all();
    if (level != 0) {
      map_data[0].show_all(level_tag.toLowerCase(), true);
    }
    map_data[level].show_all(level_tag.toLowerCase());
  }

  selected_name = $("#city_name").val();
  set_level = "city";

  $("input[type=radio][name=level]").change(function () {
    let level = $(this).val();
    let level_tag = $("#levels_tag").val();
    changeMap(level, level_tag);
    change_text(selected_name);
    fun_call();
  });

  $("#levels_tag").change(function () {
    let level_tag = $(this).val();
    let level = $("input[type=radio][name=level]:checked").val();
    changeMap(level, level_tag);
    change_text(selected_name);
    display_cards(selected_name, set_level);
  });

  var city_id = $("#city_id").val();
  var names = $("#city_name").val();

  //  $("#city_name_text").html(names + ": ");
  $.ajax({
    url: "/graphs/dashboard/" + city_id + "/",
    type: "GET",
    contenttype: "json",
    success: function (json) {
      card_data = json;
      $("#total_score").html(
        parseInt(card_data["city"][names]["scores"]["totalscore_percentile"])
      );
      $("#total_score_text").html("Overall score for " + names + " City");
      $(".overall-score").removeClass("hide");
      //          $("#levels_tag").trigger('change');
      display_cards(selected_name, set_level);
    },
  });

  $.ajax({
    url: "/graphs/card/all/",
    type: "GET",
    contenttype: "json",
    success: function (json) {
      let city_name = $("#city_name").val();
      $("#city_name_text").html("");
      $.each(json["city"], function (key, values) {
        if (values["household_count__sum"] > 0 && !exclude_cities.includes(key))
          $("#city_name_text").append(
            "<option value='" + values.city_id + "'>" + key + "</option>"
          );
      });
      $("#city_name_text").val(json["city"][city_name].city_id);
      populate_top_bar({ city_name: json["city"][city_name] });
    },
  });

  $("#city_name_text").change(function () {
    document.location.href = "/dashboard/" + $(this).val();
  });
});

 // JavaScript to toggle fullscreen mode
 document.addEventListener('DOMContentLoaded', () => {
  // JavaScript to toggle fullscreen mode
  const fullscreenContainer = document.getElementById('fullscreen-container');

  if (fullscreenContainer) {
      fullscreenContainer.addEventListener('click', () => {
          if (document.fullscreenElement) {
              // Exit fullscreen mode if already fullscreen
              document.exitFullscreen();
          } else {
              // Enter fullscreen mode if not already fullscreen
              document.documentElement.requestFullscreen();
          }
      });
  } else {
      console.error("Fullscreen container not found in the document.");
  }
});
