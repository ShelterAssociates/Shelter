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


function initialise(){

    var a =[];
    var ShapeValue=django.jQuery('#id_shape').val();
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
    creator = new PolygonCreator(map);
    var ShapeValue=django.jQuery('#id_shape').val();
    if(ShapeValue!="None")
    {
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

        P=PolygonPoints.pop
        Poly = new google.maps.Polygon({
            paths: PolygonPoints,
            draggable: true,
            editable: true,
            strokeColor: '#FF0000',
            strokeOpacity: 0.8,
            strokeWeight: 2,
            fillColor: '#FF0000',
            fillOpacity: 0.35
        });

        Poly.setMap(map);
           
        google.maps.event.addListener( Poly, "dragend", getPolygonCoords);
        google.maps.event.addListener( Poly.getPath(), "insert_at", getPolygonCoords);
        google.maps.event.addListener( Poly.getPath(), "remove_at", getPolygonCoords);
        google.maps.event.addListener( Poly.getPath(), "set_at", getPolygonCoords);
    }
    else{
        flag = 0;
    }
}

function getPolygonCoords() {
    curLatLng = [];
    curLatLng = Poly.getPath().getArray();
}   

django.jQuery(function(){
    //reset Polygon and redraw
    django.jQuery('#reset').click(function(){
        creator.destroy();
        creator=null;
        creator=new PolygonCreator(map);
    });
});

function PolygonCreator(map){
    this.map = map;
    this.pen = new Pen(this.map);
    var thisOjb=this;
    this.event=google.maps.event.addListener(thisOjb.map, 'click', function(event){
        PointArray.push(event.latLng);
        thisOjb.pen.draw(event.latLng);
    });
    this.showData = function(){
        return this.pen.getData();
    }
    this.showColor = function(){
        return this.pen.getColor();
    }
    this.destroy = function(){
        this.pen.deleteMis();
        if(null!=this.pen.polygon){
            this.pen.polygon.remove();
        }
        google.maps.event.removeListener(this.event);
    }
}

function Pen(map){
    this.map= map;
    this.listOfDots = new Array();
    this.polyline =null;
    this.polygon = null;
    this.currentDot = null;
    this.draw = function(latLng){
        if (null != this.polygon) {
            alert('Click Reset to draw another');
        }else {
            if (this.currentDot != null && this.listOfDots.length > 1 && this.currentDot == this.listOfDots[0]) {
                this.drawPloygon(this.listOfDots);
            }else {
                if(null!=this.polyline){
                    this.polyline.remove();
                }
                    var dot = new Dot(latLng, this.map, this);
                    this.listOfDots.push(dot);

                if(this.listOfDots.length > 1){
                    this.polyline = new Line(this.listOfDots, this.map);
                }
            }
        }
    }
    this.drawPloygon = function (listOfDots,color,des,id){
        this.polygon = new Polygon(listOfDots,this.map,this,color,des,id);
        this.deleteMis();
    }
    this.deleteMis = function(){
    django.jQuery.each(this.listOfDots, function(index, value){
        value.remove();
    });
    this.listOfDots.length=0;
        if(null!=this.polyline){
            this.polyline.remove();
            this.polyline=null;
        }
    }
    this.cancel = function(){
        if(null!=this.polygon){
            (this.polygon.remove());
        }
        this.polygon=null;
        this.deleteMis();
    }
    this.setCurrentDot = function(dot){
        this.currentDot = dot;
    }
    this.getListOfDots = function(){
        return this.listOfDots;
    }
    this.getData = function(){
        if(this.polygon!=null){
            var data ="";
            var paths = this.polygon.getPlots();
            paths.getAt(0).forEach(function(value, index){
                data+=(value.toString());
            });
            return data;
        }else {
                return null;
            }
        }
    this.getColor = function(){
        if(this.polygon!=null){
            var color = this.polygon.getColor();
            return color;
        }else {
            return null;
        }
    }
}

function Dot(latLng,map,pen){
    this.latLng=latLng;
    this.parent = pen;

    this.markerObj = new google.maps.Marker({
        position: this.latLng,
        map: map
    });
    this.addListener = function(){
        var parent=this.parent;
        var thisMarker=this.markerObj;
        var thisDot=this;
        google.maps.event.addListener(thisMarker, 'click', function(){
            parent.setCurrentDot(thisDot);
            parent.draw(thisMarker.getPosition());
        });
    }
    this.addListener();
    this.getLatLng = function(){
        return this.latLng;
    }
    this.getMarkerObj = function(){
        return this.markerObj;
    }
    this.remove = function(){
        this.markerObj.setMap(null);
    }
}

function Line(listOfDots,map){
    this.listOfDots = listOfDots;
    this.map = map;
    this.coords = new Array();
    this.polylineObj=null;
    if (this.listOfDots.length > 1){
        var thisObj=this;
        django.jQuery.each(this.listOfDots, function(index, value){
            thisObj.coords.push(value.getLatLng());
        });
    this.polylineObj  = new google.maps.Polyline({
        path: this.coords,
        strokeColor: "#FF0000",
        strokeOpacity: 1.0,
        strokeWeight: 2,
        draggable: true,
        editable: true,
        map: this.map
    });
    }
    this.remove = function(){
        this.polylineObj.setMap(null);
    }
}

function Polygon(listOfDots,map,pen,color){
    this.listOfDots = listOfDots;
    this.map = map;
    this.coords = new Array();
    this.parent = pen;
    this.des = 'Hello';
    var thisObj=this;
    django.jQuery.each(this.listOfDots,function(index,value){
        thisObj.coords.push(value.getLatLng());
    });
   
    this.polygonObj= new google.maps.Polygon({
        paths: this.coords,
        strokeColor: "#FF0000",
        strokeOpacity: 0.8,
        strokeWeight: 2,
        fillColor: "#FF0000",
        fillOpacity: 0.35,
        draggable: true,
        editable: true,
        map:this.map
    });
    this.remove = function(){
        this.info.remove();
        this.polygonObj.setMap(null);
    }
    this.getContent = function(){
        return this.des;
    }
    this.getPolygonObj= function(){
        return this.polygonObj;
    }
    this.getListOfDots = function (){
        return this.listOfDots;
    }
    this.getPlots = function(){
        return this.polygonObj.getPaths();
    }
    this.getColor=function(){
        return  this.getPolygonObj().fillColor;
    }
    this.setColor = function(color){
        return  this.getPolygonObj().setOptions(
            {fillColor:color,
                strokeColor:color,
                strokeWeight: 2
            }
            );
    }
    this.info = new Info(this,this.map);
    this.addListener = function(){
        var info=this.info;
        var thisPolygon=this.polygonObj;
        google.maps.event.addListener(thisPolygon, 'rightclick', function(event){
            info.show(event.latLng);
        });
    }
    this.addListener();
}
function Info(polygon,map){
    this.parent = polygon;
    this.map = map;
    this.color =  document.createElement('input');
    this.button = document.createElement('input');
    django.jQuery(this.button).attr('type','button');
    django.jQuery(this.button).val("Change Color");
    var thisOjb=this;
    this.changeColor= function(){
        thisOjb.parent.setColor(django.jQuery(thisOjb.color).val());
    }
    this.getContent = function(){
        var content = document.createElement('div');
        django.jQuery(this.color).val(this.parent.getColor());
        django.jQuery(this.button).click(function(){
            thisObj.changeColor();
        });
        django.jQuery(content).append(this.color);
        django.jQuery(content).append(this.button);
        return content;
    }
    thisObj=this;
    this.infoWidObj = new google.maps.InfoWindow({
        content:thisObj.getContent()
    });
    this.show = function(latLng){
        this.infoWidObj.setPosition(latLng);
        this.infoWidObj.open(this.map);
    }
    this.remove = function(){
        this.infoWidObj.close();
    }
}

function Point_string(){
    var PolygonArray=[];
    if (flag==0)
    {
        var Point = PointArray[0];
        PointArray.push(Point);
        PolygonArray= PointArray;
    }
    else if(flag==1)
    {
        var Point = curLatLng[0];
        curLatLng.push(Point);
        PolygonArray=  curLatLng;
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

