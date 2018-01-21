$(document).ready(function(){
    $('.btn-toggleable').find('label').click(function(e){
        if ($(this).hasClass('active')) {
            $(this).find('input').removeAttr('checked');

            $($(this).parent().children()[0]).trigger('click');
            return false;
        }
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

function on_answer_success(data) {
    if (data.result == 'success') {
        $('.self-evaluate').find('a').each(function(){
            $(this).attr('href', $(this).attr('href').replace('/evaluate/1', '/evaluate/' + data.answer_id));
        });
        $('.show-on-answered').slideDown();
        $('.hide-on-answered').slideUp();
    }
}
