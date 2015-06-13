function toggleState(sensorId) {
    var state = $("#state_" + sensorId).html();
    var targetState = state == 1 ? 0: 1;

    console.log("toggle. Sensor: " + sensorId + ", targetState: " + targetState);
    $.get('/sensors/' + sensorId + '/' + targetState, function(res, code) {
        if (code == "success") {
            var html_text;
            if (targetState == 1) {
                old_span_class = "state-off";
                span_class = "state-on";
                span_html = "An";
                button_value = "Ausschalten";
                old_button_class = "btn-success";
                new_button_class = "btn-danger";
            } else {
                old_span_class = "state_on";
                span_class = "state-off";
                span_html = "Aus";
                button_value = "Anschalten";
                old_button_class = "btn-danger";
                new_button_class = "btn-success";

                $('#power_' + sensorId).html(0);
            }

            var span = $('#span_' + sensorId);
            span.removeClass(old_span_class).addClass(span_class);
            span.html(span_html);

            var button = $('#state_button_' + sensorId);
            button.html(button_value);
            button.removeClass(old_button_class).addClass(new_button_class);

            $('#state_' + sensorId).html(targetState);
        } else {
            console.log("Error: " + code);
            console.log("Response: " + res);
        }
    });
}

function fetchPowerUsage() {
    console.log("fetchPowerUsage");

    $.get('/sensors/power', function(res) {
        console.log("power usage: " + res);

        res_json = JSON.parse(res);

        for (var i in res_json) {
            $('#power_' + res_json[i].port_id).html(res_json[i].power);
        }
    });
}