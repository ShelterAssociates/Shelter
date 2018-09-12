var report_table = null;
var report_table_aggregated = null;
var tag  = null;
var key = null;
var tag_key_dict = {};
var delta = 30 * 1000 * 60 * 60 * 24;
var todayTime = new Date();
var aMonthAgo = todayTime.getTime() - delta ;
var aMonthAgoTime = new Date(aMonthAgo);
var btn_default = [];
var total_counts = [{
						'aggregated_total_ad':0, 
						'aggregated_total_p1':0,
						'aggregated_total_p2':0,
						'aggregated_total_p3':0,
						'aggregated_total_c':0,
						'aggregated_use_of_toilet':0,
						'aggregated_toilet_connected_to':0,
						'aggregated_factsheet_done':0

					}];

function changeDateFormat(date){
    var yyyy = date.getFullYear();
    var mm = date.getMonth() + 1; 
    if (mm < 10) mm='0'+mm;
    var dd = date.getDate();
    if (dd < 10) dd='0'+dd;
    return(yyyy+'-'+mm+'-'+dd);
}
function showDropdown(){
    $("#drop_tree").toggle("show");	
}

function closeFunction(){
	$("#drop_tree").toggle("hide");
}
function structureData(data){
	var structured_data = [];
	var idx;
	for ( idx in data){
		var dict = data[idx];
		var newDict = {
			title : dict.name,
			key : dict.id,
			folder : dict.children != null && dict.children.length > 0,

		};
		if(dict.tag != null){
			newDict['tag'] = dict.tag
		}
		if (dict.children != null){
			newDict['children'] = [];
			newDict['children'] = structureData(dict.children);
			
		}
				structured_data.push(newDict);
	}
	return structured_data;
}

function set_root(data){
	var data_inter = structureData(data);
	content = [{
       title: 'Everything', 
       key: 0, 
       folder: true, 
       children: data_inter,
   }];
   return content;
}
function find_node(){
    $("#city_list").fancytree("getTree").filterNodes($("#filter_nodes").val(), {autoExpand: true});
}
function reset_filter(){
       $('#filter_nodes').val('');
       $("#city_list").fancytree("getTree").clearFilter();
}
function changeDatatableLevel(){
	var level = $("#radioForm input[type='radio']:checked")[0]['id'];
	var nodesToDisplay = $("#city_list").fancytree('getTree').getSelectedNodes();
	var nodesForLevel = {};
	temp = [];
	if (nodesToDisplay.length == 0){
		var all_nodes = [];
		$("#city_list").fancytree("getRootNode").visit(function(node){
        	if(node.getLevel() == 5) {
            	temp.push(node.key);
    		}
    	}); 
	}
	else{
		for(i = 0; i < nodesToDisplay.length; i++){
			if (typeof nodesToDisplay[i]['data'].tag == 'undefined'){
				temp.push(nodesToDisplay[i].key);	
			}
		}
	}
	
	nodesForLevel['tag'] = level;
	nodesForLevel['keys'] = temp;
 	tag_key_dict = nodesForLevel;
	load_report_table();

}
function load_report_table(){
	total_counts = [{
						'aggregated_total_ad':0, 
						'aggregated_total_p1':0,
						'aggregated_total_p2':0,
						'aggregated_total_p3':0,
						'aggregated_total_c':0,
						'aggregated_use_of_toilet':0,
						'aggregated_toilet_connected_to':0,
						'aggregated_factsheet_done':0

					}];
	btn_default = [
						{
                            extend: 'excel',
                            text: 'Excel',
                        }
                   ];
    if (report_table_aggregated == null){
		report_table_aggregated = $("#report_table_aggregated").DataTable({
			"dom": 't',
			"data": total_counts,
			"columnDefs": [{"defaultContent": "-","targets": "_all"},{"footer":true}],
			"columns":[
							{"data": "aggregated_total_ad", "title": "Agreement Done"},
							{"data": "aggregated_total_p1", "title": "Phase 1 material given"},
							{"data": "aggregated_total_p2", "title": "Phase 2 material given"},
							{"data": "aggregated_total_p3", "title": "Phase 3 material given"},
							{"data": "aggregated_total_c", "title": "Completed"},
							{"data": "aggregated_use_of_toilet", "title": "Use of toilet"},
							{"data": "aggregated_toilet_connected_to", "title": "Toilet connected to"},
							{"data": "aggregated_factsheet_done", "title": "Factsheet done"}
						]
		});
	}
               
	if($("#export_mastersheet").val()=="False"){
        btn_default=[];
    }       
	tag_key_dict['startDate'] = $("#startDate").val();
	tag_key_dict['endDate'] = $("#endDate").val();
	tag_key_dict['csrfmiddlewaretoken'] = $("#date_form input").val()

	if (report_table != null){
		report_table.ajax.reload();
	}
	else{
		report_table = $("#report_table").DataTable({
			"sDom": '<"top"Bfl>r<"mid"t><"bottom"ip><"clear">',
			"paging" : true,
            "order": [[ 9, "desc" ]],
			"ajax":{
				type : "POST",
				url: "/mastersheet/report_table/",
				data : function(){
					return JSON.stringify(tag_key_dict);
				} ,
				contentType : "application/json",
				dataSrc : function(data){
					for (i = 0; i < data.length; i++){
						if(typeof data[i]['total_ad'] != 'undefined'){
							total_counts[0]['aggregated_total_ad'] += data[i]['total_ad'];
						}
						if(typeof data[i]['total_p1'] != 'undefined'){	
							total_counts[0]['aggregated_total_p1'] += data[i]['total_p1'];
						}
						if(typeof data[i]['total_p2'] != 'undefined'){
							total_counts[0]['aggregated_total_p2'] += data[i]['total_p2'];
						}
						if(typeof data[i]['total_p3'] != 'undefined'){
							total_counts[0]['aggregated_total_p3'] += data[i]['total_p3'];
						}
						if(typeof data[i]['total_c'] != 'undefined'){
							total_counts[0]['aggregated_total_c'] += data[i]['total_c'];
						}
						if(typeof data[i]['use_of_toilet'] != 'undefined'){
							total_counts[0]['aggregated_use_of_toilet'] += data[i]['use_of_toilet'];
						}
						if(typeof data[i]['factsheet_done'] != 'undefined'){
							total_counts[0]['aggregated_factsheet_done'] += data[i]['factsheet_done'];
						}
						if(typeof data[i]['toilet_connected_to'] != 'undefined'){
							total_counts[0]['aggregated_toilet_connected_to'] += data[i]['toilet_connected_to'];
						}
					}
					report_table_aggregated.row(0).data(total_counts[0]);
					return data;
				},
				complete: function(data){
					$("div.dt-buttons>button").addClass("pull-left");
					
				}
			},
			"buttons":btn_default,
			"columnDefs": [{"defaultContent": "-","targets": "_all"},{"footer":true},],
			"columns":[
						{"data": "level", "title": "Name"},
						{"data": "total_ad", "title": "Agreement Done"},
						{"data": "total_p1", "title": "Phase 1 material given"},
						{"data": "total_p2", "title": "Phase 2 material given"},
						{"data": "total_p3", "title": "Phase 3 material given"},
						{"data": "total_c", "title": "Completed"},
						{"data": "use_of_toilet", "title": "Use of toilet"},
						{"data": "toilet_connected_to", "title": "Toilet connected to"},
						{"data": "factsheet_done", "title": "Factsheet done"},
						{"data": "city_name", "title": "City name"}
					]
		});
	}	
	
}

$(document).ready(function() {
	todayDate = changeDateFormat(todayTime);
	aMonthAgoDate = changeDateFormat(aMonthAgoTime);
	$("#startDate").val(aMonthAgoDate);
	$("#endDate").val( todayDate);
	$.ajax({
		url : '/mastersheet/show/report/',
		type : "GET",
        dataType : "json",
        data : "",
        contentType : "application/json",
        success : function (data) {	
        	$('#city_list').fancytree({
       		   checkbox: true,
		       source :set_root(data),
		       selectMode: 3,
		       extensions: ['filter'],
		       quicksearch: true,
		       autoScroll:true,
		       
			});
        },
        complete: function(){
        	//expanding city nodes
        	$("#city_list").fancytree("getRootNode").visit(function(node){
	        	if(node.getLevel() < 2) {
	            	node.setExpanded(true);
        		}
    		});

    		if(typeof tag_key_dict['tag'] == 'undefined'){
				var nodesToDisplay = [];
				var temp = [];
				$("#city_list").fancytree("getRootNode").visit(function(node){
		        	if(node.getLevel()==5) {
		            	temp.push(node.key);
		    		}
		    	});
				tag_key_dict['tag'] = 'city';
				tag_key_dict['keys'] = temp;
				load_report_table();
			}
        }
	});	
	
	
});