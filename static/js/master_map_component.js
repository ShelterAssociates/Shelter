//////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////
//                  Slum Component code
//////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////
var __extends = (this && this.__extends) || function (d, b) {
    for (var p in b) if (b.hasOwnProperty(p)) d[p] = b[p];
    function __() { this.constructor = d; }
    d.prototype = b === null ? Object.create(b) : (__.prototype = b.prototype, new __());
};

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
        error : function(response){
            div_modal.modal('hide');
            if (response.responseText!=""){
                    alert(response.responseText);
                }
        }
    });
}

//Click on each layer display values
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
        this.fillflag = obj_component.blob.fillflag;
        if(this.fillflag == undefined){
		this.fillflag= true;
	}
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
		try{
                par_child = this.parse_filter(child);
		}catch(err){}
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
                color : this.chklinecolor,
                opacity : 0.7,
                weight : this.chklinewidth
                }
               };

           if (shape_geo.type == "Point"){
                let chklinecolor = this.chklinecolor;
                myCustomColour = chklinecolor;

                let pinImage =  L.divIcon({ html: '<span style="background-color: '+chklinecolor+'"></span>',
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
		if (!this.fillflag){
                    style_geometry['style']['fillOpacity'] = 0
		    //delete style_geometry['style']['fillColor'];
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
