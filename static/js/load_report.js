var report_table = null;
var tag  = null;
var key = null;

function showDropdown(){
    $(".dropdown1").toggle("show");	
}
function applyFunction(){
	if ($("#applyButton").find("#current_item")){
		
		$("#applyButton").find("#current_item").html("");
	    $("#applyButton ").find("#current_item").remove();
	}
	var current_item = document.createElement('div');
    current_item.classList.add("display_line");
    current_item.setAttribute("id" , "current_item");
	if($("#city_list").fancytree('getTree').getActiveNode()!= null){
		tag = $("#city_list").fancytree('getTree').getActiveNode()['data'].tag;
		key = $("#city_list").fancytree('getTree').getActiveNode()['key'];
		current_item.innerHTML = "<p>Currently displaying : "+$("#city_list").fancytree('getTree').getActiveNode()['title']+"</p>"; 
	}
    else{
    	current_item.innerHTML = "<p>Currently displaying : All the records within the given date range</p>"; 
    }
   
    $("#applyButton").append(current_item);
	load_report_table();
}
function closeFunction(){
	$(".dropdown1").toggle("hide");
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
function load_report_table(){
	if (report_table != null){
		
		report_table.ajax.reload();
	}
	else{
		report_table = $("#report_table").DataTable({
			"sDom": '<"top"Bfl>r<"mid"t><"bottom"ip><"clear">',
			"paging" : false,
			"ajax":{
				url: "/mastersheet/report_table/",
				dataSrc:"",
				data : function(){return {'tag'  : tag, 'id' : key, 'startDate':$("#startDate").val(), 'endDate':$("#endDate").val()} },
				contentType : "application/json",
				complete: function(data){
					//console.log(data);
				}
			},
			"columnDefs": [{"defaultContent": "-","targets": "_all"},{"footer":true},],
			"columns":[
						{"data": "counter_ad", "title": "Agreement Done"},
						{"data": "counter_p1", "title": "Phase 1 material given"},
						{"data": "counter_p2", "title": "Phase 2 material given"},
						{"data": "counter_p3", "title": "Phase 3 material given"},
						{"data": "counter_c", "title": "Completed"}
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
	
	load_report_table();
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
		       //filter: opts,
		       
			});
        }
	});	
	
	
});