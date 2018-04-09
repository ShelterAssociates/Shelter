function highlight_buttons(){


    var btnContainer = document.getElementsByClassName("dt-buttons");

    var btns = $("button.dt-button.btn");


    for (var i = 0; i < btns.length; i++) {

        btns[i].addEventListener("click", function() {
            var current = document.getElementsByClassName("active");
            current[0].className = current[0].className.replace(" active", "");
            this.className += " active";
        });
    }

}