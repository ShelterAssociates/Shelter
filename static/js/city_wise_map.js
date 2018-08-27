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
let houses= null;
//Components/filter variables
let zindex = 0;
let global_slum_id=0;
let lst_sponsor =[];
let parse_component = {};
let modelsection = {
		"General" : "General information" ,
		"Toilet" : "Status of sanitation (2015-16)",
		"Water" : "Type of water connection",
		"Waste" : "Facility of solid waste collection",
		"Drainage" : "Drainage information",
		"Road" : "Road & access information",
		"Gutter" : "Gutter information"
};
let TYPE_COMPONENT = {
    'C':'Component',
    'S' :'Sponsor',
    'F' :'Filter'
};
var myCustomColour = '#583470'
var markerHtmlStyles = 'background-color: myCustomColour;width: 3rem;height: 3rem;display: block;left: -1.5rem;top: -1.5rem;position: relative;border-radius: 3rem 3rem 0;transform: rotate(45deg);border: 1px solid #FFFFFF';
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
        slum_bgColor = "#A3A3FF";
        slum_borderColor = "#3232FF";
        if(obj_data.associated){
            slum_bgColor = "#FFA3A3";
            slum_borderColor = "#FF0000";
        }
        this.bgColor = obj_data.bgColor || slum_bgColor;
        this.borderColor = obj_data.borderColor || slum_borderColor;
        this.legend = obj_data.legend;
        this.id = obj_data.id;
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
            let par_shape = this.drawPolygon(shape);
            this._shape = par_shape;
        },
        enumerable: true,
        configurable: true
    })

    //Draw polygon using other set of attributes like color, opacity..
    Polygon.prototype.drawPolygon = function(bounds){
        let opacity = 0.4;
        let strokeOpacity = 0.7;
        let poly_options ={
          color : this.borderColor,
          opacity : strokeOpacity,
          weight : 2,
          fillColor : this.bgColor,
          fillOpacity : opacity,
          name : this.name
        }
        var Poly = L.geoJson(bounds, {style:poly_options/*, onEachFeature:admin_onEachFeature*/});
        var return_poly;
        Poly.eachLayer(function(layer){
            return_poly = layer;
        });
        //Poly.addTo(map);
        return return_poly;
    }
    //Set up basic listeners for polygon which is displayed on map - say map hover
    Polygon.prototype.setListeners = function (){
        let shapename = this.name
        if (this.type == "Slum")
        {
            shapename = this.type + ' : ' + this.name;
            //shapename = '<div id="content" >' + '<div id="bodyContent">' + '<p><b>' + this.name + '</b></p>' + '<div class="row">' + '<div class="col-md-12">' + '<p style="font-size: 13px;">' + this.info + '</p> ';
            //shapename +='</div>' + '</div>';
        }
        this.shape.bindPopup(shapename,{autoPan:true});
        this.shape.on({
        'mouseover': function (ev) {
                        this.openPopup();
                     },
        'mouseout' : function(ev){
                        this.closePopup();
                    }

        });
    }
    //Show the polygon on map
    Polygon.prototype.show = function(){
            map.addLayer(this.shape);
            if (this.type == "Slum"){
            this.shape.bringToFront();}
            arr_poly_disp.push(this);
    }
    //Hide the polygon on map
    Polygon.prototype.hide = function(){
            map.removeLayer(this.shape);
    }
    //Hide all the polygon that are displayed on map
    Polygon.prototype.hideAll = function(){
        $.each(arr_poly_disp, function(k,v){
            map.removeLayer(v.shape)
        });
        arr_poly_disp = [];
        zIndex = 0;
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
        this.shape.on({
            'click' : function(event) {

            let flag= false;
            if(objBreadcrumb.val.length < 2){
                $("#datatable_filter").find("input").val(_this.name);
		        $("#datatable_filter").find("input").trigger('keyup');
		        $("#datatable").find('tbody>tr>td>div>span:contains('+_this.name+')').trigger('click');
		        flag = true;
            }
            else{
                if(event!=undefined){
                     slum_data_fetch(_this.id);
                }

            }

            _super.prototype.event_onClick.call(_this);
            _super.prototype.show.call(_this);
            map.fitBounds(_this.shape.getBounds());

            }});
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

        this.shape.on({'click':function(event) {
            _super.prototype.event_onClick.call(_this);
                _super.prototype.show.call(_this);
                $.each(parse_data[objBreadcrumb.val[0]]['content'][_this.name]['content'], function(k,v){
                    v.obj.show();
                });
                map.fitBounds(_this.shape.getBounds());
            }});
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
        this.shape.on({'click': function(event) {
            _super.prototype.event_onClick.call(_this);

            $.each(parse_data[_this.name]['content'], function(k,v){
                v.obj.show();
                $.each(v['content'], function(key,val){
                    val.obj.show();
                });
            });
            map.fitBounds(_this.shape.getBounds());
            }});
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
             map.removeLayer(v.shape);
        });
        arr_poly_disp = [];
        $.each(parse_data, function(key,value){
            value.obj.show();
            $.each(value['content'], function(k1,v1){
                $.each(v1['content'], function(k2,v2){
                    v2.obj.show();
                    //v2.obj.shape.bringToFront();
                });
            });

        });
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

                    obj_click.obj.shape.fireEvent('click');
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
                $("#div_legend").show();
            }
            else{
                $("#datatablecontainer").hide();
                $("#div_legend").hide();
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
                    //map.fireEvent('click', {latlng:v.shape.getCenter()})
                    var latlngPoint = v.shape.getBounds().getCenter();

                    //map.fire('click',{latlng:L.latLng([latlngPoint.lat,latlngPoint.lng])});
                   v.shape.fire('click');
                }
            });

        }
        return Breadcrumbs;
}());
function initMap12() {

    $(".overlay").show();
    var city_id = $("#city_id").val();
    var city_name = $("#city_name").val();
    $.ajax({
        url : "/admin/slummapdisplay/" + city_id + "/",
        type : "GET",
        contenttype : "json",
        success : function(json) {
            let data = json['content'];
            city = new City(city_name);
            $.each(data, function(key, value){
                let obj_parser = new Parser(0, value);
                let ward = obj_parser.render();
                $.extend(parse_data, ward);
            });
            objBreadcrumb = new Breadcrumbs([]);

            //slum name is put in the search box and enter is fired, the irt search result is loaded
           $(document).ready(function() {
                var slumname = $('#slum_name').val();
                if (slumname != "")
                {
		            var slum_input = $("#datatable_filter").find("input");
                    slum_input.val(slumname);
                    slum_input.keyup();
                    $("#datatable span").get(0).click();
                }
            });

            $(".overlay").hide();
        }
    });
}

function initMap(){
    let center_data = {"Navi Mumbai":new L.LatLng(19.09118307623272, 73.0159571631209),
                        "Thane":new L.LatLng(19.215441921044757, 72.98368482425371),
                        "Sangli":new L.LatLng(16.850235500492538, 74.60914487360401),
                        "Kolhapur":new L.LatLng(16.700800029695312, 74.23729060058895),
                        "PCMC":new L.LatLng(18.640083, 73.825560),
                        "Pune":new L.LatLng(18.51099762698481, 73.86055464212859)};
    var pos = new L.LatLng(18.640083, 73.825560);
    if ($('#city_name').val() in center_data)
    {
        pos = center_data[$('#city_name').val()];
    }
    map = new L.Map('map', {
                    center: pos,
                    zoom: 12,
                    zoomSnap: 0.25,
                    markerZoomAnimation:false
                });

    var ggl = L.gridLayer.googleMutant({type: 'satellite' }).addTo(map);
    initMap12();
}

//////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////
//                  Slum Component code
//////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////
function onEachFeature(feature, layer){
        if ('properties' in feature && 'name' in feature.properties){
            var name = feature.properties.name;
            layer.bindPopup("House:"+name);
            layer.on('mouseover', function (e) {
                this.openPopup();
            });
            layer.on('mouseout', function (e) {
                this.closePopup();
            });
//          layer.on('mousemove', function (e) {
//            e.target.closePopup();
//            var popup = e.target.getPopup();
//            popup.setLatLng(e.latlng).openOn(map);
//          });
            layer.on('click', function(e){
                household_details(name);
            });

        }
    }
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

    BaseShape.prototype.style_geo_geometry = function (shape_geo){
           style_geometry = { style :{
                strokeColor : this.chklinecolor,
                strokeOpacity : 0.8,
                strokeWeight : this.chklinewidth
                }
               };

           if (shape_geo.type == "Point"){
                let chklinecolor = this.chklinecolor;
                myCustomColour = chklinecolor;

                let pinImage =  L.divIcon({ html: '<i class="fa fa-truck" style="color: '+chklinecolor+'"></i>',
                                            iconSize: [20, 20],
                                            className: 'myDivIcon'
                                          });
                if (this.icon!=undefined && this.icon!=""){
                    icon_image = this.icon;
                    pinImage = new L.Icon({
                                            iconUrl: icon_image,
                                       });//"http://www.googlemapsmarkers.com/v1/" + chklinecolor.substring(1, chklinecolor.length) + "/");
               }
                style_geometry = {  icon : pinImage,
                                    pointToLayer: function(feature, latlng) {
                                        return L.marker(latlng, {
                                          icon: pinImage
                                        });
                                    }
                                 };
           }
           else if (shape_geo.type == "Polygon"){
                style_geometry['style'] = {
                    color : this.chklinecolor,
                    opacity : 0.7,
                    weight : this.chklinewidth,
                    fillColor : this.chkcolor,
                    fillOpacity : 0.6,
                }

            }
            style_geometry['onEachFeature'] = onEachFeature;
            return style_geometry;
        }
    //Parse all the component type component and create appropiate geometry objects
    BaseShape.prototype.parse_component = function(child){
        let parse_child = {};
        let _this = this;
        list_draw = [];
        $.each(child, function(k,v){
            list_draw.push(v.shape);
        });
        parse_child = L.geoJson(list_draw, this.style_geo_geometry(child[0].shape));
        return parse_child;
    }
    // Parse all the component type filters, sponsors and copy the object from component.
    BaseShape.prototype.parse_filter = function(child){
        let parse_child = {};
        let filter_houses = [];
        let _this = this
        $.each(child, function(k,v){
            if( v in houses){
                   filter_houses.push(houses[v])
            }
        });

        parse_child = L.geoJson(filter_houses, this.style_geo_geometry(filter_houses[0]));
        return parse_child;
    }
    //Show all the component selected
    BaseShape.prototype.show = function(){
        this.child.eachLayer(function(layer){
            map.addLayer(layer);
        });
    }
    //Hide all the component unselected
    BaseShape.prototype.hide = function(){
        this.child.eachLayer(function(layer){
             map.removeLayer(layer);
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
            if (k1=="Houses"){
                houses = {};
                 $.each(v1['child'], function(k2,v2){
                    v2.shape['properties'] = {};
                    v2.shape.properties['name'] = v2.housenumber;
                    houses[v2.housenumber] = v2.shape;
                 });
            }
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
        //v.setMap(null);
        map.removeLayer(v.shape);
      });

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

}

//Family factsheet link generate
function familyfactsheet_click(slum, house){
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

//household details
function household_details(housenumber){
    //sponsorinfo.setContent('<div class="overlay" style="display: block;"><div id="loading-img"></div></div>');
    let div_modal = $("#household_data");
    div_modal.find('#modelhdtext').html("House : "+housenumber);
    div_modal.find('#modelbody').html('<div class="overlay" style="display: block;"><div id="loading-img"></div></div>');
    div_modal.modal('show');
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
                    spstr += '<tr><td colspan="2"><a href="javascript:familyfactsheet_click('+global_slum_id+', '+housenumber+')" style="cursor:pointer;color:darkred;">View Factsheet</a></td></tr>';
                }
            }

            $.each(json, function(k, v) {
                if(k != 'FFReport'){
                    spstr += '<tr><td>' + k + '</td><td>' + v + '</td></tr>';
                }
            });
            spstr += '</tbody></table>';
            div_modal.find('#modelbody').html(spstr);

        },
        error : function(data){
            div_modal.modal('hide');
        }
    });
}