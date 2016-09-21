
   var map;
   var obj;
   
   
   function initMap12() {
   	    
        map = new google.maps.Map(document.getElementById('map12'), {
          center: {lat: 16.7003848629408189, lng: 74.2311403557174003 },  
          zoom: 12,
          mapTypeId: 'satellite',
        });        
   } 
   
   function initMap(obj,maplat) {
   	    console.log("I ma in new map");
        map = new google.maps.Map(document.getElementById('map12'), {
          center: maplat ,  
          zoom: 12,
          mapTypeId: 'satellite',
        });
        getcordinates(obj);        
   } 
   
   
   $(document).ready(function(){
        loaddata();
   });

    function loaddata(){    	
        var url = "http://192.168.0.126:8006/admin/slummapdisplay";
        $.ajax({
                url : url,type: "GET",contenttype : "json",
                success : function(json){
                   obj=json ;	
                   getcordinates(obj);
            	}
    	});
    }
    
    
    var Poly;
    var ShapeValue;
    var shapecount="";
    
    //obj=json['KMC']['content']
    function getcordinates( obj ){
    	//console.log(json['Pune']['content'] ); 
    	//ShapeValue=json['Pune']['content']['Pune Nagar Road Administrative Ward No.7']['lat'] ;
    	
    	for (var key in obj){  
        	try {
    			latlongformat(obj[key]['lat'], obj[key]['name']); 
			}
			catch(err) {
    			latlongformat(obj['lat'], obj['name']); 
			}       	
    	}		
    }
    var arr=[];
    function latlongformat(ShapeValue, shapename){
    	var PolygonPoints=[];
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
		    PolygonPoints.pop();
		    //
		    drawPolygon(PolygonPoints);
		    
		    //
		    var infoWindow= new google.maps.InfoWindow;
		    
		    google.maps.event.addListener(Poly, 'mouseover', function(event){		         
		        
		        if(infoWindow.getContent() != shapecount){
		        	console.log(infoWindow.getContent());
		        	console.log(shapecount);
		        	console.log("i m in IF");     	
		        	shapecount=infoWindow.getContent();
		        	infoWindow.setContent(shapename);
  					infoWindow.setPosition(event.latLng);
  					//infoWindow.open(map);
		        }else{
		        	shapecount=infoWindow.getContent();
		        	console.log("i m in else");   
		        }
			});
			
			google.maps.event.addListener(Poly, 'mouseout', function(event){
		         //infoWindow.close();
			});
			
			google.maps.event.addListener(Poly, 'click', function(event){		         
		        console.log(obj['content']);
		        arr.push(shapename);
		        data = fetchData(obj);
		        console.log(data);
		        
		        if(arr.length == 3){
		        	val = obj[arr[0]]["content"][arr[1]]["content"][arr[2]]
		        	data[arr[2]] = val;
		        }
		        
		        //initMap();
		        initMap(data, event.latLng.toJSON() );
		        		         
		         
			});
						
		    		    
    }    
    
    function fetchData(obj){
    	var o = obj;
    	$.each(arr, function(index,val){
    		o = o[val]['content'];
    	});
    	return o
    	
    	
    }
    
    function drawPolygon(PolygonPoints){
    	Poly = new google.maps.Polygon({
		        paths: PolygonPoints,
		        strokeColor: '#FF0000',
		        strokeOpacity: 0.8,
		        strokeWeight: 2,
		        fillColor: '#FF0000',
		        fillOpacity: 0.35		       
		    });		
		    Poly.setMap(map);
		    
		    
	        
		    
    }
    
