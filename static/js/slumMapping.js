var map;
var obj;
var mydiv;
var myheader;
var mydesc;
var mydatatable;
var wdofficer;
var wdaddress;
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
	wdaddress = $("#wdaddress");
	wdofficer = $("#wdofficer");	
	
	loadcity();
	viewIndiaBorder();		
}

function initMap(obj, zoomlavel) {	
    
	map = new google.maps.Map(document.getElementById('map12'), {
		
		zoom : zoomlavel,
		mapTypeId : 'satellite',
	});
	getcordinates(obj);
	
}

function loadcity() {
	$.ajax({
		url : url,
		type : "GET",
		contenttype : "json",
		success : function(json) {
			obj = json;
			loadslum();
			getcordinates(obj);			
		}
	});
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
			bounds.extend(new google.maps.LatLng(result2, result1));			
		}
	}
		
	PolygonPoints.pop();	
	
	var Poly1 =drawPolygon(PolygonPoints,bounds);
	var infoWindowover = new google.maps.InfoWindow;
	// Events on Polygon
	google.maps.event.addListener(Poly1, 'mouseover', function(event) {
		infoWindowover.setContent(shapename);
		infoWindowover.setPosition(Poly1.center);
		infoWindowover.open(map);

	});

	google.maps.event.addListener(Poly1, 'mouseout', function(event) {
		infoWindowover.close();
	});

	google.maps.event.addListener(Poly1, 'click', function(event) {
		infoWindowover.close();
		
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
var bbb;
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
	
	if ($.isEmptyObject(obj[arr[0]]["content"]))
	{
    	return;
	}
		
	data = fetchData(obj);
	myheader.html('<h4>' + jsondata + '</h4>');	
	setMaplink();
    drawDatatable();
	if (arr.length == 1) {
		mydesc.html(obj[arr[0]]['info']);
		initMap(data, 11);
		
	}else if (arr.length == 2) {
		mydesc.html(obj[arr[0]]["content"][arr[1]]['info']);
		initMap(data, 12);
		
	}else if (arr.length == 3) {
		mydesc.html(obj[arr[0]]["content"][arr[1]]["content"][arr[2]]['info']);
		val = obj[arr[0]]["content"][arr[1]]["content"][arr[2]]
		initMap(val,  13);
		getcordinates(data);

	} else if (arr.length == 4) {
		mydesc.html(obj[arr[0]]["content"][arr[1]]["content"][arr[2]]["content"][arr[3]]['info']);
	    val = obj[arr[0]]["content"][arr[1]]["content"][arr[2]]["content"][arr[3]]
		initMap(val, 14);
	} 
    
}

function fetchData(obj) {
	var o = obj;
	$.each(arr, function(index, val) {
		o = o[val]['content'];
	});
	return o
}

function setMaplink() {
	mydiv.html("");
	var aTag = "";
	aTag +='<label id="Home" onclick="getArea(this);">' + " <span style='text-decoration: underline;cursor:pointer;color:blue;'>Home</span></label>&nbsp;&nbsp;";
	
	for (var i = 0; i < arr.length; i++) {
	
		aTag += '>> <label id=' + arr[i] + ' onclick="getArea(this);">' + " <span style='text-decoration: underline;cursor:pointer;color:blue;'>" + arr[i] + "</span></label>&nbsp;&nbsp; ";
	}
	mydiv.html(aTag);
}

function getArea(initlink) {
	removeIndi = "";
	var textelement = (initlink.textContent).toString().trim();
	console.log(textelement);
	if(textelement == "Home"){
		arr.splice(0, 4);
		initMap(obj, 8);
		return;
	}	
	
	removeIndi = arr.indexOf(textelement) + 1;
	createMap(textelement, true);
}

function drawPolygon(PolygonPoints,centerlatlang) {	
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

var dataset = [];
var a=[];
function getData(data){
	
	$.each(data, function(k,v){
		if(v.content != undefined){
		    getData(v.content);
		}
		else{
		   a.push(v);
		}
	});
}

var arrr;
function drawDatatable(){
	data = fetchData(obj);
        a=[]
     	
	 getData(data);
	arrr=a;
	console.log(arrr);

 	mydatatable=$("#datatable").dataTable({
		"aaData": arrr,
		"bDestroy": true,
        "aoColumns": [{
        "title":'<div style="font-size: large;font-weight: 900;">'+"Slums"+'</div>',
        "mDataProp":  "name",
        "mRender" :function(oObj,val, setval){
        	console.log(setval);
        	return '<div><span style="font-weight: 900;font-size: small;color: blue;cursor: pointer;">'
        			+setval.name +'</span></div>'
        	        +'<div style="font-size: small;">'+setval.info+'</div>';
        	}         
    	}]
	});	 
}


function viewIndiaBorder() {
	var layer;
	// Fusion Tables layer
	var tableid = 420419;

	layer = new google.maps.FusionTablesLayer({
		query : {
			select : "kml_4326",
			from : tableid,
			where : "name_0 = 'India'"
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

