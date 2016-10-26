var map;
var obj;
var mydiv;
var myheader;
var mydesc;
var mydatatable;
var wdofficer;
var wdaddress;
var wdhead;
var url = "/admin/citymapdisplay";

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
	wdhead = $("#wdhead");


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
	$(".overlay").show();
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
	var arr_slum_url = [];
	//$(".overlay").show();
	$.each(obj, function(k, v) {
			arr_slum_url.push($.ajax({
				url : "/admin/slummapdisplay/" + v.id + "/",
				type : "GET",
				contenttype : "json",
				success : function(json) {
					obj[k]["content"] = json["content"];
				}
			}));
	});
	Promise.all(arr_slum_url).then( function(result) {
			$(".overlay").hide();
	});

}

function getcordinates(obj) {
	for (var key in obj) {
		try {
			latlongformat(obj[key]['lat'], obj[key]['name'],obj[key]['bgColor'],obj[key]['borderColor']);
		} catch(err) {
			latlongformat(obj['lat'], obj['name'],obj['bgColor'],obj['borderColor']);
		}
	}
}

function latlongformat(ShapeValue, shapename , bgcolor , bordercolor) {

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

    if(bgcolor == undefined){
    	bgcolor="";
    	bordercolor="";
    }
	var Poly1 = drawPolygon(PolygonPoints,bounds, bgcolor, bordercolor);

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
				'<div id="bodyContent">' +
				'<p><b>'+ shapename +'</b></p>'+
				'<div class="row">'+
				'<div class="col-md-9">'+
				 '<p>' + obj[arr[0]]["content"][arr[1]]["content"][arr[2]]["content"][arr[3]]['info'] +'</p> ';
				 if(obj[arr[0]]["content"][arr[1]]["content"][arr[2]]["content"][arr[3]]['factsheet']){
				 	contentString += '<p><a href="' + obj[arr[0]]["content"][arr[1]]["content"][arr[2]]["content"][arr[3]]['factsheet'] +'">Factsheet</a></p>' ;
				 }
				 '</div>'+
				'<div class="col-md-3" style="margin-left:-20px"><img width="100px" height="120px" src="' + obj[arr[0]]["content"][arr[1]]["content"][arr[2]]["content"][arr[3]]['photo'] +'"></img></div>'+
				'</div>';

				var infoWindow = new google.maps.InfoWindow({maxWidth: 430});
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
    var wdname="";
    var wdadd="";
    var head="";
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
		wdhead.html('');
		wdaddress.html('');
		wdofficer.html('');
		myheader.html('');
		mydesc.html('');
		initMap(data, 11);

	}else if (arr.length == 2) {
		mydesc.html(obj[arr[0]]["content"][arr[1]]['info']);
	    wdhead.html('');
		wdaddress.html('');
	    wdofficer.html('');

		wdadd +="<div class='row'><div  class='col-md-2' style='margin-left:25px'><b>Address :</b> </div><div class='col-md-9'>";
		if(obj[arr[0]]["content"][arr[1]]['wardOfficeAddress']){
			wdadd += (obj[arr[0]]["content"][arr[1]]['wardOfficeAddress']).trim();
		}else{
			wdadd += " - ";
		}
		wdadd +="</div></div>";

		wdname +="<div class='row'><div class='row' style='margin-left:25px'><div class='col-md-2' ><b>Name :</b></div><div class='col-md-10'> ";
		if(obj[arr[0]]["content"][arr[1]]['wardOfficerName'])
		{
			wdname += obj[arr[0]]["content"][arr[1]]['wardOfficerName'] ;
		}else{
			wdname += " - ";
		}
		wdname += "</div></div>"+
		          "<div class='row' style='margin-left:25px'><div class='col-md-2' ><b> Contact :</b></div><div class='col-md-10'> ";
		if(obj[arr[0]]["content"][arr[1]]['wardOfficeTel']){
			wdname += obj[arr[0]]["content"][arr[1]]['wardOfficeTel'] ;
		}else{
			wdname += " - ";
		}
		wdname += "</div></div></div>";

	    head += "<div><b>Administrative Ward : </b></div>";
		wdhead.html(head);
		wdaddress.html(wdadd);
		wdofficer.html(wdname);

		initMap(data, 12);

	}else if (arr.length == 3) {
		mydesc.html(obj[arr[0]]["content"][arr[1]]["content"][arr[2]]['info']);
		wdhead.html('');
		wdaddress.html('');
	    wdofficer.html('');

		wdadd +="<div class='row'><div  class='col-md-2' style='margin-left:25px'><b>Address :</b> </div><div class='col-md-9'>";
		if(obj[arr[0]]["content"][arr[1]]["content"][arr[2]]['wardOfficeAddress']){
			wdadd += (obj[arr[0]]["content"][arr[1]]["content"][arr[2]]['wardOfficeAddress']).trim();
		}else{
			wdadd += " - ";
		}
		wdadd +="</div></div>";

		wdname +="<div class='row'><div class='row' style='margin-left:25px'><div class='col-md-2' ><b>Name :</b></div><div class='col-md-10'> ";
		if(obj[arr[0]]["content"][arr[1]]["content"][arr[2]]['wardOfficerName'])
		{
			wdname += obj[arr[0]]["content"][arr[1]]["content"][arr[2]]['wardOfficerName'] ;
		}else{
			wdname += " - ";
		}
		wdname += "</div></div>"+
		          "<div class='row' style='margin-left:25px'><div class='col-md-2' ><b> Contact :</b></div><div class='col-md-10'> ";
		if(obj[arr[0]]["content"][arr[1]]["content"][arr[2]]['wardOfficeTel']){
			wdname += obj[arr[0]]["content"][arr[1]]["content"][arr[2]]['wardOfficeTel'] ;
		}else{
			wdname += " - ";
		}
		wdname += "</div></div></div>";

	    head += "<div><b>Electoral Ward : </b></div>";
		wdhead.html(head);
		wdaddress.html(wdadd);
		wdofficer.html(wdname);

		val = obj[arr[0]]["content"][arr[1]]["content"][arr[2]]
		initMap(val,  13);
		getcordinates(data);

	} else if (arr.length == 4) {
		mydesc.html(obj[arr[0]]["content"][arr[1]]["content"][arr[2]]["content"][arr[3]]['info']);
	    wdhead.html('');
	    wdaddress.html('');
		wdofficer.html('');

	    val = obj[arr[0]]["content"][arr[1]]["content"][arr[2]]["content"][arr[3]]
		initMap(val, 16);

    	mydatatable.fnDestroy();
    	$("#datatable").empty();
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

    if(arr.length > 0){
    	for (var i = 0; i < arr.length; i++) {
			aTag += '>> <label id=' + arr[i] + ' onclick="getArea(this);">' + " <span style='text-decoration: underline;cursor:pointer;color:blue;'>" + arr[i] + "</span></label>&nbsp;&nbsp; ";
		}
    }

	mydiv.html(aTag);
}

function getArea(initlink) {
	removeIndi = "";
	var textelement = (initlink.textContent).toString().trim();

	if(textelement == "Home"){
		arr.splice(0, 4);
		setMaplink();
		initMap(obj, 8);
		viewIndiaBorder();

		wdhead.html('');
		wdaddress.html('');
		wdofficer.html('');
		myheader.html('');
		mydesc.html('');
		$("#datatable").empty();
		$("#datatablecontainer").hide();
		return;
	}

    $("#datatablecontainer").show();
	removeIndi = arr.indexOf(textelement) + 1;
	createMap(textelement, true);
}

function drawPolygon(PolygonPoints,centerlatlang , bgcolor ,bordercolor) {
	var Poly;
	var newbgcolor="#FFA3A3";
	var newbordercolor="#FF0000";

	if(bgcolor != undefined && bgcolor != ""){
		newbgcolor=bgcolor;
	}

	if(bordercolor != undefined && bordercolor != ""){
		newbordercolor=bordercolor;
	}

	Poly = new google.maps.Polygon({
		paths : PolygonPoints,
		strokeColor : newbordercolor,
		strokeOpacity : 0.7,
		strokeWeight : 2,
		fillColor : newbgcolor ,
		fillOpacity : 0.2,
		center : centerlatlang.getCenter()
	});
	 Poly.setMap(map);
	 map.setCenter(centerlatlang.getCenter() );
	 return Poly;
}

var dataset = [];
var a=[];
var stackLegend =[];
function getData(data){

	$.each(data, function(k,v){
		if(v.content != undefined){
        stackLegend.push(k);
		    getData(v.content);
        stackLegend.pop();
		}
		else{
       v['legend'] = stackLegend.join(':')
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
 	mydatatable=$("#datatable").dataTable({
		"aaData": arrr,
		"bDestroy": true,
    "order": [[ 0, "asc" ]],
    "aoColumns": [{
        "title":'<div style="font-size: large;font-weight: 900;">'+"Slums"+'</div>',
        "mDataProp":  "name",
        "mRender" :function(oObj,val, setval){

              var desc = "";
              if(setval.legend != "")
                  desc = ' ('+ setval.legend.replace(":"," >> ") +')';
            	return '<div><span style="font-weight: 900;font-size: small;color: blue;cursor: pointer;" name="divSlum" data="'+setval.legend + ":"+setval.name+'">'
            			+setval.name + desc +' </span></div>'
            	        +'<div style="font-size: small;">'+setval.info+'</div>';
            	}
    	   }]
	});

  $("#datatablecontainer").show();

  $("#datatable").on("click", "span", function(){
    data = $(this).attr("data");
    arr_data = data.split(":");
    $.each(arr_data,function(k,v){
      if(arr.indexOf(v)==-1)
        arr.push(v);
    });
    slum_pop = arr.pop();
    arr.push(slum_pop);
    createMap(slum_pop, false);
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
