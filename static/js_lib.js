function toggleState(type, name, sensorId) {
    var state = $("#state_" + name + '_' + sensorId).html();
    var targetState = state == 1 ? 0: 1;

    console.log("toggle. Name: " + name + ", Sensor: " + sensorId + ", targetState: " + targetState);
    $.get('/' + name + '/sensors/' + sensorId + '/' + targetState, function(res, code) {
        if (code == "success") {
            if (type != "server") {
                toggleButtonState(name, sensorId, state, targetState);
            } else {
                if (targetState == 1) {
                    // 2 == starting
                    toggleButtonState(name, sensorId, 0, 2);
                } else {
                    // 3 = shut down in progress
                    toggleButtonState(name, sensorId, 1, 3);
                }
            }

        } else {
            console.log("Error: " + code);
            console.log("Response: " + res);
        }
    });
}

function changeButtonStateIfChanged(name, sensorId, state) {
    var currentState = $("#state_" + name + '_' + sensorId).html();

    if (currentState == 2 || currentState == 3) {
        if ((currentState == 2 && state == 1) || (currentState == 3 && state == 0)) {
            toggleButtonState(name, sensorId, currentState, state);
        }
    } else if (currentState != state) {
        toggleButtonState(name, sensorId, currentState, state);
    }
}

function toggleButtonState(name, sensorId, currentState, targetState) {
    var old_span_class;
    var span_class;
    var span_html;
    var button_value;
    var old_button_class;
    var new_button_class;

    if (currentState == 0) {
        old_button_class = "btn-success";
        old_span_class = "state-off";
    } else if (currentState == 1) {
        old_button_class = "btn-danger";
        old_span_class = "state-on";
    } else if (currentState == 2 || currentState == 3) {
        old_button_class = "btn-warning";
        old_span_class = "state-progress";
    }

    if (targetState == 1) {
        span_class = "state-on";
        span_html = "An";
        button_value = "Ausschalten";
        new_button_class = "btn-danger";
    } else if (targetState == 0) {
        span_class = "state-off";
        span_html = "Aus";
        button_value = "Anschalten";
        new_button_class = "btn-success";

        $('#' + name + '_power_' + sensorId).html(0);
    } else if (targetState == 2){
        // start in progress
        span_class = "state-progress";
        span_html = "Starten";
        button_value = "Ausschalten";
        new_button_class = "btn-warning";
    } else if (targetState == 3) {
        // shutdown in progress
        span_class = "state-progress";
        span_html = "Herunterfahren";
        button_value = "Anschalten";
        new_button_class = "btn-warning";
    }

    var span = $('#span_' + name + '_' + sensorId);
    span.removeClass(old_span_class).addClass(span_class);
    span.html(span_html);

    var button = $('#state_button_' + name + '_' + sensorId);
    button.html(button_value);
    button.removeClass(old_button_class).addClass(new_button_class);

    $('#state_' + name + '_' + sensorId).html(targetState);
}

function fetchPowerUsage() {
    console.log("fetchPowerUsage");

    $.get('/sensors/power', function(res) {
        console.log("power usage: " + res);

        var res_json = JSON.parse(res);

        for (var i in res_json) {
            var name = res_json[i].name;
            if (res_json[i].type == "power_cord") {
                for (var j in res_json[i].data) {
                    var power_usage = res_json[i].data[j].state['power'];
                    var sensorId = res_json[i].data[j].port;
                    var state = res_json[i].data[j].state['output'];
                    $('#' + name + '_power_' + sensorId).html(Math.round(power_usage * 10) / 10);

                    changeButtonStateIfChanged(name, sensorId, state);
                }
            } else if (res_json[i].type == "server") {
                var state = res_json[i].data.output;
                changeButtonStateIfChanged(name, 0, state);
            }

        }
    });
}