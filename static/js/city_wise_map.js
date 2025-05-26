    /*
 *  Library to parse and display below elements,
 *   1. Admin ward
 *   2. Electoral ward
 *   3. Slum
 *   4. Component/Filter/Sponsor
 *   5. RIM data
 */
//Admin, Electoral, Slum map variables
let length_of_components = {"Dambar road":75140, "Cement/Concrete":34648, "Interlocking":24264, "Kharanja":20767, "Kutcha road":96744, "Existing Drainage Line":383, "Location of Kutcha Open Nali (Gutter)":5266, "Location of Pucca Closed Nali (Gutter)":5581, "Location of Pucca Open Nali (Gutter)":59665, "Location of Nahar":23136, "Location of Nala":6907};
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
let globalJsonData = {};
let modelsection = {
		"General" : "General information" ,
		"Toilet" : "Status of sanitation (pre SBM)",
		"Water" : "Type of water connection",
		"Waste" : "Facility of solid waste collection",
		"Drainage" : "Drainage/open gutter information",
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
                        "Pune":new L.LatLng(18.51099762698481, 73.86055464212859),
                        "Panvel":new L.LatLng(19.051509, 73.109058),
                        "Saharanpur":new L.LatLng(29.96813172,77.54673382),
                        "Pune District":new L.LatLng(18.57054718,74.07657987),
                        "Mohanlalganj City":new L.LatLng(26.66998253,80.98541311),
                        "Nilgiri District":new L.LatLng(11.45878141, 76.64049998)};
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
    // Changing Zoom level for Pune District.
    const cityArray = ['Pune District', 'Nilgiri District']
    if (cityArray.includes($('#city_name').val())){
        map.setZoom(9);
    };
    var ggl = L.gridLayer.googleMutant({type: 'satellite' }).addTo(map);
    initMap12();
}

function getQueryParam(param) {
    const params = new URLSearchParams(window.location.search);
    return params.get(param);
}


function readJSONFile(filePath, callback, param1, param2) {
    return fetch(filePath)
        .then(response => response.json())
        .then(data => {
            callback(data, param1, param2);  // Assign the JSON response to a global variable
        })
        .catch(error => {
            console.error('Error fetching JSON data:', error);
        });
}

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
        const visible = getQueryParam('mr');
        if (visible=='1'){
            readJSONFile(`/admin/translations/?mr=${visible}`, generate_filter, slumId, result[0])
        }else{
            generate_filter(globalJsonData, slumId, result[0]);
        }
        // generate_filter(globalJsonData, slumId, result[0]);
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
                if (v[i].hasOwnProperty( "ctb_name")){
                    toilet_header += "<th> " +v[i][ "ctb_name"]+ "</th>";
                    delete v[i][ "ctb_name"]
                }else{
                    toilet_header += "<th> CTB" +(i+1) + "</th>";
                };
            }
            toilet_header+= "</tr></thead>";
            if(v.length > 0){
                // Making a array cosisting all keys which available in toilet data.
                keys_headers2 = Object.keys(v[0]);
                for (j=1; j<v.length; j++){
                    keys_headers1 = Object.keys(v[j]);
                    keys_headers2 = keys_headers2.concat(keys_headers1);
                }
                // Removing duplicates from  all keys_headers2 which available in toilet data.
                function removeDuplicates(arr) {
                    return arr.filter((item,
                        index) => arr.indexOf(item) === index);
                }
                keys_headers = removeDuplicates(keys_headers2);
                $.each(keys_headers.slice(0, keys_headers.length), function(key, val) {
                    toilet_body += '<tr><td style="font-weight:bold;width:200px;">' + val + '</td>';
                    for (i=0; i<v.length; i++){
                        value = v[i][val];
                        if(value == undefined)
                                value="None";
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
function generate_filter(globalJsonData, slumID, result){
    let compochk = $("#compochk");
    let counter = 0;
    let panel_component = "";
    $.each(result, function(k, v){
        counter = counter + 1;
        panel_component_value = Object.keys(globalJsonData).length > 0 ? globalJsonData[k] : k;
		panel_component += '<div name="div_group" class=" panel  panel-default panel-heading"> ' +
		                    '<input class="chk" name="grpchk" type="checkbox" onclick="checkAllGroup(this)"></input>&nbsp;&nbsp;<a name="chk_group" data-toggle="collapse" data-parent="#compochk" href="#' + counter + '"><b><span>' + panel_component_value + '</span></b></a>' +
		                    '</br>'

		panel_component += '<div id="' + counter + '" class="panel-collapse collapse" name="'+k+'">';
        $.each(v, function(k1, v1) {
            let chkcolor = v1['blob']['polycolor'];
            inner_panel_component_value = Object.keys(globalJsonData).length > 0 ? globalJsonData[k1] : k1;
            let child_length = null;
            if (k1 in length_of_components){
                child_length = length_of_components[k1] + " mtr";
            }else{
                child_length = v1['child'].length;
            };
            let icon = v1['icon'] ?? "Not specified";
            panel_component += '<div name="div_group" >' + '&nbsp;&nbsp;&nbsp;' +
                                 '<input name="chk1" class="chk" style="background:'+chkcolor+';background-color:' + chkcolor + '; " selection="' + k + '" component_type="' + v1['type'] + '" type="checkbox" value="' + k1 + '" onclick="checkSingleGroup(this);" >' +
                                   '<a>&nbsp;' + inner_panel_component_value + '</a>&nbsp;(' + child_length + ') <img src="' + icon + '">' +
                                 '</input>' +
                                '</div>';
            if (k1=="Structure" || k1 == 'Admin Ward Area'){
                houses = {};
                 $.each(v1['child'], function(k2,v2){
                    v2.shape['properties'] = {};
                    v2.shape.properties['name'] = v2.housenumber;
                    if (k1 == 'Admin Ward Area'){
                        v2.shape.properties['Level'] = 'Admin';
                    }
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
