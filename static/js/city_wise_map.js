/*
 *  Library to parse and display below elements,
 *   1. Admin ward
 *   2. Electoral ward
 *   3. Slum
 *   4. Component/Filter/Sponsor
 *   5. RIM data
 */
//Admin, Electoral, Slum map variables
let WARDLEVEL = ["AdministrativeWard",
                 "ElectoralWard",
                 "Slum"];
let parse_data = {};
let map = null;
let arr_poly_disp = [];
let legends =[];
let city = null;
let objBreadcrumb = null;

//Components/filter variables
let zindex = 0;
let global_slum_id=0;
let lst_sponsor =[];
let parse_component = {};
let modelsection = {
		"General" : "General information" ,
		"Toilet" : "Toilet information",
		"Water" : "Water information",
		"Waste" : "Waste management information",
		"Drainage" : "Drainage information",
		"Road" : "Road & access information",
		"Gutter" : "Gutter information"
};
let TYPE_COMPONENT = {
    'C':'Component',
    'S' :'Sponsor',
    'F' :'Filter'
};

var __extends = (this && this.__extends) || function (d, b) {
    for (var p in b) if (b.hasOwnProperty(p)) d[p] = b[p];
    function __() { this.constructor = d; }
    d.prototype = b === null ? Object.create(b) : (__.prototype = b.prototype, new __());
};

//Polygon custom object
var Polygon = (function () {
    //set polygon details
    function Polygon(obj_data) {
        this.type = obj_data.type;
        this.name = obj_data.name.trim();
        this.info = obj_data.info;
        this.bgColor = obj_data.bgColor || "#FFA3A3";
        this.borderColor = obj_data.borderColor || "#FF0000";
        this.legend = obj_data.legend;
        this.id = obj_data.id;
        this.center = '';//bounds.getCenter();
        this.shape = obj_data.lat;
        this.officeAddress = obj_data.wardOfficeAddress || "";
        this.officerName = obj_data.wardOfficerName || "";
        this.officerTel = obj_data.wardOfficeTel || "";
    }
    //Property to convert shape to polygon object
    Object.defineProperty(Polygon.prototype, "shape", {
        get: function () {
            return this._shape;
        },
        set: function (shape) {
            let par_shape = this.parse_shape(shape);
            this._shape = par_shape;
        },
        enumerable: true,
        configurable: true
    })
    //Parser to convert string of lat/longs to map latlng object
    Polygon.prototype.parse_shape = function(shape){
        let lat = shape.substring(20, shape.length-2);
        let bounds = [];//new google.maps.LatLngBounds();
        let latlong = new google.maps.LatLngBounds();
        $.each(lat.split(','), function(key,val){
            let result = val.trim().split(' ');
            if(result.length > 1){
                bounds.push(new google.maps.LatLng(result[1].trim(), result[0].trim()));
                latlong.extend(new google.maps.LatLng(result[1].trim(), result[0].trim()));
            }
        });
        this.center = latlong;//.getCenter();
        return this.drawPolygon(bounds);
    }
    //Draw polygon using other set of attributes like color, opacity..
    Polygon.prototype.drawPolygon = function(bounds){
        let opacity = 0.4;
        let strokeOpacity = 0.7;
        let poly_options ={
          paths : bounds,
          strokeColor : this.borderColor,
          strokeOpacity : strokeOpacity,
          strokeWeight : 2,
          fillColor : this.bgColor,
          fillOpacity : opacity,
          name : this.name
        }
        let Poly = new google.maps.Polygon(poly_options);
        return Poly;
    }
    //Set up basic listeners for polygon which is displayed on map - say map hover
    Polygon.prototype.setListeners = function (){
        var label_options = {
              map: map,
              position: this.center.getCenter(),
              text: '',
              minZoom: 7,
              zIndex : 999
            };
        var slumLabel = new MapLabel(label_options);
          //slumLabel.changed('text');
        let shapename = this.name
        if (this.type == "Slum")
        {
            shapename = this.type + ': ' +shapename;
        }
        google.maps.event.addListener(this.shape, 'mouseover', function(event) {
          slumLabel.text = shapename;
          slumLabel.changed('text');
        });
        google.maps.event.addListener(this.shape, 'mouseout', function(event) {
          slumLabel.text = '';
          slumLabel.changed('text');
        });
    }
    //Show the polygon on map
    Polygon.prototype.show = function(){
        zIndex = WARDLEVEL.indexOf(this.type) + 1;
        this.shape.setOptions({ zIndex: zIndex });
        this.shape.setMap(map);
        arr_poly_disp.push(this.shape);
        //map.fitBounds(bounds);
    }
    //Hide the polygon on map
    Polygon.prototype.hide = function(){
        this.shape.setMap(null);
    }
    //Hide all the polygon that are displayed on map
    Polygon.prototype.hideAll = function(){
        $.each(arr_poly_disp, function(k,v){
             v.setMap(null);
        });
        arr_poly_disp = [];
        zIndex = 0;
    }
    //Set zoom level
    Polygon.prototype.setZoomLevel = function(zoom){
            map.setZoom(zoom);
    }
    //Set other UI details like info, ward details ...depending on the admin, elect, slum
    Polygon.prototype.event_onClick = function(){
        this.hideAll();
        objBreadcrumb.push(this.name);
        //Header
        myheader = $("#maphead");
        myheader.html('<h4>' + this.name+'</h4>');

        //Info
        let mydesc = $("#mapdesc");
        mydesc.html(this.info);

        let wdaddress = $("#wdaddress");
        let wdofficer = $("#wdofficer");
        let wdhead = $("#wdhead");
        let wdhd = "";
        let wdadd = "";
        let wdname = "";
        if(this.officeAddress!=""){

            wdhd = "<div><b>Details: </b></div>";
            wdadd = "<div class='row'><div  class='col-md-2' style='margin-left:25px'><b>Address :</b> </div><div class='col-md-9'>";
            if (this.officeAddress) {
                wdadd += (this.officeAddress).trim();
            } else {
                wdadd += " - ";
            }
            wdadd += "</div></div>";


            wdname = "<div class='row'><div class='row' style='margin-left:25px'><div class='col-md-2' ><b>Name :</b></div><div class='col-md-10'> ";
            if (this.officerName) {
                wdname += this.officerName;
            } else {
                wdname += " - ";
            }
            wdname += "</div></div>";
            wdname +="<div class='row' style='margin-left:25px'><div class='col-md-2' ><b> Contact :</b></div><div class='col-md-10'> ";
            if (this.officerTel) {
                wdname += this.officerTel;
            } else {
                wdname += " - ";
            }
            wdname += "</div></div></div>";


        }
        wdhead.html(wdhd);
        wdaddress.html(wdadd);
        wdofficer.html(wdname);

    }
    return Polygon;
}());

var Slum = (function (_super) {
    __extends(Slum, _super);
    function Slum(obj_data) {
        obj_data['info'] = obj_data['info'] + "<br/><div style='padding-top:10px;'><a style='font-weight:bold;text-decoration: underline;cursor:pointer;' href='javascript:Slum.prototype.factsheet_click(this,"+obj_data.id+")'>View Factsheet</a></div>";
       _super.call(this, obj_data) || this;
       _super.prototype.show.call(this);
    }
    Slum.prototype.factsheet_click = function(element, slum_id){
        $(".overlay").show();
		var Sid = slum_id;
		var url = "/admin/rimreportgenerate/";
        var Fid = "154";
		$.ajax({
			url : url,
			data : { Sid : Sid, Fid : Fid},
			type: "POST",
			contenttype : "json",
			success : function(json){
					url = json.string;
					$(".overlay").hide();
					window.open("" + url );
			}
		});
    }
    //Set click listeners
    Slum.prototype.setListeners = function(){
        _super.prototype.setListeners.call(this);
        let _this = this;
        google.maps.event.addListener(this.shape, 'click', function(event_shape) {
            let flag= false;
            if(objBreadcrumb.val.length < 3){
                $("#datatable_filter").find("input").val(_this.name);
		        $("#datatable_filter").find("input").trigger('keyup');
		        $("#datatable").find('tbody>tr>td>div>span:contains('+_this.name+')').trigger('click');
		        flag = true;
            }
            else{
                if(event_shape!=undefined){
                        var contentString = '<div id="content" >' + '<div id="bodyContent">' + '<p><b>' + _this.name + '</b></p>' + '<div class="row">' + '<div class="col-md-12">' + '<p style="font-size: 13px;">' + _this.info + '</p> ';
                        //if (obj[arr[0]]["content"][arr[1]]["content"][arr[2]]["content"][arr[3]]['factsheet']) {
                        //contentString += '<p><a href="javascript:factsheet_click(this)">Factsheet</a></p>';
                        //}
                        contentString +='</div>' + '</div>';

                        var infoWindow = new google.maps.InfoWindow({
                            maxWidth : 430
                        });
                        infoWindow.setContent(contentString);
                        infoWindow.setPosition(event_shape.latLng);
                        infoWindow.open(map);
                }
                else{
                    flag=true;
                }
            }
            if(flag){
                slum_data_fetch(_this.id);
            }
            _super.prototype.event_onClick.call(_this);
            _super.prototype.show.call(_this);
            map.fitBounds(_this.center);
        });
    }
    return Slum;
}(Polygon));

var ElectoralWard = (function (_super) {
    __extends(ElectoralWard, _super);
    function ElectoralWard(obj_data) {
        _super.call(this, obj_data) || this;
    }
    //Set click listeners
    ElectoralWard.prototype.setListeners = function(){
        _super.prototype.setListeners.call(this);
        let _this = this;

        google.maps.event.addListener(this.shape, 'click', function(event) {
            _super.prototype.event_onClick.call(_this);
            let bounds = new google.maps.LatLngBounds();
            _super.prototype.show.call(_this);
            $.each(parse_data[objBreadcrumb.val[0]]['content'][_this.name]['content'], function(k,v){
                v.obj.show();
            });
            $.extend(bounds, _this.center);
            map.fitBounds(bounds);
        });
    }
    return ElectoralWard;
}(Polygon));

var AdministrativeWard = (function (_super) {
    __extends(AdministrativeWard, _super);
    function AdministrativeWard(obj_data) {
        _super.call(this, obj_data) || this;
        _super.prototype.show.call(this);
    }
    //Set click listeners
    AdministrativeWard.prototype.setListeners = function(){
        _super.prototype.setListeners.call(this);
        let _this = this;
        google.maps.event.addListener(this.shape, 'click', function(event) {
            _super.prototype.event_onClick.call(_this);
            let bounds = new google.maps.LatLngBounds();
            $.each(parse_data[_this.name]['content'], function(k,v){
                v.obj.show();
                $.each(v['content'], function(key,val){
                    val.obj.show();
                });
            });
            $.extend(bounds, _this.center);
            map.fitBounds(bounds);
        });
    }
    return AdministrativeWard;
}(Polygon));

//As there is no  city detials. Created a dummy city class.
var City = (function(){

    function City (name){
        this.name = name;
        this.shape = { 'click':this.click };
    }
    //Added click listener to display top level details from where it started.
    City.prototype.click = function(){
        $.each(arr_poly_disp, function(k,v){
             v.setMap(null);
        });
        arr_poly_disp = [];
        let bounds = new google.maps.LatLngBounds();
        $.each(parse_data, function(key,value){
            value.obj.show();
            $.each(value['content'], function(k1,v1){
                $.each(v1['content'], function(k2,v2){
                    v2.obj.show();
                });
            });
            $.extend(bounds, value.obj.center);
        });
        map.fitBounds(bounds);
        map.setZoom(12);
        myheader = $("#maphead");
        myheader.html('');

        //Info
        let mydesc = $("#mapdesc");
        mydesc.html('');
        let wdaddress = $("#wdaddress");
        let wdofficer = $("#wdofficer");
        let wdhead = $("#wdhead");
        wdhead.html('');
        wdofficer.html('');
        wdaddress.html('');
    }
    return City;
}());
//AdministrativeWard.prototype = Object.create(Polygon.prototype);
//ElectoralWard.prototype = Object.create(Polygon.prototype);
//Slum.prototype = Object.create(Polygon.prototype);

//Parser to Initiates the objects depending on admin, elect, slum
var Parser = (function() {
       function Parser(index, data){
            this.index = index;
            this.data = data;
       }
       //Render through each and every level and return above class objects
       Parser.prototype.render = function(){

             let wards = {};
             let w_data = {}
             let ward = this.ward_data();
             wards[this.data.name] = {"obj":ward, /*"name":this.data.name,*/ /*"content":{}*/}
             ;
             if (this.data.content != undefined && this.data.content != null){
                 let _this = this;
                 legends.push((this.data.name).trim());
                 $.each(this.data.content, function(key,value){

                    let objParse = new Parser(_this.index+1, value);
                    let ward = objParse.render();

                     $.extend(w_data, ward);
                 });
                 legends.pop();
                 wards[this.data.name]["content"] = w_data;
             }

             return wards;
       }
        // Some custom setup before creating above objects
       Parser.prototype.ward_data = function(){
            let dataval = $.extend({}, this.data);
            delete dataval['content'];
            dataval['type'] = WARDLEVEL[this.index];
            var details = [];
            $.extend(details, legends);
            dataval['legend'] = details || [];
            let ward = new (eval(WARDLEVEL[this.index]))(dataval);
            delete dataval;
            ward.setListeners();
            return ward;
       }
        return Parser;
}());

//Class to handle breadcrumbs and there clicks with datatable refresh.
var Breadcrumbs = (function(){

        function Breadcrumbs(val){
            this.val = val;
            this.mydatatable = null;
            this.datatable_data = [];
        }
        Object.defineProperty(Breadcrumbs.prototype, "val", {
            get: function () {
                return this._val;
            },
            set: function (val) {
                this._val = val;
                this.draw();
            },
            enumerable: true,
            configurable: true
        });
        //Re-draw the breadcrumb on update of val
        Breadcrumbs.prototype.draw = function(){
            let mydiv = $("#maplink");
            mydiv.html("");
            var aTag = "   ";
            aTag += '<label id="Home" onclick="Breadcrumbs.prototype.breadcrumb_onClick(this, false);">' + " <span style='text-decoration: underline;cursor:pointer;color:blue;'>"+ city.name +"</span></label>&nbsp;&nbsp; >> ";
            $.each(this.val, function(key,val){
                aTag += '<label id="' + val + '" onclick="Breadcrumbs.prototype.breadcrumb_onClick(this, true);">' + " <span style='text-decoration: underline;cursor:pointer;color:blue;'>" + val + "</span></label>&nbsp;&nbsp; >> ";
            });
            mydiv.html((aTag.slice(0,aTag.length - 3)).trim());
            this.drawDatatable();
        }
        //Push the element
        Breadcrumbs.prototype.push = function(data){
             data = data.trim();
             if (this.val.indexOf(data) < 0){
                 this.val.push(data);
                 this.draw();
             }
        }
        //Remove element and redraw element
        Breadcrumbs.prototype.slice = function(removeIndi){
            this.val.splice(removeIndi, 4);
            this.draw();

        }
        //Breadcrumb click event
        Breadcrumbs.prototype.breadcrumb_onClick = function(tag, flag){
            let removeIndi = 0;
            let obj_click = city;
            let original = objBreadcrumb.val.length;

            if(flag){
                let textelement = (tag.textContent).toString().trim();
                removeIndi = objBreadcrumb.val.indexOf(textelement) + 1;
                if (removeIndi < objBreadcrumb.val.length){
                    objBreadcrumb.slice(removeIndi);
                    obj_click = parse_data[objBreadcrumb.val[0]];
                    if(objBreadcrumb.val.length == 2)
                        obj_click = obj_click.content[objBreadcrumb.val[1]];

                    google.maps.event.trigger(obj_click.obj.shape, 'click');
                }
            }
            else{
                objBreadcrumb.slice(removeIndi);
                obj_click.shape.click();
            }
            if(original == 3 && original > objBreadcrumb.val.length){
                $("#compochk").find("input[type=checkbox][name=grpchk]:checked").click();
                $("#compochk").html("");
                global_slum_id=0;
                zindex = 0;
                lst_sponsor =[];
                parse_component ={};
            }
        }
        //Datatable renderer
        Breadcrumbs.prototype.drawDatatable = function(){
            let data = parse_data;
             try{
            $.each(this.val, function(key, value){
                data = data[value].content;
            });
            }
            catch(e){
                data=[];
            }
            let _this = this;
            this.datatable_data = [];
            $.each(data, function(k,v){
                _this.datatableParser(v, _this);
            });
            if(this.datatable_data.length > 0){
                this.mydatatable = $("#datatable").dataTable({
                    "aaData" : this.datatable_data,
                    "bDestroy" : true,
                    "order" : [[0, "asc"]],
                    "aoColumns" : [{
                        "title" : '<div style="font-size: large;font-weight: 900;">' + "Slums" + '</div>',
                        "mDataProp" : "name",
                        "mRender" : function(oObj, val, setval) {

                            var desc = "";
                            if (setval.legend.length > 0 )
                                desc = ' ('+setval.legend.join(" >> ") + ')';
                            return '<div><span onclick="Breadcrumbs.prototype.datatableSlum_onClick(this);" style="font-weight: 900;font-size: small;color: blue;cursor: pointer;" name="divSlum" data="' + setval.legend.join(":") + ":" + setval.name + '">' + setval.name + desc + ' </span></div>' + '<div style="font-size: small;">' + setval.info + '</div>';
                        }
                    }]
                });
                $("#datatablecontainer").show();
            }
            else{
                $("#datatablecontainer").hide();
            }
        }
        //Data parser for datatable
        Breadcrumbs.prototype.datatableParser = function(data_val, bread){
             let _this = bread;
             if (data_val.content != undefined && data_val.content != null){
                $.each(data_val.content, function(key,val){
                    _this.datatableParser(val, _this);
                });
             }
             else{
                _this.datatable_data.push(data_val.obj);
             }

        }
        //Datatable row click event
        Breadcrumbs.prototype.datatableSlum_onClick = function (row){
            data = $(row).attr("data");
            arr_data = data.split(":");
            objBreadcrumb.val = arr_data;
            $.each(arr_poly_disp, function(k,v){
                if(v.name == arr_data[2]){
                   google.maps.event.trigger(v, 'click');
                }
            });

        }
        return Breadcrumbs;
}());

function initMap12() {
    labelmap();
    map = new google.maps.Map(document.getElementById('map12'), {
        center : {
            lat : 19.489339,
            lng : 74.631617
        },
        zoom : 6,
        mapTypeId : 'satellite',
    });

    $(".overlay").show();
    var city_id = $("#city_id").val();
    var city_name = $("#city_name").val();
    $.ajax({
        url : "/admin/slummapdisplay/" + city_id + "/",
        type : "GET",
        contenttype : "json",
        success : function(json) {
            let bounds = new google.maps.LatLngBounds();
            let data = json['content'];
            city = new City(city_name);

            $.each(data, function(key, value){
                let obj_parser = new Parser(0, value);
                let ward = obj_parser.render();
                $.extend(bounds, ward[key].obj.center);
                $.extend(parse_data, ward);
            });
            objBreadcrumb = new Breadcrumbs([]);
            map.setCenter(bounds.getCenter());
            map.fitBounds(bounds);
            map.setZoom(12);

            //slum name is put in the search box and enter is fired, the irt search result is loaded
           $(document).ready(function() {
                var slumname = $('#slum_name').val();
                if (slumname != "")
                {
                    $("#datatable_filter").find("input").val(slumname)
                        $("#datatable_filter").find("input").val(slumname)
                        $("#datatable span").get(0).click();
                }   
            });
             
            $(".overlay").hide();
        }
    });
}

//Base class for shape components
var Shape =(function(){
    function Shape(obj_shape){
         this.name = obj_shape.housenumber;
         this._this = obj_shape._this;
         this.type = obj_shape.shape.type;
         this.center = '';
         this.coordinates = obj_shape.shape.coordinates;
    }
    Object.defineProperty(Shape.prototype, "coordinates", {
        get: function () {
            return this._coordinates;
        },
        set: function (coordinates_data) {
            let par_coordinates = this.parse_coordinates(coordinates_data);
            this._coordinates = par_coordinates;
        },
        enumerable: true,
        configurable: true
    })
    //Parse the co-ordinates and convert it to appropiate format required by geometry.
    Shape.prototype.parse_coordinates = function(coordinates_data){
        let bounds = [];//new google.maps.LatLngBounds();
        let latlong = new google.maps.LatLngBounds();
        let coordinates = coordinates_data;
        if (coordinates_data.length == 2)
            coordinates = [coordinates_data];
        if (coordinates_data.length == 1)
            coordinates = coordinates_data[0];
        $.each(coordinates, function(key,val){
            bounds.push(new google.maps.LatLng(val[1], val[0]));
            latlong.extend(new google.maps.LatLng(val[1], val[0]));
        });
        this.center = latlong.getCenter();
        return bounds;
    }
    //Iterate through all the geometry elements and draw them appropiately.
    Shape.prototype.geometry = function(){
        let geo = eval('this.'+this.type +'()');
        var options = {
            map: map,
            position: this.center,
            text: '',
            minZoom: 8,
            zIndex : 999
        };
        var slumLabel = new MapLabel(options);
        let _this = this;    //slumLabel.changed('text');
        google.maps.event.addListener(geo, 'mouseover', function(event) {
            slumLabel.text = _this.name;
            slumLabel.changed('text');
        });
        google.maps.event.addListener(geo, 'mouseout', function(event) {
            slumLabel.text = '';
            slumLabel.changed('text');
        });
        return geo;
    }
    //Draw polygon
    Shape.prototype.Polygon = function(){
        let chkPoly = new google.maps.Polygon({
            paths : this.coordinates,
            strokeColor : this._this.chklinecolor,
            strokeOpacity : 0.7,
            strokeWeight : this._this.chklinewidth,
            fillColor : this._this.chkcolor,
            fillOpacity : 0.6,
            center : this.center,
            zIndex:1,
        });
        if(this._this.name == "Houses")
            this.household_details(chkPoly, this.name);
        return chkPoly;
    }
    //Draw linestring
    Shape.prototype.LineString = function(){
        let chkPoly = new google.maps.Polyline({
            path : this.coordinates,
            strokeColor : this._this.chklinecolor,
            strokeOpacity : 0.8,
            strokeWeight : this._this.chklinewidth
        });
        return chkPoly;
    }
    //Draw point with the icon
    Shape.prototype.Point = function(){
        let chklinecolor = this._this.chklinecolor;
        let pinImage = new google.maps.MarkerImage("http://www.googlemapsmarkers.com/v1/" + chklinecolor.substring(1, chklinecolor.length) + "/");
        if (this._this.icon!=undefined && this._this.icon!=""){
            pinImage = new google.maps.MarkerImage(this._this.icon)//"http://www.googlemapsmarkers.com/v1/" + chklinecolor.substring(1, chklinecolor.length) + "/");
        }
       chkPoint = new google.maps.Marker({
            position : this.coordinates[0],
            icon : pinImage,
        });
        return chkPoint;
    }
    //For component type houses add a click event which displays all the household detials
    Shape.prototype.household_details = function (shape, housenumber){
        var sponsorinfo = new google.maps.InfoWindow({
            maxWidth : 430,
            minWidth : 100,
            minHeight : 100
        });
		sponsorinfo.setContent('<div class="overlay" style="display: block;"><div id="loading-img"></div></div>');
        google.maps.event.addListener(shape, 'click', function(event) {
            $.each(lst_sponsor, function(k, v) {
                v.close();
            });
            lst_sponsor = [];
            sponsorinfo.setPosition(event.latLng);
            $.ajax({
                url : '/component/get_kobo_RHS_list/' + global_slum_id + '/' + housenumber,
                type : "GET",
                contenttype : "json",
                success : function(json) {
                    var spstr = "";
                    spstr += '<table class="table table-striped" style="font-size: 10px;"><tbody>';
                    if(json['FFReport']){
                        flag = false;
                        let fields = $("a[name=chk_group]:contains('Sponsor')").parent().find('input[type=checkbox]');
                        fields.slice(0, fields.length - 1).each(function(ind, chk){
                                if($(chk).is(":checked")){
                                        flag=true;
                                    }
                        });
                        if (flag){
                        spstr += '<tr><td colspan="2"><a href="javascript:Shape.prototype.familyfactsheet_click('+global_slum_id+', '+housenumber+')" style="cursor:pointer;color:darkred;">View Factsheet</a></td></tr>';
                        }
                    }
                    var flag = false;
                    $.each(json, function(k, v) {
                        flag = true;
                        spstr += '<tr><td>' + k + '</td><td>' + v + '</td></tr>';
                    });
                    spstr += '</tbody></table>';
                    if (flag){
                        sponsorinfo.setContent(spstr);
                        lst_sponsor.push(sponsorinfo);
                        sponsorinfo.open(map);
                    }
                }

            });
        });
    }
    //Family factsheet click event.
    Shape.prototype.familyfactsheet_click = function(slum, house){
        $(".overlay").show();
        $.ajax({
            url : '/admin/familyrportgenerate/',
            data : { Sid : slum, HouseNo : house},
            type: "POST",
            contenttype : "json",
            success : function(json){
                  $(".overlay").hide();
                    if (json['string']!=undefined){
                    url = json.string;
                    window.open("" + url );
                }
                else{
                    alert(json['error']);
                }
            },
            error:function(){
                $(".overlay").hide();
            }
        });
    }
    return Shape;
}());

//Parse for each of the components
var BaseShape = (function(){
    function BaseShape(obj_component){
        this.icon = obj_component.icon;
        this.name = obj_component.name;
        this.chkcolor = obj_component.blob.polycolor || "#FFA3A3";
        this.chklinecolor = obj_component.blob.linecolor || "#ff0000";
        this.chklinewidth = obj_component.blob.linewidth || "1";
        this.type = obj_component.type;
        this.count = obj_component.count;
        this.child = obj_component.child;
        this.icon = obj_component.icon;
    }
    //Property to convert shape to polygon object
    Object.defineProperty(BaseShape.prototype, "child", {
        get: function () {
            return this._child;
        },
        set: function (child) {
            let par_child = null;
            if(this.type != 'C'){
                par_child = this.parse_filter(child);
            }
            else{
                par_child = this.parse_component(child);
            }
            this._child = par_child;
        },
        enumerable: true,
        configurable: true
    })
    //Parse all the component type component and create appropiate geometry objects
    BaseShape.prototype.parse_component = function(child){
        let parse_child = {};
        let _this = this;
        $.each(child, function(k,v){
            v['_this'] = _this;
            let obj_shape = new Shape(v);
            let geo_shape = obj_shape.geometry();
            parse_child[obj_shape.name] = geo_shape;
        });
        return parse_child;
    }
    // Parse all the component type filters, sponsors and copy the object from component.
    BaseShape.prototype.parse_filter = function(child){
        let data = {};
        let houses = parse_component["Houses"].child;
        let _this = this
        $.each(child, function(k,v){
            if( v in houses){
                let geo = {};
                $.extend(geo, houses[v]);
                geo.setOptions({
                    strokeColor : _this.chklinecolor,
                    strokeWeight : _this.chklinewidth,
                    fillColor : _this.chkcolor,
                });
                data[v] = geo;
            }
        });
        return data;
    }
    //Show all the component selected
    BaseShape.prototype.show = function(){
        zindex++;
        $.each(this.child, function(k,v){
            //v.setMap(map);
            v.set("zIndex", zindex);
	    v.setMap(map);
        });
    }
    //Hide all the component unselected
    BaseShape.prototype.hide = function(){
        $.each(this.child, function(k,v){
            v.set("zIndex", null);
            v.setMap(null);
        });
    }
    return BaseShape;
}());

//Component type component
var Component =(function(_super){
    __extends(Component, _super);
    function Component(obj_component){
        _super.call(this, obj_component) || this;
    }
    return Component;
}(BaseShape));

//Component type filter
var Filter = (function(_super){
    __extends(Filter, _super);
    function Filter(obj_filter){
        _super.call(this, obj_filter) || this;
    }
    return Filter;
}(BaseShape));

//Component type sponsor
var Sponsor = (function(_super){
    __extends(Sponsor, _super);
    function Sponsor(obj_sponsor){
        _super.call(this, obj_sponsor) || this;
    }
    return Sponsor;
}(BaseShape));

// Get filters and RIM data after selecting particular slum
function slum_data_fetch(slumId){
    let compochk = $("#compochk");
    compochk.html('<div style="height:300px;width:300px;"><div id="loading-img"></div></div>');
	var ajax_calls = [$.ajax({
            url : '/component/get_component/' + slumId,
            type : "GET",
            contenttype : "json"
        }),
        $.ajax({
            url : '/component/get_kobo_RIM_data/' + slumId,
            type : "GET",
            contenttype : "json"
        })
	];

    Promise.all(ajax_calls).then(function(result) {
        global_slum_id =slumId;
        generate_filter(slumId, result[0]);
        generate_RIM(result[1]);
    });

}

//Populate RIM data modal pop-up's as per section wise.
function generate_RIM(result){
    $("#rim").html('');
    if('General' in result){
        try{
        result['General']['admin_ward']=objBreadcrumb.val[0];
        result['General']['slum_name']=objBreadcrumb.val[2];
        }catch(e){}
    }
    $.each(result, function(k,v){
        let modal = $("#myModal").clone();
        modal.find('#modelhdtext').html(modelsection[k]);
        modal.attr({'id': k});
        let spstr ="";
        let commentstr ="";
        spstr += '<table class="table table-striped"  style="margin-bottom:0px;font-size: 12px;">';

        if ( v instanceof Array) {
            modal.find('div.modal-dialog').addClass("modal-lg");
            let toilet_header = "<thead><tr><th>&nbsp;</th>";
            let toilet_body = "<tbody>";
            for (i=0; i<v.length; i++){
                toilet_header += "<th> CTB " +(i+1) + "</th>";
            }
            toilet_header+= "</tr></thead>";
            if(v.length > 0){
                keys_headers = Object.keys(v[0]);
                $.each(keys_headers.slice(3, keys_headers.length-1), function(key, val) {
                    toilet_body += '<tr><td style="font-weight:bold;width:200px;">' + val + '</td>';

                    for (i=0; i<v.length; i++){
                        value = v[i][val];
                        if(value == undefined)
                                value="&nbsp;";
                        toilet_body += '<td>' + value + '</td>';
                    }
                    toilet_body += '</tr>';
                });
            }
            else{
                toilet_body += '<tr><td>No CTB\'s</td></tr>';
            }
            spstr += toilet_header + toilet_body;
        }
        else{
            modal.find('div.modal-dialog').removeClass('modal-lg');
            spstr += "<tbody>";
            $.each(v, function(key, val) {
                if (key.indexOf("comment") != -1 || key.indexOf("Describe") != -1) {
                    commentstr += '<tr><td  colspan=2><label style="font-weight:bold;">' + key + ': </label> ' + val + '</td></tr>';
                } else {
                    spstr += '<tr><td style="font-weight:bold;width:50%;">' + key + '</td><td>' + val + '</td></tr>';
                }

            });
        }
        spstr += commentstr + '</tbody></table>';
        modal.find('#modelbody').html(spstr);
        $("#rim").append(modal);

        $("div.panel-collapse[name='"+modelsection[k]+"']").prepend('<div name="div_group" >' + '&nbsp;&nbsp;&nbsp;' + '<span><a style="cursor:pointer;color:darkred;" data-toggle="modal" data-target="#'+k+'">View Tabular Data</a><span>' + '</div>');
    });
}
// Generates right filter
function generate_filter(slumID, result){
    let compochk = $("#compochk");
    let counter = 0;
    let panel_component = "";
    $.each(result, function(k, v){
        counter = counter + 1;
		panel_component += '<div name="div_group" class=" panel  panel-default panel-heading"> ' +
		                    '<input class="chk" name="grpchk" type="checkbox" onclick="checkAllGroup(this)"></input>&nbsp;&nbsp;<a name="chk_group" data-toggle="collapse" data-parent="#compochk" href="#' + counter + '"><b>' + k + '</b></a>' +
		                    '</br>'

		panel_component += '<div id="' + counter + '" class="panel-collapse collapse" name="'+k+'">';

        $.each(v, function(k1, v1) {
            let chkcolor = v1['blob']['polycolor'];
            panel_component += '<div name="div_group" >' + '&nbsp;&nbsp;&nbsp;' +
                                 '<input name="chk1" class="chk" style="background:'+chkcolor+';background-color:' + chkcolor + '; " selection="' + k + '" component_type="' + v1['type'] + '" type="checkbox" value="' + k1 + '" onclick="checkSingleGroup(this);" >' +
                                   '<a>&nbsp;' + k1 + '</a>&nbsp;(' + v1['child'].length + ')' +
                                 '</input>' +
                                '</div>';

            let obj  = eval('new '+TYPE_COMPONENT[v1.type]+'(v1)');
             parse_component[k1] = obj;
        });

		panel_component += '</div></div>';
    });
    compochk.html(panel_component);
}

//Event handler for check/uncheck all boxes as per the section
function checkAllGroup(grpchk){
    if($(grpchk).is(':checked')){
        $(grpchk).parent().find('[name=chk1]:not(:checked)').click();
        if($(grpchk).parent().find('div.in').length == 0)
            $(grpchk).parent().find('a[name=chk_group]').click();
    }
    else{
        $(grpchk).parent().find('[name=chk1]:checked').click();
        if ($(grpchk).parent().find('div.in').length > 0)
            $(grpchk).parent().find('a[name=chk_group]').click();
    }
}
//Event handler for checkbox selection for the filter ON / OFF
function checkSingleGroup(singlechk){
    /*if(arr_poly_disp.length > 0){
        arr_poly_disp[0].setMap(null);
        arr_poly_disp = [];
    } */
    $.each(arr_poly_disp, function(k,v){
        v.setMap(null);
      });
    var l = map.getZoom();
    map.setZoom(l+1);
    map.setZoom(l);
    var chkchild = $(singlechk).val();
	var section = $(singlechk).attr('selection');
	var component_type = $(singlechk).attr('component_type');
	if ($(singlechk).is(':checked')){
        parse_component[chkchild].show();
	}
	else{
        parse_component[chkchild].hide();
	}
	let flag = false;
	if($(singlechk).parent().parent().parent().find('[name=chk1]:checked').length >0)
	    flag=true;
	$(singlechk).parent().parent().parent().find('[name=grpchk]')[0].checked =flag;
//    map.setZoom(l+1);
    var s = map.setZoom(l);
}
