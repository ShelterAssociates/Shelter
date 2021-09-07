	var report_table_covid = null;
	var tag  = null;
	var key = null;
	var change = 0;
	var tag_key_dict = {};
	var delta = 30 * 1000 * 60 * 60 * 24;
	var todayTime = new Date();
	var aMonthAgo = todayTime.getTime() - delta ;
	var aMonthAgoTime = new Date(aMonthAgo);
	var thisYear = new Date();
	var aprilOfYear = new Date(thisYear.setMonth(03,01));
	var btn_default = [];


	function changeDateAfter(date){
		var y = date.getFullYear();
		var m_c = date.getMonth();
		var m = '04'
		var d = '01'
		if (parseInt(m) > m_c){
			var y1 = y - 1;
			return (y1+'-'+m+'-'+d);
		} else{
			return (y+'-'+m+'-'+d);
		}

	}


	function StartDate(date){
		var yyyy = date.getFullYear();
		var mm_c = date.getMonth();
		var mm = '04';
		var dd = '01';
		if (parseInt(mm) > mm_c){
			var yyyy1 = yyyy - 1;
			return (yyyy1+'-'+mm+'-'+dd);
		} else if (parseInt(mm) == mm_c) {
			return (yyyy+'-'+mm+'-'+dd);
		} else { 
			return (yyyy+'-'+mm+'-'+dd);
		}
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
		load_report_covid();

	}

	function load_report_covid(){

		btn_default = [
			{
				extend: 'excel',
				text: 'Excel',
			}
	   ];
		if($("#export_mastersheet").val()=="False"){

		}
		tag_key_dict['startDate'] = $("#startDate").val();
		tag_key_dict['endDate'] = $("#endDate").val();
		tag_key_dict['csrfmiddlewaretoken'] = $("#date_form input").val();

		if (report_table_covid != null){
					report_table_covid.ajax.reload();
		}
		else{
		report_table_covid = $("#report_table_covid").DataTable({
			"sDom": '<"top"Bfl>r<"mid"t><"bottom"ip><"clear">',
			"paging" : true,
			"order": [[ 9, "desc" ]],
			"ajax":{
				type : "POST",
				url: "/graphs/covid_report/",
				data : function(){
					return JSON.stringify(tag_key_dict);
				} ,
				contentType : "application/json",
				dataSrc : function(data){
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
						{"data": "total_hh", "title": "Total Households"},
						{"data": "total_oc_hh", "title": "Occupied Households as per AVNI Survey"},
						{"data": "total_sw_hh", "title": "Surveyed household"},
						{"data": "pr", "title": "percentage(%)"},
						{"data": "total_hh_m", "title": "Total Surveyed HH Members"},
						{"data": "total_blw_18", "title": "No. of people below 18"},
						{"data": "total_18_44", "title": "No. of people in 18-44"},
						{"data": "1_dose_done_18_44", "title": "1st dose taken"},
						{"data": "2_dose_done_18_44", "title": "2nd dose taken"},
						{"data": "total_intrested_18_44", "title": "interested"},
						{"data": "total_abv_45", "title": "No. of people in 45+"},
						{"data": "total_1_dose_45", "title": "1st dose taken "},
						{"data": "total_2_dose_45", "title": "2nd dose taken"},
						{"data": "total_intrested_45", "title": "interested"},
						{"data": "total_intrested", "title": "Total interested"},
						{"data": "total_1_dose_elg_18_44", "title": "No. of people eligible for 1st dose: 18-44"},
						{"data": "total_1_dose_elg_abv_45", "title": "No. of people eligible for 1st dose: 45+"},
						{"data": "city_name", "title":"City Name"}
					],
					"scrollX": true
			
		});
	}
	}
	
	

	$(document).ready(function() {
		todayDate = changeDateFormat(todayTime);
		startDate = StartDate(todayTime);
		$("#startDate").val(startDate);
		$("#endDate").val(todayDate);
		$("#endDate").change(function(){
			var date1 = new Date(document.getElementById('endDate').value);
			change = changeDateAfter(date1);
			$("#startDate").val(change);
		});

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

					load_report_covid();
				}
	        }
		});


	});