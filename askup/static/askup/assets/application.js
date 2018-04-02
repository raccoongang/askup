$(document).ready(function(){
    var alert_timeout = null;
    alert_init();

    $('.btn-feedback').on('click', show_evaluated_and_go_next);

    $('[custom-valid-message]').each(function() {
        var custom_valid_message = $(this).attr('custom-valid-message');
        $(this).find('input, textarea').each(function() {
            $(this)[0].oninvalid = function(e) {
                e.target.setCustomValidity("");
                if (!e.target.validity.valid) {
                    e.target.setCustomValidity(custom_valid_message);
                }
            };
            $(this)[0].oninput = function(e) {
                e.target.setCustomValidity("");
            };
        });
    });

    $('.btn-toggleable').find('label').click(function(e){
        if ($(this).hasClass('active')) {
            $(this).find('input').removeAttr('checked');

            $($(this).parent().children()[0]).trigger('click');
            return false;
        }

        var radio = $(this).find('input').first();

        if (radio.length == 0) {
            return;
        }

        show_blooms_taxonomy_hint(radio);
    });

    $('.upvote-button, .downvote-button').click(function(e){
        vote_url = $(this).data('vote-url');
        question_id = $(this).data('question-id');

        $.ajax({
            url: vote_url,
            type: 'GET',
            data: $(this).serialize(),
            success: function(data) {
                on_vote_success(question_id, data);
            },
            error: function(data) {
                console.log(data);
            }
        });
        return false;
    });

    $(document).ready(function(){
        $('[data-toggle="tooltip"]').tooltip();
    });

    $('.hide-on-answered textarea#id_text').on('keydown', function(event) {
        if (event.keyCode === 13) {
            if (event.ctrlKey) {
                $(this).val($(this).val() + '\n');
            } else {
                $(this).parents('.hide-on-answered').find('#submit-id-submit').trigger('click');
            }

            event.preventDefault()
        }
    });

    $('.my-subject-row').click(on_click_my_subject);

    $('#user_organization_filter').on('change', function(event) {
        window.location.href = $(this).val();
    });

    check_active_blooms_taxonomy();
});

function alert_init() {
    alert_timeout = window.setTimeout(alert_open_animation, 400);
}

function alert_open_animation(close_timeout, callback) {
    var alert_selector = '.alert-success, .alert-warning, .alert-danger';

    if (typeof(close_timeout) === 'undefined') {
        close_timeout = 0;
    }

    if (typeof(callback) === 'undefined') {
        callback = function () {};
    }

    $('.alert, .close-alert').on('click', function() {
        $(alert_selector).slideUp(400);
    });
    $(alert_selector).slideDown();

    if (close_timeout) {
        window.clearTimeout(alert_timeout);
        alert_timeout = window.setTimeout(function() {$(alert_selector).slideUp(400, callback);}, close_timeout);
    }
}

function show_evaluated_and_go_next(event) {
    var self = this;
    $('.btn-feedback').unbind();
    $('.btn-feedback').on('click', function() {return false;});
    var callback = function() {window.location.href = $(self).attr('href');};

    if ($(this).hasClass('btn-success')) {
        show_alert('success', 'Nicely done!', 2000, callback);
    } else if  ($(this).hasClass('btn-maybe')) {
        show_alert('warning', 'Not bad', 2000, callback);
    } else {
        show_alert('danger', 'No worries, you\'ll get it next time', 2000, callback);
    }

    return false;
}

function show_alert(cls, message, timeout, callback) {
    if (typeof(timeout) === 'undefined') {
        timeout = 5000;
    }

    if (typeof(callback) === 'undefined') {
        callback = function() {};
    }

    var close_alert = '<a href="#" class="close-alert grow"><i class="fa fa-times-circle"></i></a>';
    $('.alert').hide();
    $('.alert').html(message + close_alert);
    $('.alert').attr('class', 'alert center alert-' + cls);

    window.clearTimeout(alert_timeout);
    alert_timeout = alert_open_animation(timeout, callback);
}

$(document).on('shown.bs.modal', function() {
    $(this).find('input[name=name]').focus();
});

$(document).on('submit', '.hide-on-answered>form', function() {
    $.ajax({
        url: '',
        type: 'POST',
        data: $(this).serialize(),
        success: on_answer_success,
        error: function(data) {
            console.log(data)
        }
    });
    return false;
});

function on_vote_success(question_id, data) {
    if (data.result == 'error') {
        show_alert('danger', data.message);
        return false;
    }

    show_alert('success', data.message);
    $('.question-' + question_id + '-net-votes').html(data.value);
}

function on_answer_success(data) {
    if (data.result == 'success') {
        $('h4.your-answer').html($('#id_text').val());
        $('.self-evaluate').find('a').each(function(){
            $(this).attr('href', data.evaluation_urls[$(this).attr('data-evaluation-name')]);
        });
        $('.show-on-answered').slideDown();
        $('.hide-on-answered').slideUp();
        return;
    }

    if ('redirect_url' in data) {
        var callback = function() {window.location.href = data.redirect_url};
        var notification = data.notification;
        show_alert('danger', notification, 5000, callback);
    }
}

var blooms_taxonomy_hints = {
    '0': "Retrieving relevant knowledge from long-term memory",
    '1': "Determining the meaning of facts by building connections between new and prior knowledge",
    '2': "Carry out a procedure in a given situation or predict an outcome given a perturbation in the system",
    '3': "Interpreting data and selecting the best conclusion, making a diagnosis",
    '4': "Making judgements based on criteria and standards",
    '5': "Developing new ideas, combining elements into new patterns"
};

function check_active_blooms_taxonomy() {
    var radios = $('.blooms-taxonomy .btn-toggleable').find('input[type=radio]:checked');

    if (radios.length == 0) {
        return;
    }

    show_blooms_taxonomy_hint(radios.first());
}

function show_blooms_taxonomy_hint(taxonomy_element) {
    if (taxonomy_element.val() === '') {
        $('.blooms-taxonomy .blooms-taxonomy-hints').html('');
    } else {
        $('.blooms-taxonomy .blooms-taxonomy-hints').html(
            blooms_taxonomy_hints[parseInt(taxonomy_element.val())]
        );
    }
}

function on_click_my_subject() {
    var subject_id = $(this).attr('data-subject-id');
    var subject_questions_url = $(this).attr('data-questions-url');
    var subject_element_id = 'my-subject-' + subject_id + '-questions';
    var subject_element = $(this);
    var glyphicon_element = $(subject_element).find('.glyphicon');
    var subject_questions_element = $('#' + subject_element_id);

    if (subject_questions_element.length === 0) {
        $(this).after(
            '<div class="row my-subject-questions margin-right-15" id="' +
            subject_element_id +
            '"><div class="center"><img src="' + STATIC_URL_LOADER_IMAGE +
            '"/></div></div>'
        );
        subject_questions_element = $('#' + subject_element_id);
        $(glyphicon_element).removeClass('glyphicon-triangle-right');
        $(glyphicon_element).addClass('glyphicon-triangle-bottom');
        do_user_questions_ajax_request(subject_questions_url, subject_id, subject_questions_element);
    } else {
        subject_questions_element.remove();
        $(glyphicon_element).removeClass('glyphicon-triangle-bottom');
        $(glyphicon_element).addClass('glyphicon-triangle-right');
    }

    return false;
}

function do_user_questions_ajax_request(subject_questions_url, subject_id, subject_questions_element) {
    $.ajax({
        url: subject_questions_url,
        type: 'GET',
        success: function(data) {
            on_subject_questions_get(data, subject_id, subject_questions_element);
        },
        error: function(data) {
            console.log(data);
        }
    });
}

function on_subject_questions_get(data, subject_id, subject_questions_element) {
    var questions_wrapper = $(
        '<div style="display: none" id="my-subject-' + subject_id + '-questions-wrapper"></div>'
    );

    for (var i=0; i < data.questions.length; i++) {
        question_html = QUESTION_ROW_TEMPLATE.replace(/888/g, data.questions[i][0]);
        question_html = question_html.replace(/999/g, data.questions[i][1]);
        question_html = question_html.replace(/##question_text##/g, data.questions[i][2]);
        question_html = question_html.replace(/##vote_value##/g, data.questions[i][3]);
        questions_wrapper.append(question_html);
    }

    if (!data.can_edit) {
        $(questions_wrapper).find('.question-actions').hide();
    }

    subject_questions_element.html(questions_wrapper.html());
}
