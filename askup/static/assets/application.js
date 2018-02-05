$(document).ready(function(){
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
    });
    $('.upvote-button, .downvote-button').click(function(e){
        if ($(this).attr('data-vote') == 'upvote') {
            url_base = '/askup/question/upvote/';
        } else {
            url_base = '/askup/question/downvote/';
        }

        question_id = $(this).attr('data-vote-qid');

        $.ajax({
            url: url_base + question_id + '/',
            type: 'GET',
            data: $(this).serialize(),
            success: on_vote_success,
            error: function(data) {
                console.log(data);
            }
        });
        return false;
    });
    $(document).ready(function(){
        $('[data-toggle="tooltip"]').tooltip(); 
    });
});

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

function on_vote_success(data) {
    if (data.result == 'error') {
        return false;
    }

    $('.question-' + question_id + '-net-votes').html(data.value);
}

function on_answer_success(data) {
    if (data.result == 'success') {
        $('h4.your-answer').html($('#id_text').val());
        $('.self-evaluate').find('a').each(function(){
            $(this).attr('href', $(this).attr('href').replace('/evaluate/1', '/evaluate/' + data.answer_id));
        });
        $('.show-on-answered').slideDown();
        $('.hide-on-answered').slideUp();
    }
}
