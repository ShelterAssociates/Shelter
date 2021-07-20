	var report_table = null;
	var report_table_aggregated = null;
	var report_table_cm = null;
	var report_table_cm_aggregated = null;
	var report_table_cm_activity_count = null
	var report_table_cm_activity_count_aggregated = null;
	var report_table_accounts = null;
	var tag  = null;
	var key = null;
	var tag_key_dict = {};
	var delta = 30 * 1000 * 60 * 60 * 24;
	var todayTime = new Date();
	var aMonthAgo = todayTime.getTime() - delta ;
	var aMonthAgoTime = new Date(aMonthAgo);
	var thisYear = new Date();
	var aprilOfYear = new Date(thisYear.setMonth(03,01));
	var btn_default = [];
	var total_counts = [{
							'aggregated_total_ad':0, 
							'aggregated_total_p1':0,
							'aggregated_total_p2':0,
							'aggregated_total_p3':0,
							'aggregated_total_st':0,
							'aggregated_total_c':0,
							'aggregated_use_of_toilet':0,
							'aggregated_toilet_connected_to':0,
							'aggregated_factsheet_done':0,
							'aggregated_factsheet_assign':0
						}];
	var total_counts_cm_activity_count = [{
						"aggregated_total_Awarenesssong":0,
						"aggregated_total_CornerMeeting":0, 
						"aggregated_total_FGDwithBoys":0,
						"aggregated_total_FGDwithGirls":0, 
						"aggregated_total_FGDwithMen":0, 
						"aggregated_total_FGDwithWomen":0, 
						"aggregated_total_Filmscreening":0,
						"aggregated_total_Handwash":0, 
						"aggregated_total_Other":0, 
						"aggregated_total_Samiteemeeting1":0,
						"aggregated_total_Samiteemeeting2":0,
						"aggregated_total_Samiteemeeting3":0,
						"aggregated_total_Samiteemeeting4":0,
						"aggregated_total_Samiteemeeting5":0,
						"aggregated_total_Snakeandladder":0, 
						"aggregated_total_Streetplay":0, 
						"aggregated_total_WorkshopforBoys":0, 
						"aggregated_total_WorkshopforGirls":0,
						"aggregated_total_WorkshopwithChildren":0,
						"aggregated_total_WorkshopforWomen":0, 
						"aggregated_total_WorkshopwithMen":0, 
						"aggregated_city_name":0,
	}];
	var total_counts_cm = [{

						"aggregated_total_Awarenesssong":0,
						"aggregated_total_CornerMeeting":0, 
						"aggregated_total_FGDwithBoys":0,
						"aggregated_total_FGDwithGirls":0, 
						"aggregated_total_FGDwithMen":0, 
						"aggregated_total_FGDwithWomen":0, 
						"aggregated_total_Filmscreening":0,
						"aggregated_total_Handwash":0, 
						"aggregated_total_Other":0, 
						"aggregated_total_Samiteemeeting1":0,
						"aggregated_total_Samiteemeeting2":0,
						"aggregated_total_Samiteemeeting3":0,
						"aggregated_total_Samiteemeeting4":0,
						"aggregated_total_Samiteemeeting5":0,
						"aggregated_total_Snakeandladder":0, 
						"aggregated_total_Streetplay":0, 
						"aggregated_total_WorkshopforBoys":0, 
						"aggregated_total_WorkshopforGirls":0,
						"aggregated_total_WorkshopwithChildren":0,
						"aggregated_total_WorkshopforWomen":0, 
						"aggregated_total_WorkshopwithMen":0, 
						"aggregated_city_name":0, 

	}];

    function addMonths(date, months) {
      date.setMonth(date.getMonth() + months);
      return date;
    }

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
							'aggregated_total_st':0,
							'aggregated_total_c':0,
							'aggregated_use_of_toilet':0,
							'aggregated_toilet_connected_to':0,
							'aggregated_factsheet_done':0,
							'aggregated_factsheet_assign':0
						}];

		total_counts_cm_activity_count = [{

						"aggregated_total_Awarenesssong":0,
						"aggregated_total_CornerMeeting":0, 
						"aggregated_total_FGDwithBoys":0,
						"aggregated_total_FGDwithGirls":0, 
						"aggregated_total_FGDwithMen":0, 
						"aggregated_total_FGDwithWomen":0, 
						"aggregated_total_Filmscreening":0,
						"aggregated_total_Handwash":0, 
						"aggregated_total_Other":0, 
						"aggregated_total_Samiteemeeting1":0,
						"aggregated_total_Samiteemeeting2":0,
						"aggregated_total_Samiteemeeting3":0,
						"aggregated_total_Samiteemeeting4":0,
						"aggregated_total_Samiteemeeting5":0,
						"aggregated_total_Snakeandladder":0, 
						"aggregated_total_Streetplay":0, 
						"aggregated_total_WorkshopforBoys":0, 
						"aggregated_total_WorkshopforGirls":0,
						"aggregated_total_WorkshopwithChildren":0,
						"aggregated_total_WorkshopforWomen":0, 
						"aggregated_total_WorkshopwithMen":0, 
						"aggregated_city_name":0, 

	}];
		total_counts_cm = [{

						"aggregated_total_Awarenesssong":0,
						"aggregated_total_CornerMeeting":0, 
						"aggregated_total_FGDwithBoys":0,
						"aggregated_total_FGDwithGirls":0, 
						"aggregated_total_FGDwithMen":0, 
						"aggregated_total_FGDwithWomen":0, 
						"aggregated_total_Filmscreening":0,
						"aggregated_total_Handwash":0, 
						"aggregated_total_Other":0, 
						"aggregated_total_Samiteemeeting1":0,
						"aggregated_total_Samiteemeeting2":0,
						"aggregated_total_Samiteemeeting3":0,
						"aggregated_total_Samiteemeeting4":0,
						"aggregated_total_Samiteemeeting5":0,
						"aggregated_total_Snakeandladder":0, 
						"aggregated_total_Streetplay":0, 
						"aggregated_total_WorkshopforBoys":0, 
						"aggregated_total_WorkshopforGirls":0,
						"aggregated_total_WorkshopwithChildren":0,
						"aggregated_total_WorkshopforWomen":0, 
						"aggregated_total_WorkshopwithMen":0, 
						"aggregated_city_name":0, 

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
								{"data": "", "title": "Name"},
								{"data": "aggregated_total_ad", "title": "Agreement Done"},
								{"data": "aggregated_total_p1", "title": "Phase 1 material given"},
								{"data": "aggregated_total_p2", "title": "Phase 2 material given"},
								{"data": "aggregated_total_p3", "title": "Phase 3 material given"},
								{"data": "aggregated_total_st", "title": "Septic tank given"},
								{"data": "aggregated_total_c", "title": "Completed"},
								{"data": "aggregated_use_of_toilet", "title": "Use of toilet"},
								{"data": "aggregated_toilet_connected_to", "title": "Toilet connected to"},
								{"data": "aggregated_factsheet_done", "title": "Factsheet done"},
								{"data": "aggregated_factsheet_assign", "title": "Factsheet Assign"}
							]
			});
		}
	               
		if($("#export_mastersheet").val()=="False"){
	        btn_default=[];
	    }       
		tag_key_dict['startDate'] = $("#startDate").val();
		tag_key_dict['endDate'] = $("#endDate").val();
		tag_key_dict['csrfmiddlewaretoken'] = $("#date_form input").val();
		if (report_table_accounts != null){
			report_table_accounts.ajax.reload();
		}
		else{
			report_table_accounts = $("#report_table_accounts").DataTable({
				"sDom": '<"top"Bfl>r<"mid"t><"bottom"ip><"clear">',
				"paging" : true,
				"ajax":{
					type : "POST",
					url: "/mastersheet/report_table_accounts/",
					data : function(){
						return JSON.stringify(tag_key_dict);
					} ,
					contentType : "application/json",
					dataSrc:'',
				},
				"buttons":btn_default,
				"columnDefs": [{"defaultContent": "-","targets": "_all"},{"footer":true},],
				"columns":[
							{"data": "level", "title": "Name"},
							{"data": "total_p1", "title": "Phase 1 material given"},
							{"data": "total_p1_accounts", "title": "Phase 1 - Accounts"},
							{"data": "total_p2", "title": "Phase 2 material given"},
							{"data": "total_p2_accounts", "title": "Phase 2 - Accounts"},
							{"data": "total_p3", "title": "Phase 3 material given"},
							{"data": "total_p3_accounts", "title": "Phase 3 - Accounts"},
							{"data": "city_name", "title": "City name"}
							
						]
			});
		}
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
							if(typeof data[i]['total_st'] != 'undefined'){
								total_counts[0]['aggregated_total_st'] += data[i]['total_st'];
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
							if(typeof data[i]['factAssign'] != 'undefined'){
								total_counts[0]['aggregated_factsheet_assign'] += data[i]['factAssign'];
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
							{"data": "total_ad", "title": "Agreement Done Date"},
							{"data": "total_p1", "title": "Phase 1 material given"},
							{"data": "total_p2", "title": "Phase 2 material given"},
							{"data": "total_p3", "title": "Phase 3 material given"},
							{"data": "total_st", "title": "Septic tanks given"},
							{"data": "total_c", "title": "Completed"},
							{"data": "use_of_toilet", "title": "Use of toilet"},
							{"data": "toilet_connected_to", "title": "Toilet connected to"},
							{"data": "factsheet_done", "title": "Factsheet done"},
							{"data": "factAssign", "title": "Factsheet Assign"},
							{"data": "city_name", "title": "City name"}
						]
			});
		}	

		if (report_table_cm_aggregated == null){
			report_table_cm_aggregated = $("#report_table_cm_aggregated").DataTable({
				"dom": 't',
				"data": total_counts_cm,
				"columnDefs": [{"defaultContent": "-","targets": "_all"},{"footer":true}],
				"columns":[

							{"data": "", "title": "Name"},	
							{"data": "aggregated_total_Awarenesssong", "title": "Awareness song"},
							{"data": "aggregated_total_CornerMeeting", "title": "Corner Meeting"},
							{"data": "aggregated_total_FGDwithBoys", "title": "FGD with Boys"},
							{"data": "aggregated_total_FGDwithGirls", "title": "FGD with Girls"},
							{"data": "aggregated_total_FGDwithMen", "title": "FGD with Men"},
							{"data": "aggregated_total_FGDwithWomen", "title": "FGD with Women"},
							{"data": "aggregated_total_Filmscreening", "title": "Film screening"},
							{"data": "aggregated_total_Handwash", "title": "Hand wash"},
							{"data": "aggregated_total_Other", "title": "Other"},
							{"data": "aggregated_total_Samiteemeeting1", "title": "Samitee meeting 1"},
							{"data": "aggregated_total_Samiteemeeting2", "title": "Samitee meeting 2"},
							{"data": "aggregated_total_Samiteemeeting3", "title": "Samitee meeting 3"},
							{"data": "aggregated_total_Samiteemeeting4", "title": "Samitee meeting 4"},
							{"data": "aggregated_total_Samiteemeeting5", "title": "Samitee meeting 5"},
							{"data": "aggregated_total_Snakeandladder", "title": "Snake and ladder"},
							{"data": "aggregated_total_Streetplay", "title": "Street play"},
							{"data": "aggregated_total_WorkshopforBoys", "title": "Workshop for Boys"},
							{"data": "aggregated_total_WorkshopforGirls", "title": "Workshop for Girls"},
							{"data": "aggregated_total_WorkshopwithChildren", "title": "Workshop with Children"},
							{"data": "aggregated_total_WorkshopforWomen", "title": "Workshop for Women"},
							{"data": "aggregated_total_WorkshopwithMen", "title": "Workshop with Men"},
						],
					"scrollX": true
			});
		}
		if (report_table_cm_activity_count_aggregated == null){
			report_table_cm_activity_count_aggregated = $("#report_table_cm_activity_count_aggregated").DataTable({
				"dom": 't',
				"data": total_counts_cm_activity_count,
				"columnDefs": [{"defaultContent": "-","targets": "_all"},{"footer":true}],
				"columns":[
							{"data": "", "title": "Name"},	
							{"data": "aggregated_total_Awarenesssong", "title": "Awareness song"},
							{"data": "aggregated_total_CornerMeeting", "title": "Corner Meeting"},
							{"data": "aggregated_total_FGDwithBoys", "title": "FGD with Boys"},
							{"data": "aggregated_total_FGDwithGirls", "title": "FGD with Girls"},
							{"data": "aggregated_total_FGDwithMen", "title": "FGD with Men"},
							{"data": "aggregated_total_FGDwithWomen", "title": "FGD with Women"},
							{"data": "aggregated_total_Filmscreening", "title": "Film screening"},
							{"data": "aggregated_total_Handwash", "title": "Hand wash"},
							{"data": "aggregated_total_Other", "title": "Other"},
							{"data": "aggregated_total_Samiteemeeting1", "title": "Samitee meeting 1"},
							{"data": "aggregated_total_Samiteemeeting2", "title": "Samitee meeting 2"},
							{"data": "aggregated_total_Samiteemeeting3", "title": "Samitee meeting 3"},
							{"data": "aggregated_total_Samiteemeeting4", "title": "Samitee meeting 4"},
							{"data": "aggregated_total_Samiteemeeting5", "title": "Samitee meeting 5"},
							{"data": "aggregated_total_Snakeandladder", "title": "Snake and ladder"},
							{"data": "aggregated_total_Streetplay", "title": "Street play"},
							{"data": "aggregated_total_WorkshopforBoys", "title": "Workshop for Boys"},
							{"data": "aggregated_total_WorkshopforGirls", "title": "Workshop for Girls"},
							{"data": "aggregated_total_WorkshopwithChildren", "title": "Workshop with Children"},
							{"data": "aggregated_total_WorkshopforWomen", "title": "Workshop for Women"},
							{"data": "aggregated_total_WorkshopwithMen", "title": "Workshop with Men"},
						],
					"scrollX": true
			});
		}

		if (report_table_cm_activity_count != null){
			report_table_cm_activity_count.ajax.reload();
		}
		else{
			report_table_cm_activity_count = $("#report_table_cm_activity_count").DataTable({
				"sDom": '<"top"Bfl>r<"mid"t><"bottom"ip><"clear">',
				"paging" : true,
				"ajax":{
					type : "POST",
					url: "/mastersheet/report_table_cm_activity_count/",
					data : function(){
						return JSON.stringify(tag_key_dict);
					} ,
					dataSrc:function(data){

						for(i=0; i<data.length; i++){
							if(data[i].hasOwnProperty('total_FGDwithBoys')){
							}

							if(data[i].hasOwnProperty('total_Awarenesssong') ){
								total_counts_cm_activity_count[0]['aggregated_total_Awarenesssong'] += data[i]['total_Awarenesssong'];
							}
							if(data[i].hasOwnProperty('total_CornerMeeting')){
								total_counts_cm_activity_count[0]['aggregated_total_CornerMeeting'] += data[i]['total_CornerMeeting'];
							}
							if(data[i].hasOwnProperty('total_FGDwithBoys')){

								total_counts_cm_activity_count[0]['aggregated_total_FGDwithBoys'] += data[i]['total_FGDwithBoys'];
							}
							if(data[i].hasOwnProperty('total_FGDwithGirls')){
								total_counts_cm_activity_count[0]['aggregated_total_FGDwithGirls'] += data[i]['total_FGDwithGirls'];
							}
							if(data[i].hasOwnProperty('total_FGDwithMen')){
								total_counts_cm_activity_count[0]['aggregated_total_FGDwithMen'] += data[i]['total_FGDwithMen'];
							}
							if(data[i].hasOwnProperty('total_FGDwithWomen')){
								total_counts_cm_activity_count[0]['aggregated_total_FGDwithWomen'] += data[i]['total_FGDwithWomen'];
							}
							if(data[i].hasOwnProperty('total_Filmscreening')){
								total_counts_cm_activity_count[0]['aggregated_total_Filmscreening'] += data[i]['total_Filmscreening'];
							}
							if(data[i].hasOwnProperty('total_Handwash')){
								total_counts_cm_activity_count[0]['aggregated_total_Handwash'] += data[i]['total_Handwash'];
							}
							if(data[i].hasOwnProperty('total_Other')){
								total_counts_cm_activity_count[0]['aggregated_total_Other'] += data[i]['total_Other'];
							}
							if(data[i].hasOwnProperty('total_Samiteemeeting1')){
								total_counts_cm_activity_count[0]['aggregated_total_Samiteemeeting1'] += data[i]['total_Samiteemeeting1'];
							}
							if(data[i].hasOwnProperty('total_Samiteemeeting2')){
								total_counts_cm_activity_count[0]['aggregated_total_Samiteemeeting2'] += data[i]['total_Samiteemeeting2'];
							}
							if(data[i].hasOwnProperty('total_Samiteemeeting3')){
								total_counts_cm_activity_count[0]['aggregated_total_Samiteemeeting3'] += data[i]['total_Samiteemeeting3'];
							}
							if(data[i].hasOwnProperty('total_Samiteemeeting4')){
								total_counts_cm_activity_count[0]['aggregated_total_Samiteemeeting4'] += data[i]['total_Samiteemeeting4'];
							}
							if(data[i].hasOwnProperty('total_Samiteemeeting5')){
								total_counts_cm_activity_count[0]['aggregated_total_Samiteemeeting5'] += data[i]['total_Samiteemeeting5'];
							}
							if(data[i].hasOwnProperty('total_Snakeandladder')){
								total_counts_cm_activity_count[0]['aggregated_total_Snakeandladder'] += data[i]['total_Snakeandladder'];
							}
							if(data[i].hasOwnProperty('total_Streetplay')){
								total_counts_cm_activity_count[0]['aggregated_total_Streetplay'] += data[i]['total_Streetplay'];
							}
							if(data[i].hasOwnProperty('total_WorkshopforBoys')){
								total_counts_cm_activity_count[0]['aggregated_total_WorkshopforBoys'] += data[i]['total_WorkshopforBoys'];
							}
							if(data[i].hasOwnProperty('total_WorkshopforGirls')){
								total_counts_cm_activity_count[0]['aggregated_total_WorkshopforGirls'] += data[i]['total_WorkshopforGirls'];
							}
							if(data[i].hasOwnProperty('total_WorkshopwithChildren')){
								total_counts_cm_activity_count[0]['aggregated_total_WorkshopwithChildren'] += data[i]['total_WorkshopwithChildren'];
							}
							if(data[i].hasOwnProperty('total_WorkshopforWomen')){
								total_counts_cm_activity_count[0]['aggregated_total_WorkshopforWomen'] += data[i]['total_WorkshopforWomen'];
							}
							if(data[i].hasOwnProperty('total_WorkshopwithMen')){
								total_counts_cm_activity_count[0]['aggregated_total_WorkshopwithMen'] += data[i]['total_WorkshopwithMen'];
							}
							
						}
						report_table_cm_activity_count_aggregated.row(0).data(total_counts_cm_activity_count[0]);
						return data;
					},
					contentType : "application/json",
					
				},
				 "buttons":btn_default,
				 "columnDefs": [{"defaultContent": "-","targets": "_all"},{"footer":true},],
				"columns":[
						{"data": "level", "title": "Name"},
						{"data": "total_Awarenesssong", "title": "Awareness song"},
						{"data": "total_CornerMeeting", "title": "Corner Meeting"},
						{"data": "total_FGDwithBoys", "title": "FGD with Boys"},
						{"data": "total_FGDwithGirls", "title": "FGD with Girls"},
						{"data": "total_FGDwithMen", "title": "FGD with Men"},
						{"data": "total_FGDwithWomen", "title": "FGD with Women"},
						{"data": "total_Filmscreening", "title": "Film screening"},
						{"data": "total_Handwash", "title": "Hand wash"},
						{"data": "total_Other", "title": "Other"},
						{"data": "total_Samiteemeeting1", "title": "Samitee meeting 1"},
						{"data": "total_Samiteemeeting2", "title": "Samitee meeting 2"},
						{"data": "total_Samiteemeeting3", "title": "Samitee meeting 3"},
						{"data": "total_Samiteemeeting4", "title": "Samitee meeting 4"},
						{"data": "total_Samiteemeeting5", "title": "Samitee meeting 5"},
						{"data": "total_Snakeandladder", "title": "Snake and ladder"},
						{"data": "total_Streetplay", "title": "Street play"},
						{"data": "total_WorkshopforBoys", "title": "Workshop for Boys"},
						{"data": "total_WorkshopforGirls", "title": "Workshop for Girls"},
						{"data": "total_WorkshopwithChildren", "title": "Workshop with Children"},
						{"data": "total_WorkshopforWomen", "title": "Workshop for Women"},
						{"data": "total_WorkshopwithMen", "title": "Workshop with Men"},
						{"data": "city_name", "title": "City name"}
						
					],
					"scrollX": true
			});
		}
		if(report_table_cm != null){
			report_table_cm.ajax.reload();
		}
		else{
			try{
			report_table_cm = $("#report_table_cm").DataTable({
				"sDom": '<"top"Bfl>r<"mid"t><"bottom"ip><"clear">',
				"paging" : true,
				"ajax":{
					type : "POST",
					url: "/mastersheet/report_table_cm/",
					data : function(){
						return JSON.stringify(tag_key_dict);
					} ,
					dataSrc:function(data){

						for(i=0; i<data.length; i++){
							if(data[i].hasOwnProperty('total_FGDwithBoys')){
							}

							if(data[i].hasOwnProperty('total_Awarenesssong') ){
								total_counts_cm[0]['aggregated_total_Awarenesssong'] += data[i]['total_Awarenesssong'];
							}
							if(data[i].hasOwnProperty('total_CornerMeeting')){
								total_counts_cm[0]['aggregated_total_CornerMeeting'] += data[i]['total_CornerMeeting'];
							}
							if(data[i].hasOwnProperty('total_FGDwithBoys')){

								total_counts_cm[0]['aggregated_total_FGDwithBoys'] += data[i]['total_FGDwithBoys'];
							}
							if(data[i].hasOwnProperty('total_FGDwithGirls')){
								total_counts_cm[0]['aggregated_total_FGDwithGirls'] += data[i]['total_FGDwithGirls'];
							}
							if(data[i].hasOwnProperty('total_FGDwithMen')){
								total_counts_cm[0]['aggregated_total_FGDwithMen'] += data[i]['total_FGDwithMen'];
							}
							if(data[i].hasOwnProperty('total_FGDwithWomen')){
								total_counts_cm[0]['aggregated_total_FGDwithWomen'] += data[i]['total_FGDwithWomen'];
							}
							if(data[i].hasOwnProperty('total_Filmscreening')){
								total_counts_cm[0]['aggregated_total_Filmscreening'] += data[i]['total_Filmscreening'];
							}
							if(data[i].hasOwnProperty('total_Handwash')){
								total_counts_cm[0]['aggregated_total_Handwash'] += data[i]['total_Handwash'];
							}
							if(data[i].hasOwnProperty('total_Other')){
								total_counts_cm[0]['aggregated_total_Other'] += data[i]['total_Other'];
							}
							if(data[i].hasOwnProperty('total_Samiteemeeting1')){
								total_counts_cm[0]['aggregated_total_Samiteemeeting1'] += data[i]['total_Samiteemeeting1'];
							}
							if(data[i].hasOwnProperty('total_Samiteemeeting2')){
								total_counts_cm[0]['aggregated_total_Samiteemeeting2'] += data[i]['total_Samiteemeeting2'];
							}
							if(data[i].hasOwnProperty('total_Samiteemeeting3')){
								total_counts_cm[0]['aggregated_total_Samiteemeeting3'] += data[i]['total_Samiteemeeting3'];
							}
							if(data[i].hasOwnProperty('total_Samiteemeeting4')){
								total_counts_cm[0]['aggregated_total_Samiteemeeting4'] += data[i]['total_Samiteemeeting4'];
							}
							if(data[i].hasOwnProperty('total_Samiteemeeting5')){
								total_counts_cm[0]['aggregated_total_Samiteemeeting5'] += data[i]['total_Samiteemeeting5'];
							}
							if(data[i].hasOwnProperty('total_Snakeandladder')){
								total_counts_cm[0]['aggregated_total_Snakeandladder'] += data[i]['total_Snakeandladder'];
							}
							if(data[i].hasOwnProperty('total_Streetplay')){
								total_counts_cm[0]['aggregated_total_Streetplay'] += data[i]['total_Streetplay'];
							}
							if(data[i].hasOwnProperty('total_WorkshopforBoys')){
								total_counts_cm[0]['aggregated_total_WorkshopforBoys'] += data[i]['total_WorkshopforBoys'];
							}
							if(data[i].hasOwnProperty('total_WorkshopforGirls')){
								total_counts_cm[0]['aggregated_total_WorkshopforGirls'] += data[i]['total_WorkshopforGirls'];
							}
							if(data[i].hasOwnProperty('total_WorkshopwithChildren')){
								total_counts_cm[0]['aggregated_total_WorkshopwithChildren'] += data[i]['total_WorkshopwithChildren'];
							}
							if(data[i].hasOwnProperty('total_WorkshopforWomen')){
								total_counts_cm[0]['aggregated_total_WorkshopforWomen'] += data[i]['total_WorkshopforWomen'];
							}
							if(data[i].hasOwnProperty('total_WorkshopwithMen')){
								total_counts_cm[0]['aggregated_total_WorkshopwithMen'] += data[i]['total_WorkshopwithMen'];
							}
							
						}
						report_table_cm_aggregated.row(0).data(total_counts_cm[0]);
						return data;
					},
					contentType : "application/json",
					
				},
				 "buttons":btn_default,
				 "columnDefs": [{"defaultContent": "-","targets": "_all"},{"footer":true},],
				"columns":[
						{"data": "level", "title": "Name"},
						{"data": "total_Awarenesssong", "title": "Awareness song"},
						{"data": "total_CornerMeeting", "title": "Corner Meeting"},
						{"data": "total_FGDwithBoys", "title": "FGD with Boys"},
						{"data": "total_FGDwithGirls", "title": "FGD with Girls"},
						{"data": "total_FGDwithMen", "title": "FGD with Men"},
						{"data": "total_FGDwithWomen", "title": "FGD with Women"},
						{"data": "total_Filmscreening", "title": "Film screening"},
						{"data": "total_Handwash", "title": "Hand wash"},
						{"data": "total_Other", "title": "Other"},
						{"data": "total_Samiteemeeting1", "title": "Samitee meeting 1"},
						{"data": "total_Samiteemeeting2", "title": "Samitee meeting 2"},
						{"data": "total_Samiteemeeting3", "title": "Samitee meeting 3"},
						{"data": "total_Samiteemeeting4", "title": "Samitee meeting 4"},
						{"data": "total_Samiteemeeting5", "title": "Samitee meeting 5"},
						{"data": "total_Snakeandladder", "title": "Snake and ladder"},
						{"data": "total_Streetplay", "title": "Street play"},
						{"data": "total_WorkshopforBoys", "title": "Workshop for Boys"},
						{"data": "total_WorkshopforGirls", "title": "Workshop for Girls"},
						{"data": "total_WorkshopwithChildren", "title": "Workshop with Children"},
						{"data": "total_WorkshopforWomen", "title": "Workshop for Women"},
						{"data": "total_WorkshopwithMen", "title": "Workshop with Men"},
						{"data": "city_name", "title": "City name"}
						
					],
					"scrollX": true

			});
		}catch(e){console.log(e);}
		}
		
	}

	$(document).ready(function() {
		todayDate = changeDateFormat(todayTime);
//		aMonthAgoDate = changeDateFormat(aMonthAgoTime);
        n = new Date(thisYear.setMonth(03,01));
        n.setFullYear(n.getFullYear() - 1)
		aprilofthisyear = changeDateFormat(n);
		$("#startDate").val(aprilofthisyear);
		$("#endDate").val(todayDate);
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