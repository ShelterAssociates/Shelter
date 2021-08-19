var change = 0;
var delta = 30 * 1000 * 60 * 60 * 24;
var todayTime = new Date();
var aMonthAgo = todayTime.getTime() - delta ;
var aMonthAgoTime = new Date(aMonthAgo);
var thisYear = new Date();
var aprilOfYear = new Date(thisYear.setMonth(03,01));


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

});