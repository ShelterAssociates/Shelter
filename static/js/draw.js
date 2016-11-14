var map;
var Poly;
var isClosed = false;
var markersArray =[];
var Pcenter;
var Zoom=14;
var shapecolor;

/* Intialise a Google Map */

function initialise(){

    var Points=[];
    var myOptions = {
        zoom: Zoom,
        center: new google.maps.LatLng(18.505536, 73.822812),
        mapTypeId: google.maps.MapTypeId.SATELLITE   
    };

    map = new google.maps.Map(document.getElementById('main-map'), myOptions); 
    var Pcenter = new google.maps.LatLng(41.850, -87.650);

    var ShapeValue=django.jQuery('#id_shape').val();   
    Points=Pointconverter(ShapeValue);
    Pcenter=centerpoint(Points);
    if(Pcenter)
    {
        myOptions = {
        zoom: Zoom,
        center: new google.maps.LatLng(Pcenter.lat(),Pcenter.lng()),
        mapTypeId: google.maps.MapTypeId.SATELLITE
        };
    }
    if(ShapeValue!="None")
    {
        map=null;
        map = new google.maps.Map(document.getElementById('main-map'), myOptions);
 
        var Rpolygon="";
 
        PointArray=[];
 
        var CPoints=[];
 
        try {
            Rpolygon =laodmap2();
        }
 
        catch(err)
        {
            Rpolygon="";
        }
 
        if(ShapeValue) 
         {  
            
            
            PointArray=Pointconverter(ShapeValue);            
            initMap(Rpolygon,PointArray);
         }   
         
    }
    else{     
        drawMap();        
    }
}

/* convert a polygon string to PolygonField object*/

function Point_string(){
    var PointArray=[];
    var PolygonArray=[];
    PointArray = Poly.getPath().getArray();  
    var Point = PointArray[0];
    PointArray.push(Point);
    PolygonArray= PointArray;
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



/* on change draw reference polygon on map*/

function initMap(mstring,PointArray){
    var MPoints=[];
    MPoints=Pointconverter(mstring);

    if(PointArray.length==0)
    {   
     Pcenter=centerpoint(MPoints);
    }
    else
    {   
       Pcenter=centerpoint(PointArray);      
    }    
    
    map=null;

    var myOptions = {
        zoom: Zoom,
        center: new google.maps.LatLng(Pcenter.lat(),Pcenter.lng()),
        mapTypeId: google.maps.MapTypeId.SATELLITE   
        };
    map = new google.maps.Map(document.getElementById('main-map'), myOptions);
    
    if(MPoints){
        var RArea = new google.maps.Polyline({
          path: MPoints,
          geodesic: true,
          strokeColor: shapecolor,
          strokeOpacity: 1.0,
          strokeWeight: 2
        });

        RArea.setMap(map);
    }

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

/* Load a refereence Polygon */

function laodmap(){
    
    var id = django.jQuery("#id_city option:selected, #id_administrative_ward option:selected, #id_electoral_ward option:selected").val();
    var name = django.jQuery("#id_city, #id_administrative_ward, #id_electoral_ward").attr("name");
    var model = name.replace(/_/g, '');  
     
    if(model=="city")
    {
        Zoom=12;
    }    
    else if(model=="administrativeward")
    {
        Zoom=14;
    }
    else
    {
        Zoom=16;
    }
   
    $.ajax({
        url : url,
        type : "POST",
       data : { 'id' : id,'model':model},
  
        contenttype : "json",
         success : function(json){
            shapecolor=json.background_color
            var PointArray=[];
            PointArray = Poly.getPath().getArray();
            initMap(json.shape,PointArray);
        }
    });   
}

/* Load a refereence Polygon */

function laodmap2(){

    var id = django.jQuery("#id_city option:selected, #id_administrative_ward option:selected, #id_electoral_ward option:selected").val();
    var name = django.jQuery("#id_city, #id_administrative_ward, #id_electoral_ward").attr("name");
    var model = name.replace(/_/g, '');
    var val;
    if(model=="city")
    {
        Zoom=12;
    }    
    else if(model=="administrativeward")
    {
        Zoom=14;
    }
    else
    {
        Zoom=15;
    }
    
    $.ajax({
        url : url,
        type : "POST",
       data : { 'id' : id,'model':model},
  
        contenttype : "json",
        success : function(json) {
            val = json.shape;
            shapecolor=json.background_color
        },
        async:false
    });

    return val;
}

/* Draw a polygon on google map on click*/
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
  

/* clear markers from google map */  
function clearOverlays() {
  for (var i = 0; i < markersArray.length; i++ ) {
    markersArray[i].setMap(null);
  }
  markersArray.length = 0;
}



/* Convert a PolygonField object to polygon string*/
function Pointconverter(PolyString){
    var PolygonPoints=[];
    var Parray =[];
    var Shape="";
    var Polygoncheckstring="SRID=4326;POLYGON ((";
    if((PolyString.substring(0,20))==Polygoncheckstring)
    {
       Shape = PolyString.substring(20,PolyString.length-2);
    }
    else
    {
        Shape = PolyString.substring(9,PolyString.length-2);
        Zoom =15;
    }    
    var Parray = Shape.split(/[\s,]+/);
    var Plng;
    var Plat;   

    for (var i=0; i <= Parray.length-1 ; i ++){
        if (i%2==0)
        {
            Plng = Parray[i];
        }else if (i %2 !=0){
            Plat =Parray[i];
            PolygonPoints.push(new google.maps.LatLng(Plat, Plng));
            }
        }
    return PolygonPoints;
}

/* find a center point of polygon */
function centerpoint(Points){
    var bounds = new google.maps.LatLngBounds();
    var Point = new google.maps.LatLng(41.850, -87.650);
    var i;   
    for (i = 0; i < Points.length; i++) {
       bounds.extend(Points[i]);
    }
    Point=bounds.getCenter();
    return Point; 
}


django.jQuery(document).ready(function(){
    /* Reset polygon */
    django.jQuery('#reset').click(function(){
        map=null;
        var myOptions = {
        zoom: Zoom,
        center: new google.maps.LatLng(18.505536, 73.822812),
        mapTypeId: google.maps.MapTypeId.SATELLITE   
    };
        map = new google.maps.Map(document.getElementById('main-map'), myOptions);
        drawMap();
    });

    /* save PolygonField object*/
    django.jQuery("input[name='_save'], input[name='_continue'], input[name='_addanother']").click(function(){
        var string = Point_string();
        django.jQuery('#id_shape').val(string);
        django.jQuery('#id_shape').text(string);
    });

    /* on change load reference polygon*/
    django.jQuery("#id_city, #id_administrative_ward, #id_electoral_ward").on('change',function()
     {  
        laodmap();      
    });
});

