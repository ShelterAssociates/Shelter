var report_table = null;
var tag  = null;
var key = null;
var tag_key_dict = {};
var delta = 30 * 1000 * 60 * 60 * 24;
var todayTime = new Date();
var aMonthAgo = todayTime.getTime() - delta ;
var aMonthAgoTime = new Date(aMonthAgo);


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
	
	tag_key_dict['startDate'] = $("#startDate").val();
	tag_key_dict['endDate'] = $("#endDate").val();

	if (report_table != null){
		report_table.ajax.reload();
	}
	else{
		report_table = $("#report_table").DataTable({
			"sDom": '<"top"Bfl>r<"mid"t><"bottom"ip><"clear">',
			"paging" : false,

			"ajax":{
				type : "POST",
				url: "/mastersheet/report_table/",
				data : function(){
					return JSON.stringify(tag_key_dict);
				} ,
				contentType : "application/json",
				dataSrc : "",
				complete: function(data){
					
				}
			},
			"columnDefs": [{"defaultContent": "-","targets": "_all"},{"footer":true},],
			"columns":[
						{"data": "level", "title": " "},
						{"data": "total_ad", "title": "Agreement Done"},
						{"data": "total_p1", "title": "Phase 1 material given"},
						{"data": "total_p2", "title": "Phase 2 material given"},
						{"data": "total_p3", "title": "Phase 3 material given"},
						{"data": "total_c", "title": "Completed"}
					]
		});
	}

}


var opts = {
       autoApply: true,            // Re-apply last filter if lazy data is loaded
       autoExpand: true,           // Expand all branches that contain matches while filtered
       counter: false,             // Show a badge with number of matching child nodes near parent icons
       fuzzy: false,               // Match single characters in order, e.g. 'fb' will match 'FooBar'
       hideExpandedCounter: true,  // Hide counter badge if parent is expanded
       hideExpanders: false,       // Hide expanders if all child nodes are hidden by filter
       highlight: true,            // Highlight matches by wrapping inside <mark> tags
       leavesOnly: false,          // Match end nodes only
       nodata: false,              // Display a 'no data' status node if result is empty
       mode: 'hide'                // Grayout unmatched nodes (pass "hide" to remove unmatched node instead)
   };

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