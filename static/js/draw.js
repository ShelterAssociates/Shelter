var myOptions;
var map;
var Poly;
var isClosed = false;
var markersArray =[];

    

function initialise(){
    var Points=[];
    myOptions = {
        zoom: 14,
        center: new google.maps.LatLng(18.505536, 73.822812),
        mapTypeId: google.maps.MapTypeId.SATELLITE   
        };
        
    map = new google.maps.Map(document.getElementById('main-map'), myOptions); 

    var ShapeValue=django.jQuery('#id_shape').val();   
    Points=Pointconverter(ShapeValue); 
    var P=Points.pop();

    if(P)
    {
        myOptions = {
        zoom: 10,
        center: new google.maps.LatLng(P.lat(),P.lng()),
        mapTypeId: google.maps.MapTypeId.SATELLITE
        };
    }
    else{
        
        myOptions = {
        zoom: 14,
        center: new google.maps.LatLng(18.505536, 73.822812),
        mapTypeId: google.maps.MapTypeId.SATELLITE   
        };
    }
    
    if(ShapeValue!="None")
    {

         map = new google.maps.Map(document.getElementById('main-map'), myOptions);

         PointArray=[];
         var CPoints=[];
        try {
            var Rpolygon=laodmapcity2();
        
             CPoints=Pointconverter(Rpolygon);

            var RArea = new google.maps.Polyline({
                        path:  CPoints,
                        geodesic: true,
                        strokeColor: '#FF0000',
                        strokeOpacity: 1.0,
                        strokeWeight: 2
            });

            RArea.setMap(map);
        }
        catch(err) {
                console.log(err); 
        } 
  
        PointArray=Pointconverter(ShapeValue);
        
        Poly = new google.maps.Polygon({
            paths:  PointArray,
            draggable: true,
            editable: true,
            strokeColor: '#FF0000',
            strokeOpacity: 0.8,
            strokeWeight: 2,
            fillColor: '#FF0000',
            fillOpacity: 0.35
        });

         Poly.setMap(map);      
    }
    else{     
        drawMap();        
    }
}


function Point_string(){
    var PointArray=[];
    var PolygonArray=[];
    PointArray = Poly.getPath().getArray();  
    var Point = PointArray[0];
    PointArray.push(Point);
    PolygonArray= PointArray;
    alert("Point_string");
    alert(PolygonArray);
    
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


function initMap(mstring,PointArray){
    var MPoints=[];
    map=null;
    map = new google.maps.Map(document.getElementById('main-map'), myOptions);
    

    MPoints=Pointconverter(mstring);
    alert(MPoints);

    var RArea = new google.maps.Polyline({
          path: MPoints,
          geodesic: true,
          strokeColor: '#FF0000',
          strokeOpacity: 1.0,
          strokeWeight: 2
        });

        RArea.setMap(map);


    if(PointArray.length > 0){

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
     }
     else
     {   
        isClosed=true;
        drawMap();
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
            var PointArray=[];
            PointArray = Poly.getPath().getArray();
            initMap(json,PointArray);
        },
        async:false
    });   
}


function laodmapcity2(){
    var id = django.jQuery("#id_city option:selected").val();  
    var val;
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

      var PointArray=[]; 
      isClosed = false;
      Poly = new google.maps.Polyline({ map: map, path: [], strokeColor: "#FF0000", strokeOpacity: 1.0, strokeWeight: 2 });
  
      google.maps.event.addListener(map, 'click', function (clickEvent) {
        if (isClosed)
            return;
        var markerIndex = Poly.getPath().length;
        var isFirstMarker = markerIndex === 0;
        var Point = clickEvent.latLng;
        PointArray.push(Point); 

        var marker = new google.maps.Marker({ map: map, position: clickEvent.latLng, draggable: true });
        markersArray.push(marker);
        if (isFirstMarker) {
            google.maps.event.addListener(marker, 'click', function () {
                if (isClosed)
                    return;
                var path = Poly.getPath();
                Poly.setMap(null);
                Poly = new google.maps.Polygon({ map: map, path: PointArray, strokeColor: "#FF0000", strokeOpacity: 0.8, strokeWeight: 2, fillColor: "#FF0000", fillOpacity: 0.35,draggable: true,
            editable: true });
                isClosed = true;
                clearOverlays();
            });
        }

        google.maps.event.addListener(marker, 'drag', function (dragEvent) {
            Poly.getPath().setAt(markerIndex, dragEvent.latLng);
        });
        Poly.getPath().push(clickEvent.latLng);
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
        drawMap();
    });
});


function Pointconverter(PolyString){
    var PolygonPoints=[];
    var adummy =[];
    var Shape;
    var Shape = PolyString.substring(20,PolyString.length-2);
    var adummy = Shape.split(/[\s,]+/);
    var dummy1;
   var dummy2;   

    for (var i=0; i <= adummy.length-1 ; i ++){
        if (i%2==0)
        {
            dummy1 = adummy[i];
        }else if (i %2 !=0){
            dummy2 =adummy[i];
            PolygonPoints.push(new google.maps.LatLng(dummy2, dummy1));
            }
        }
    return PolygonPoints;
}