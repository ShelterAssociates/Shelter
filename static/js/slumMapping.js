var map;
var obj;
var mydiv;
var myheader;
var mydesc;
var mydatatable;
var wdofficer;
var wdaddress;
var wdhead;
var compochk;
var url = "/admin/citymapdisplay";

//var ShapeValue;
//var shapecount = "";
var arr = [];
var removeIndi;

//var centerlat;


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
	compochk=$("#compochk")

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
		infoWindowover.setPosition(bounds.getCenter());
		infoWindowover.open(map);

	});

	google.maps.event.addListener(Poly1, 'mouseout', function(event) {
		infoWindowover.close();
	});
    
    var indiWindow=true;
    
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
				
				var infoWindow= new google.maps.InfoWindow({maxWidth: 430});
				infoWindow.setContent(contentString);
				infoWindow.setPosition(event.latLng);
				infoWindow.open(map);
                
                indiWindow=false;
			}
			

		} else {

			createMap(shapename, false);
			
		}
	});
}

function createMap(jsondata, arrRemoveInd) {
    var wdname="";
    var wdadd="";
    var head="";
    compochk.html('');
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
		objmap=initMap(val, 16);

    	mydatatable.fnDestroy();
    	$("#datatable").empty();
    	
    	
    	compo(val['id']);
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
		compochk.html('');
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
    var opacity=0.2;
	if(bgcolor != undefined && bgcolor != ""){
		newbgcolor=bgcolor;
	}

	if(bordercolor != undefined && bordercolor != ""){
		newbordercolor=bordercolor;
	}
	
	if(arr.length > 2){		
		opacity=0.1;
	}
	
	Poly = new google.maps.Polygon({
		paths : PolygonPoints,
		strokeColor : newbordercolor,
		strokeOpacity : 0.7,
		strokeWeight : 2,
		fillColor : newbgcolor ,
		fillOpacity : opacity,
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

function compo(slumId)
{
	$.ajax({
			url : '/component/fetchcomponents/'+slumId,
			type : "GET",
			contenttype : "json",
			success : function(json) {
				viewcompo(jsond);
			}
	});
}

function viewcompo(dvalue){
	str="";
	counter=1;
	
	var chkPoly;
	chkpoly1=[]
	chkpolydata={}
	
	$.each(dvalue, function(k,v){
		/*
		 str +='<div name="div_group" class="panel-group panel  panel-default panel-heading"> '
			+'<input style="font-size:12%;" class="panel-title" name="chk_group"  value="'+ k +'"  >&nbsp;'
        	+'<a name="chk_group" data-toggle="collapse" href="#'+counter+'">'+k+'</a>'
			+'</input></br>'
		 * */
		counter=counter+1; 
		str +='<div name="div_group" class=" panel  panel-default panel-heading"> '	
        	+'<a name="chk_group" data-toggle="collapse" href="#'+counter+'">'+k+'</a>'
			+'</br>'
			
		str +='<div id="'+counter+'" class="panel-collapse collapse">'	
		$.each(v,function(k1,v1){
			
			var chkcolor=v1['color'];
		    chkpolydata[k1]={};
		        
			str += '<div name="div_group" >'
					+'&nbsp;&nbsp;&nbsp;'		     	
		    		+'<input name="chk1" style="background-color:'+chkcolor+'; -webkit-appearance: none; border: 1px solid black; height: 1.2em; width: 0.8em;"  type="checkbox" value="'+k1+'" onclick="checkSingleGroup(this);" >'
		    		+'<a>&nbsp;'+k1+'</a>'
		    		+'</input>'
		    		+'</div>'
		        		
	    	$.each(v1['child'],function(k2,v2){
	    		var flightPlanCoordinates = [
		          {lat: 37.772, lng: -122.214},
		          {lat: 21.291, lng: -157.821},
		          {lat: -18.142, lng: 178.431},
		          {lat: -27.467, lng: 153.027}
		        ];
	    	
	    		
	    		chkPoly = new google.maps.Polyline({
					path : flightPlanCoordinates,
					strokeColor : chkcolor,
					strokeOpacity : 0.8,
					strokeWeight : 8
					//center : centerlatlang.getCenter()
				 });
	    				    		
	    		chkpolydata[k1][v2['houseno']]= chkPoly;
	    		
	    	});	
		});		
		str +='</div></div>' ;
		
	});
	
	compochk.html(str) ; 
	
	  			                 
		
}



function checkAll(checkbox_group)
{
	
	checktoggle = checkbox_group.checked;
	var checkboxes = new Array();
	divParent = checkbox_group.parentElement	    			
	checkboxes = divParent.getElementsByTagName('input')
	
    for (var i=0; i<checkboxes.length; i++)  {
        if (checkboxes[i].type == 'checkbox')   {
          checkboxes[i].checked = checktoggle;
        }
    }
}


function checkSingleGroup(single_checkbox) {	
	//componentfillmap();
}

function componentfillmap(){
	chkchild="";
	chkparent="";
	
	
	$('input[name=chk1]').each(function () {
      
       if(this.checked==true){
			chkchild = $(this).val();	    
	       	chkparent = $(this).parent().parent().parent().children().attr("value") ;
	        jsonv=jsond[chkparent][chkchild]
	                    
            jsonv['child'].length
            
            var chkcolor=jsonv['color']
            
            $(jsonv['child']).each(function(){
            	household_points=[]
            	
            	$(this.latlang).each(function(){            		
            		household_points.push(new google.maps.LatLng(18.48, 17.78));
            		household_points.push(new google.maps.LatLng(18.50, 17.98));            		
            	});
            	
            	
            	Poly = new google.maps.Polyline({
 						path : household_points,
 						strokeColor : chkcolor,
 						strokeOpacity : 0.8,
 						strokeWeight : 8
 						//center : centerlatlang.getCenter()
 					 });
 				Poly.setMap(map);	 
            });
            	
       }
       
  	});
}



/*
 lat : 18.484913,
			lng : 73.785493
		},
 * */




jsond={
	
  general:{
    household:{
      disname:"AAA",
      color:"RED",
      order:"1",
      type:"map",
      child:[{houseno:"0001",latlang:"18.485,73.786"},{houseno:"0002",latlang:"18.487,73.788"},{houseno:"0003",latlang:"18.485,73.786"}]
    }
    
},
drainage:{
  drainage10:{
    disname:"AAA",
      color:"YELLOW",
      order:"1",
      type:"map",
      child:[{houseno:"0001",latlang:"18.485,73.786"},{houseno:"0002",latlang:"18.487,73.788"},{houseno:"0003",latlang:"18.485,73.786"}]
  },
  draainage12:{
    disname:"AAA",
      color:"GREEN",
      order:"1",
      type:"map",
      child:[{houseno:"0001",latlang:"123,343"},{houseno:"0002",latlang:"123,343"},{houseno:"0003",latlang:"123,343"}]
  }
},

toilet:{
  toilet1:{
    disname:"AAA",
      color:"BLUE",
      order:"1",
      type:"map",
      child:[{houseno:"0001",latlang:"123,343"},{houseno:"0002",latlang:"123,343"},{houseno:"0003",latlang:"123,343"}]
  },
  toilet2:{
    disname:"AAA",
      color:"Aqua",
      order:"1",
      type:"map",
      child:[{houseno:"0001",latlang:"123,343"},{houseno:"0002",latlang:"123,343"},{houseno:"0003",latlang:"123,343"}]
  }
}
}

