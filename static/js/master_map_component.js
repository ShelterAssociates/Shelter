var __extends = (this && this.__extends) || function (d, b) {
    for (var p in b) if (b.hasOwnProperty(p)) d[p] = b[p];
    function __() { this.constructor = d; }
    d.prototype = b === null ? Object.create(b) : (__.prototype = b.prototype, new __());
};

function familyfactsheet_click(slum, house) {
    $(".overlay").show();
    $.ajax({
        url: '/admin/familyrportgenerate/',
        data: { Sid: slum, HouseNo: house },
        type: "POST",
        contenttype: "json",
        success: function (json) {
            $(".overlay").hide();
            if (json['string'] != undefined) {
                url = json.string;
                window.open("" + url);
            } else {
                alert(json['error']);
            }
        },
        error: function () {
            $(".overlay").hide();
        }
    });
}

function household_details(housenumber) {
    let div_modal = $("#household_data");
    div_modal.find('#modelhdtext').html("House : " + housenumber);
    div_modal.find('#modelbody').html('<div class="overlay" style="display: block;"><div id="loading-img"></div></div>');
    div_modal.modal('show');
    $.ajax({
        url: '/component/get_kobo_RHS_list/' + global_slum_id + '/' + housenumber,
        type: "GET",
        contenttype: "json",
        success: function (json) {
            var spstr = "";
            spstr += '<table class="table table-striped" style="font-size: 10px;"><tbody>';
            if (json['FFReport']) {
                flag = false;
                let fields = $("a[name=chk_group]:contains('Sponsor')").parent().find('input[type=checkbox]');
                fields.slice(0, fields.length - 1).each(function (ind, chk) {
                    if ($(chk).is(":checked")) {
                        flag = true;
                    }
                });
                if (flag) {
                    spstr += '<tr><td colspan="2"><a href="javascript:familyfactsheet_click(' + global_slum_id + ', ' + housenumber + ')" style="cursor:pointer;color:darkred;">View Factsheet</a></td></tr>';
                }
            }
            $.each(json, function (k, v) {
                if (k != 'FFReport') {
                    spstr += '<tr><td>' + k + '</td><td>' + v + '</td></tr>';
                }
            });
            spstr += '</tbody></table>';
            div_modal.find('#modelbody').html(spstr);
        },
        error: function (response) {
            div_modal.modal('hide');
            if (response.responseText != "") {
                alert(response.responseText);
            }
        }
    });
}

function onEachFeature(feature, layer) {
    if ('properties' in feature && 'name' in feature.properties) {
        var name = feature.properties.name;
        if ('Level' in feature.properties) {
            layer.bindPopup("Admin Ward:" + name);
        } else {
            layer.bindPopup("House:" + name);
        }
        layer.on('mouseover', function (e) { this.openPopup(); });
        layer.on('mouseout', function (e) { this.closePopup(); });
        layer.on('click', function (e) {
            if ('Level' in feature.properties) {
                if (typeof _wbSelectWard === 'function') {
                    _wbSelectWard(name);
                }
            } else {
                household_details(name);
            }
        });
    }
}

var BaseShape = (function () {
    function BaseShape(obj_component) {
        this.icon = obj_component.icon;
        this.name = obj_component.name;
        this.chkcolor = obj_component.blob.polycolor || "#FFA3A3";
        this.chklinecolor = obj_component.blob.linecolor || "#ff0000";
        this.chklinewidth = obj_component.blob.linewidth || "1";
        this.fillflag = obj_component.blob.fillflag;
        if (this.fillflag == undefined) {
            this.fillflag = true;
        }
        this.type = obj_component.type;
        this.count = obj_component.count;
        this.child = obj_component.child;
        this.icon = obj_component.icon;
    }

    /* Stores the raw feature array; the Leaflet group is built on first use.
       Building every component up front cost ~25k L.geoJson features per slum
       while only the checked ones are ever drawn. */
    Object.defineProperty(BaseShape.prototype, "child", {
        get: function () { return this._materialize(); },
        set: function (child) {
            this._rawChild = child;
            this._child = null;
            this._built = false;
        },
        enumerable: true,
        configurable: true
    });

    /* Memoises failures too, so an unparseable component is not retried on
       every click. */
    BaseShape.prototype._materialize = function () {
        if (this._built) { return this._child; }
        this._built = true;

        if (this.type != 'C') {
            try { this._child = this.parse_filter(this._rawChild); } catch (err) { this._child = null; }
        } else {
            this._child = this.parse_component(this._rawChild);
        }
        return this._child;
    };

    BaseShape.prototype.style_geo_geometry = function (shape_geo) {
        // FIX 1: 'let' makes this local — no longer a global that gets overwritten
        let style_geometry = {
            style: {
                color: this.chklinecolor,
                opacity: 0.7,
                weight: this.chklinewidth
            }
        };

        if (shape_geo.type == "Point") {
            // FIX 2: 'let' keeps these local to each call
            let chklinecolor = this.chklinecolor;
            let myCustomColour = chklinecolor;

            let pinImage = L.divIcon({
                html: '<span style="background-color: ' + chklinecolor + '"></span>',
                iconSize: [20, 20],
                className: 'myDivIcon'
            });
            if (this.icon != undefined && this.icon != "") {
                // FIX 3: 'let' keeps icon_image local
                let icon_image = this.icon;
                pinImage = new L.Icon({ iconUrl: icon_image });
            }
            style_geometry = {
                icon: pinImage,
                pointToLayer: function (feature, latlng) {
                    return L.marker(latlng, { icon: pinImage });
                }
            };
        } else if (shape_geo.type == "Polygon") {
            style_geometry['style'] = {
                color: this.chklinecolor,
                opacity: 0.7,
                weight: this.chklinewidth,
                fillColor: this.chkcolor,
                fillOpacity: 0.6,
            };
            if (!this.fillflag) {
                style_geometry['style']['fillOpacity'] = 0;
            }
        }

        style_geometry['onEachFeature'] = onEachFeature;
        return style_geometry;
    };

    /* Always builds the full slum-wide group. Ward scoping is owned by
       _showComponentForActiveWard(), which keeps its own separate layer; a
       ward-filtered group memoised here would be restored later as if it were
       the full one. */
    BaseShape.prototype.parse_component = function (child) {
        // FIX 4: 'let' keeps list_draw local
        let list_draw = [];
        let i;
        let v;

        if (!child || !child.length) { return L.geoJson([]); }

        for (i = 0; i < child.length; i++) {
            v = child[i];
            if (v && v.shape) {
                list_draw.push(v.shape);
            }
        }

        return L.geoJson(list_draw, this.style_geo_geometry(child[0].shape));
    };

    /* Resolves household numbers against the global `houses` lookup. Unscoped,
       for the same reason as parse_component. */
    BaseShape.prototype.parse_filter = function (child) {
        let filter_houses = [];
        let i;
        let houseKey;
        let houseKeyInt;

        for (i = 0; i < (child || []).length; i++) {
            houseKey = String(child[i]).split(".")[0].trim();
            houseKeyInt = parseInt(houseKey, 10);
            if (houses[houseKey]) {
                filter_houses.push(houses[houseKey]);
            } else if (houses[String(houseKey)]) {
                filter_houses.push(houses[String(houseKey)]);
            } else if (!isNaN(houseKeyInt) && houses[houseKeyInt]) {
                filter_houses.push(houses[houseKeyInt]);
            }
        }

        return L.geoJson(filter_houses, this.style_geo_geometry(filter_houses[0]));
    };

    BaseShape.prototype.show = function () {
        var group = this._materialize();
        if (!group) { return; }
        group.eachLayer(function (layer) { map.addLayer(layer); });
    };

    /* Reads _child directly, not the getter: hiding a component that was never
       shown must not trigger a build. */
    BaseShape.prototype.hide = function () {
        if (!this._built || !this._child) { return; }
        this._child.eachLayer(function (layer) { map.removeLayer(layer); });
    };

    return BaseShape;
}());

var Component = (function (_super) {
    __extends(Component, _super);
    function Component(obj_component) { _super.call(this, obj_component) || this; }
    return Component;
}(BaseShape));

var Filter = (function (_super) {
    __extends(Filter, _super);
    function Filter(obj_filter) { _super.call(this, obj_filter) || this; }
    return Filter;
}(BaseShape));

var Sponsor = (function (_super) {
    __extends(Sponsor, _super);
    function Sponsor(obj_sponsor) { _super.call(this, obj_sponsor) || this; }
    return Sponsor;
}(BaseShape));

// Ward assignment for map features is computed server-side (see
// `_get_ward_component_counts` in component/services/helper.py) and
// consumed via `_wb.componentWards` in ward_breakdown.js — no client-side
// point-in-polygon/centroid computation needed here.