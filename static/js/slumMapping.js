var map;
var obj;
var mydiv;
var url = "/admin/slummapdisplay";
var Poly;
var ShapeValue;
var shapecount = "";
var arr = [];
var removeIndi;
var indiWindow;


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

}

function initMap(obj, maplat, zoomlavel) {
	
	map = new google.maps.Map(document.getElementById('map12'), {
		center : {
			lat : parseFloat(maplat[2]),
			lng : parseFloat(maplat[1])
		},
		zoom : zoomlavel,
		mapTypeId : 'satellite',
	});

	getcordinates(obj);
}


$(document).ready(function() {
	loaddata();
});

function loaddata() {
	$.ajax({
		url : url,
		type : "GET",
		contenttype : "json",
		success : function(json) {
			obj = json;
			getcordinates(obj);
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
		}
	}
	
	PolygonPoints.pop();
	drawPolygon(PolygonPoints);

	var infoWindow = new google.maps.InfoWindow;
	// Events on Polygon
	google.maps.event.addListener(Poly, 'mouseover', function(event) {
		infoWindow.setContent(shapename);
		infoWindow.setPosition(event.latLng);
		infoWindow.open(map);
		
	});

	google.maps.event.addListener(Poly, 'mouseout', function(event) {
		infoWindow.close();
	});
	
	google.maps.event.addListener(Poly, 'click', function(event) {
		createMap(shapename, false);
        
        if(arr.length == 4){
        	if(indiWindow == true){
        		var contentString = '<div id="content">'+
			      '<div id="siteNotice">'+
			      '</div>'+
			      '<h1 id="firstHeading" class="firstHeading"></h1>'+
			      '<div id="bodyContent">'+
			      '<p><b>'+shapename+'</b></p>' +			      
			      '<p>'+obj[arr[0]]["content"][arr[1]]["content"][arr[2]]["content"][arr[3]]['info']+'</p>'+
			      '</div>'+
			      '</div>';
        		
        		var infoWindow = new google.maps.InfoWindow;		
				infoWindow.setContent(contentString);
				infoWindow.setPosition(event.latLng);
				infoWindow.open(map);		
        	}        	
        	indiWindow = true;
        	
        }else{
        	indiWindow= false;
        }
		
	});
}

function createMap(jsondata, arrRemoveInd) {
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
	setMaplink();
	var centerlat = fetchLatLng(obj);
	
	if (arr.length == 3) {
		val = obj[arr[0]]["content"][arr[1]]["content"][arr[2]]
		initMap(val, centerlat, 13);
		getcordinates(data);
		
	} else if (arr.length == 4) {
		val = obj[arr[0]]["content"][arr[1]]["content"][arr[2]]["content"][arr[3]]
		initMap(val, centerlat, 14);
	} else {
		initMap(data, centerlat, 11);
	}
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
	var d_lat1;
	
	if (arr.length == 1) {
		d_lat = obj[arr[0]]['lat'].split(",");

	} else if (arr.length == 2) {
		d_lat = obj[arr[0]]["content"][arr[1]]['lat'].split(",");
	} else if (arr.length == 3) {
		d_lat = obj[arr[0]]["content"][arr[1]]["content"][arr[2]]['lat'].split(",");

	} else if (arr.length == 4) {
		d_lat = obj[arr[0]]["content"][arr[1]]["content"][arr[2]]["content"][arr[3]]['lat'].split(",");
	}

	d_lat1 = d_lat[d_lat.length - 3];	
	var c_split = d_lat1.split(" ");
	return c_split;

}

function DataLatlng(obj){
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

function drawPolygon(PolygonPoints) {
	Poly = new google.maps.Polygon({
		paths : PolygonPoints,
		strokeColor : '#FF0000',
		strokeOpacity : 0.7,
		strokeWeight : 2,
		fillColor : "#"+((1<<24)*Math.random()|0).toString(16),
		fillOpacity : 0.30
	});
	Poly.setMap(map);
}

