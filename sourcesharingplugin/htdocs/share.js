jQuery(function($){
  $('#user').live('change', function(e){
    var i = $('<input name="users" type="text">').val($(this).val())
    $('#selected-users').append(i)
    $('#selected-users').append($('<span style="color:red;cursor:pointer"> x </span>').click(function(e){i.remove(); $(this).remove()}))
  })
})