var map;
var obj;
var mydiv;
var myheader;
var mydesc;

var url = "/admin/citymapdisplay";
var Poly;
var ShapeValue;
var shapecount = "";
var arr = [];
var removeIndi;
var indiWindow;
var centerlat;

function initMap12() {

	map = new google.maps.Map(document.getElementById('map12'), {
		center : {
			lat : 18.484913,
			lng : 73.785493
		},
		zoom : 8,
		mapTypeId : 'satellite',
	});
	mydiv = $("#maplink");
	myheader = $("#maphead");
	mydesc = $("#mapdesc");
	
	loadcity();
}

function initMap(obj, zoomlavel) {

	map = new google.maps.Map(document.getElementById('map12'), {
		
		zoom : zoomlavel,
		mapTypeId : 'satellite',
	});

	getcordinates(obj);
}

function loadslum() {
	$.each(obj, function(k, v) {
		$.ajax({
			url : "/admin/slummapdisplay/" + v.id + "/",
			type : "GET",
			contenttype : "json",
			success : function(json) {
				obj[k]["content"] = json["content"];
			}
		});
	});
}


$(document).ready(function() {
	
});

function loadcity() {
	$.ajax({
		url : url,
		type : "GET",
		contenttype : "json",
		success : function(json) {
			obj = json;
			getcordinates(obj);
			loadslum();
		}
	});
}

function getcordinates(obj) {

	for (var key in obj) {
		try {
			latlongformat(obj[key]['lat'], obj[key]['name']);
		} catch(err) {
			latlongformat(obj['lat'], obj['name']);
		}
	}
}

function latlongformat(ShapeValue, shapename) {
	var PolygonPoints = [];
	var centerlatlang=[];
	var bounds = new google.maps.LatLngBounds();
	
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
			centerlatlang.push({lat : result2, lng : result1 });
			bounds.extend(new google.maps.LatLng(result2, result1));
			
		}
	}
		
	PolygonPoints.pop();
	centerlatlang.pop();
	
	console.log("hello");
	var Poly1 =drawPolygon(PolygonPoints,bounds);

	var infoWindow = new google.maps.InfoWindow;
	// Events on Polygon
	google.maps.event.addListener(Poly1, 'mouseover', function(event) {
		console.log(Poly1.center);		
		infoWindow.setContent(shapename);
		infoWindow.setPosition(Poly1.center);
		infoWindow.open(map);

	});

	google.maps.event.addListener(Poly1, 'mouseout', function(event) {
		
		infoWindow.close();
	});

	google.maps.event.addListener(Poly1, 'click', function(event) {
		
		

		if (arr.length == 4) {
			if (indiWindow == true) {
				var contentString = '<div id="content" >' + 
				'<div id="siteNotice">' + 
				'</div>' + 
				'<h1 id="firstHeading" class="firstHeading"></h1>' + 
				'<div id="bodyContent">' + 
				'<p><b>' + shapename + 
				'</b></p>' + 
				'<p>' + obj[arr[0]]["content"][arr[1]]["content"][arr[2]]["content"][arr[3]]['info'] +
				 '</p>' + '</div>' + '</div>';

				var infoWindow = new google.maps.InfoWindow({maxWidth: 400});
				infoWindow.setContent(contentString);
				infoWindow.setPosition(event.latLng);
				infoWindow.open(map);
			}
			indiWindow = true;

		} else {
			createMap(shapename, false);
			indiWindow = false;
		}

	});
}

function createMap(jsondata, arrRemoveInd) {
	console.log("create map");

	if (arrRemoveInd == true) {
		if (arr.indexOf(jsondata) > -1 == true) {
			var indi = arr.indexOf(jsondata);
			arr.splice(removeIndi, 4);
		}
	} else {
		if (arr.indexOf(jsondata) > -1 == false) {
			arr.push(jsondata);
		}
	}
	data = fetchData(obj);
	console.log(data);

	setMaplink();
	centerlat = fetchLatLng(obj);

	

	if (arr.length == 3) {
		val = obj[arr[0]]["content"][arr[1]]["content"][arr[2]]
		initMap(val,  13);
		getcordinates(data);

	} else if (arr.length == 4) {
		val = obj[arr[0]]["content"][arr[1]]["content"][arr[2]]["content"][arr[3]]
		initMap(val, 14);

	} else {
		initMap(data, 11);
	}

	myheader.html('<h4>' + jsondata + '</h4>');

}

function fetchData(obj) {
	var o = obj;
	$.each(arr, function(index, val) {
		o = o[val]['content'];
	});
	return o
}

function fetchLatLng(obj) {
	var d_lat;
	var c_split;

	if (arr.length == 1) {
		d_lat = obj[arr[0]]['lat'].split(",");
		mydesc.html(obj[arr[0]]['info']);

	} else if (arr.length == 2) {
		d_lat = obj[arr[0]]["content"][arr[1]]['lat'].split(",");
		mydesc.html(obj[arr[0]]["content"][arr[1]]['info']);

	} else if (arr.length == 3) {
		d_lat = obj[arr[0]]["content"][arr[1]]["content"][arr[2]]['lat'].split(",");
		mydesc.html(obj[arr[0]]["content"][arr[1]]["content"][arr[2]]['info']);

	} else if (arr.length == 4) {
		d_lat = obj[arr[0]]["content"][arr[1]]["content"][arr[2]]["content"][arr[3]]['lat'].split(",");
		mydesc.html(obj[arr[0]]["content"][arr[1]]["content"][arr[2]]["content"][arr[3]]['info']);
	}

	c_split = d_lat[d_lat.length - 3].split(" ");

	return c_split;
}

function DataLatlng(obj) {
	var o = obj;
	$.each(arr, function(index, val) {
		o = o[val]['content'];
	});
	return o
}

function setMaplink() {
	mydiv.html("");
	var aTag = "";
	for (var i = 0; i < arr.length; i++) {
		aTag += '<label id=' + arr[i] + ' onclick="getArea(this);">&nbsp;&nbsp;' + " <span style='text-decoration: underline;cursor:pointer;color:blue;'>" + arr[i] + "</span></label>";
	}
	mydiv.html(aTag);
}

function getArea(initlink) {
	removeIndi = "";
	var textelement = (initlink.textContent).toString().trim();
	removeIndi = arr.indexOf(textelement) + 1;
	createMap(textelement, true)

}

function drawPolygon(PolygonPoints,centerlatlang) {
	//var center= centroid(centerlatlang);
	console.log(centerlatlang.getCenter());
	Poly = new google.maps.Polygon({
		paths : PolygonPoints,
		strokeColor : '#FF0000',
		strokeOpacity : 0.7,
		strokeWeight : 2,
		fillColor : "#" + ((1 << 24) * Math.random() | 0).toString(16),
		fillOpacity : 0.30,
		center : centerlatlang.getCenter()
	});
	 Poly.setMap(map);
	 map.setCenter(centerlatlang.getCenter() );
	 return Poly;
}


