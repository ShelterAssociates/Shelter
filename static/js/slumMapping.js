var map;
function initMap12() {
	labelmap();
	map = new google.maps.Map(document.getElementById('map12'), {
		center : {
			lat : 19.489339,
			lng : 74.631617
		},
		zoom : 4,
		mapTypeId : 'satellite',
	});
	loadcity();
	viewIndiaBorder();
}
function animateMapZoomTo(map, targetZoom) {
    var currentZoom = arguments[2] || map.getZoom();
    if (currentZoom != targetZoom) {
        google.maps.event.addListenerOnce(map, 'zoom_changed', function (event) {
            animateMapZoomTo(map, targetZoom, currentZoom + (targetZoom > currentZoom ? 1 : -1));
        });
        setTimeout(function(){ map.setZoom(currentZoom) }, 80);
    }
}

function loadcity() {
	$(".overlay").show();
	$.ajax({
		url : '/admin/citymapdisplay',
		type : "GET",
		contenttype : "json",
		success : function(json) {
			getcordinates(json);
			animateMapZoomTo(map,8);
			$(".overlay").hide();
		}
	});
}

function getcordinates(obj1) {
    $.each(obj1, function(k,v){
        latlongformat(v);
    });
}
function latlongformat(city) {
	var PolygonPoints = [];
	var centerlatlang = [];
	var bounds = new google.maps.LatLngBounds();
	let ShapeValue = city.lat;
    let bgcolor = city.bgColor || "";
    let bordercolor = city.borderColor || "";
    let shapename = city.name;
	var result = ShapeValue.substring(20, ShapeValue.length - 2);
	var array = result.split(/[\s,]+/);
	var result1;
	var result2;

	for (var i = 0; i <= array.length - 1; i++) {
		if (i % 2 == 0) {
			result1 = array[i];
		} else if (i % 2 != 0) {
			result2 = array[i];
			PolygonPoints.push(new google.maps.LatLng(result2, result1));
			bounds.extend(new google.maps.LatLng(result2, result1));
		}
	}
	PolygonPoints.pop();
	var Poly1 = drawPolygon(PolygonPoints, bounds, bgcolor, bordercolor, shapename);
	var options = {
        map: map,
        position: bounds.getCenter(),
        text: '',
        minZoom: 7,
        zIndex : 999
    };
	var slumLabel = new MapLabel(options);
    slumLabel.text = shapename;
    slumLabel.changed('text');

	google.maps.event.addListener(Poly1, 'click', function(event) {
        var win = window.open(window.location.protocol + '/'+city.id, '_blank');
        win.focus();
	});

}

function drawPolygon(PolygonPoints, centerlatlang, bgcolor, bordercolor, shapename, index=2) {
	var Poly;
	var newbgcolor = "#FFA3A3";
	var newbordercolor = "#FF0000";
	var opacity = 0.4;
	if (bgcolor != undefined && bgcolor != "") {
		newbgcolor = bgcolor;
	}

	if (bordercolor != undefined && bordercolor != "") {
		newbordercolor = bordercolor;
	}

    if(['Pune', 'PCMC'].indexOf(shapename)< 0){
        index=1;
    }

	Poly = new google.maps.Polygon({
		paths : PolygonPoints,
		strokeColor : newbordercolor,
		strokeOpacity : 0.7,
		strokeWeight : 2,
		fillColor : newbgcolor,
		fillOpacity : opacity,
		center : centerlatlang.getCenter(),
		zIndex:index,
	});
	Poly.setMap(map);
	map.setCenter(centerlatlang.getCenter());
	return Poly;
}

function viewIndiaBorder() {
	var layer;
	// Fusion Tables layer
	var tableid = 420419;

	layer = new google.maps.FusionTablesLayer({
		query : {
			select : "kml_4326",
			from : tableid,
			where : "name_0 = 'India' and name_1= 'Maharashtra'"
		},
		styles : [{
			polygonOptions : {
				strokeWeight : "2",
				strokeColor : "#FF0000",
				strokeOpacity : "0.4",
				fillOpacity : "0.0",
				fillColor : "#000000"
			}
		}]
	});

	layer.setMap(map);
}