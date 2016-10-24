var PointArray=[];
var myOptions;
var map;
var creator;
var PolygonPoints=[];
var Poly;
var curLatLng=[];
var creator;
var flag=0;
var P;
var Points=[];
var MPoints=[];
var ShapeValue;
var bermudaTriangle;
var S;
var Cflag;
var val;
var CPoints;
var x;
var isClosed = false;
var markersArray =[];
var poly;
    
function initialise(){
 
    var a =[];
    ShapeValue=django.jQuery('#id_shape').val();
    var r = ShapeValue.substring(20,ShapeValue.length-2);
    var a= r.split(/[\s,]+/);
    var r1;
    var r2;
    for (var i=0; i <= a.length-1 ; i ++){
        if (i%2==0)
        {
            r1 = a[i];
        }else if (i %2 !=0){
            r2 =a[i];
            Points.push(new google.maps.LatLng(r2, r1));
            }
        }
    
        P=Points.pop();

    if(P)
    {
         myOptions = {
        zoom: 10,
        center: new google.maps.LatLng(P.lat(),P.lng()),
        mapTypeId: google.maps.MapTypeId.SATELLITE
        }
    }
    else{
         myOptions = {
        zoom: 14,
        center: new google.maps.LatLng(18.505536, 73.822812),
        mapTypeId: google.maps.MapTypeId.SATELLITE   
        }
    }

    map = new google.maps.Map(document.getElementById('main-map'), myOptions);
   
    if(ShapeValue!="None")
    {

         map = new google.maps.Map(document.getElementById('main-map'), myOptions);

         var v=laodmapcity2();
         r = v.substring(20,v.length-2);
         var a = r.split(/[\s,]+/);
        
         var r1;
         var r2;
         CPoints=[];
        for (var i=0; i <= a.length-1 ; i ++){
        if (i%2==0)
        {
            r1 = a[i];
        }else if (i %2 !=0){
            r2 =a[i];
            CPoints.push(new google.maps.LatLng(r2, r1));
            }
        }
            
        var flightPath = new google.maps.Polyline({
          path:  CPoints,
          geodesic: true,
          strokeColor: '#FF0000',
          strokeOpacity: 1.0,
          strokeWeight: 2
        });

        flightPath.setMap(map);

        flag = 1;
        var result = ShapeValue.substring(20,ShapeValue.length-2);
        var array= result.split(/[\s,]+/);
        var result1;
        var result2;
        for (var i=0; i <= array.length-1 ; i ++){
            if (i%2==0)
            {
                result1 = array[i];
            }else if (i %2 !=0){
                result2 =array[i];
                PolygonPoints.push(new google.maps.LatLng(result2, result1));
            }
        }

        
        Poly = new google.maps.Polygon({
            paths:  PolygonPoints,
            draggable: true,
            editable: true,
            strokeColor: '#FF0000',
            strokeOpacity: 0.8,
            strokeWeight: 2,
            fillColor: '#FF0000',
            fillOpacity: 0.35
        });

         Poly.setMap(map);

        // isClosed=true;

        google.maps.event.addListener( Poly, "dragend", getPolygonCoords);
        google.maps.event.addListener( Poly.getPath(), "insert_at", getPolygonCoords);
        google.maps.event.addListener( Poly.getPath(), "remove_at", getPolygonCoords);
        google.maps.event.addListener( Poly.getPath(), "set_at", getPolygonCoords);

       
    }
    else{
        flag = 0;
        drawMap();
        
    }

    
}

function getPolygonCoords() {
    curLatLng = [];
    curLatLng = Poly.getPath().getArray();
    alert("Hi");
    console.log(curLatLng);
}   



function Point_string(){
   
    var PolygonArray=[];
    alert("I am in Point_string condition");    
    if (flag==0)
    {
        PointArray = poly.getPath().getArray();  
        var Point = PointArray[0];
        PointArray.push(Point);
        PolygonArray= PointArray;
        alert("in if condition");
    }
    else if(flag==1)
    {
        var Point = curLatLng[0];
        curLatLng.push(Point);
        alert(curLatLng);
        PolygonArray =  curLatLng;
       
    }
    var c_str="POLYGON((";
    var string_append="";
    var lng ="";
    var lat = "";
    for(var i=0; i<PolygonArray.length;i++){
        lng = PolygonArray[i].lng();
        lat = PolygonArray[i].lat();
        string_append+=lng+" "+lat +",";
    };
    c_str+=string_append.substring(string_append,string_append.length-1)+"))";
    return c_str;
}

django.jQuery(document).ready(function(){
    django.jQuery("input[name='_save']").click(function(){
        var string = Point_string();
        django.jQuery('#id_shape').val(string);
        django.jQuery('#id_shape').text(string);
    });
});


django.jQuery(document).ready(function(){
    django.jQuery("input[name='_addanother']").click(function(){
        var string = Point_string();
        django.jQuery('#id_shape').val(string);
        django.jQuery('#id_shape').text(string);
    });
});


django.jQuery(document).ready(function(){
    django.jQuery("input[name='_continue']").click(function(){
        var string = Point_string();
        django.jQuery('#id_shape').val(string);
        django.jQuery('#id_shape').text(string);
    });
});




django.jQuery(document).ready(function(){
    django.jQuery("#id_city").on('change',function()
     {  
        laodmapcity();      
    });
});


function initMap(mstring){
    var a =[];
    var Shape=mstring;
    var r = Shape.substring(20,Shape.length-2);
    var a = r.split(/[\s,]+/);
    var r1;
    var r2;
    MPoints=[];
   map=null;

   map = new google.maps.Map(document.getElementById('main-map'), myOptions);
        
    for (var i=0; i <= a.length-1 ; i ++){
        if (i%2==0)
        {
            r1 = a[i];
        }else if (i %2 !=0){
            r2 =a[i];
            MPoints.push(new google.maps.LatLng(r2, r1));
            }
        }

     var flightPath = new google.maps.Polyline({
          path: MPoints,
          geodesic: true,
          strokeColor: '#FF0000',
          strokeOpacity: 1.0,
          strokeWeight: 2
        });

        flightPath.setMap(map);


     if(ShapeValue!="None")
     {
        Poly = new google.maps.Polygon({
            paths:PolygonPoints, 
            draggable: true,
            editable: true,
            strokeColor: '#FF0000',
            strokeOpacity: 0.8,
            strokeWeight: 2,
            fillColor: '#FF0000',
            fillOpacity: 0.35
        });



        Poly.setMap(map);
        isClosed=true;
  

    }
    else{

        if(PointArray.length==0)
        {
           drawMap(map);

        }
        else
        {
            Poly = new google.maps.Polygon({
            paths:PointArray,
            draggable: true,
            editable: true,
            strokeColor: '#FF0000',
            strokeOpacity: 0.8,
            strokeWeight: 2,
            fillColor: '#FF0000',
            fillOpacity: 0.35
            });
        
            Poly.setMap(map);
            isClosed=true;
        }         
    }

}

function laodmapcity(){
    
    var id = django.jQuery("#id_city option:selected").val();  
    $.ajax({
        url : "/admin/Acitymapdisplay/",
        type : "POST",
       data : { 'id' : id},
  
        contenttype : "json",
        success : function(json) {
           // PolygonPoints=Poly.getPath().getArray();
            initMap(json);
        },
        async:false
    });
   
}



function laodmapcity2(){
    var id = django.jQuery("#id_city option:selected").val();  
    $.ajax({
        url : "/admin/Acitymapdisplay/",
        type : "POST",
       data : { 'id' : id},
  
        contenttype : "json",
        success : function(json) {
          val = json;
        },
        async:false
    });

    return val;
}


function drawMap(){
  
      isClosed = false;
      poly = new google.maps.Polyline({ map: map, path: [], strokeColor: "#FF0000", strokeOpacity: 1.0, strokeWeight: 2 });
  
      google.maps.event.addListener(map, 'click', function (clickEvent) {
        if (isClosed)
            return;
        var markerIndex = poly.getPath().length;
        var isFirstMarker = markerIndex === 0;
        var Point = clickEvent.latLng;
        PointArray.push(Point); 

        var marker = new google.maps.Marker({ map: map, position: clickEvent.latLng, draggable: true });
        markersArray.push(marker);
        if (isFirstMarker) {
            google.maps.event.addListener(marker, 'click', function () {
                if (isClosed)
                    return;
                var path = poly.getPath();
                poly.setMap(null);
                poly = new google.maps.Polygon({ map: map, path: PointArray, strokeColor: "#FF0000", strokeOpacity: 0.8, strokeWeight: 2, fillColor: "#FF0000", fillOpacity: 0.35,draggable: true,
            editable: true });
                isClosed = true;
                clearOverlays();
            });
        }

        google.maps.event.addListener(marker, 'drag', function (dragEvent) {
            poly.getPath().setAt(markerIndex, dragEvent.latLng);
        });
        poly.getPath().push(clickEvent.latLng);
    }
       ); 

}
  
function clearOverlays() {
  for (var i = 0; i < markersArray.length; i++ ) {
    markersArray[i].setMap(null);
  }
  markersArray.length = 0;
}



django.jQuery(document).ready(function(){
      django.jQuery('#reset').click(function(){
        map=null;
        map = new google.maps.Map(document.getElementById('main-map'), myOptions);
        PointArray=[];
        PolygonPoints=[];
        drawMap();

    });
});