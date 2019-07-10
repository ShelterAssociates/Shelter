//Script to draw boundaries - Administrative ward, Electoral ward, and slum
//
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
        $(".overlay").show();
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
        $(".overlay").hide();
    }
    return City;
}());
//AdministrativeWard.prototype = Object.create(Polygon.prototype);
//ElectoralWard.prototype = Object.create(Polygon.prototype);
//Slum.prototype = Object.create(Polygon.prototype);