$(document).ready(function(){
    $(document).on('shown.bs.modal', function() {
        $(this).find('input[name=name]').focus();
    });
});
