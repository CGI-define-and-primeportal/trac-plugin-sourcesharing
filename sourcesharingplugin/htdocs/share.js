jQuery(function($){
  $('#user-select').live('change', function(e){
    var mailto = $(this).val()
    if (!mailto) {
      return
    }
    var i = $('<div style="border:1px dotted #ddd;padding:3px;float:left;margin:2px;cursor:pointer">')
    i.text(mailto).click(function(e){$(this).remove()})
    i.attr('title', 'Click to remove')
    i.append($('<input type="hidden" name="user"/>').val(mailto))
    i.append($('<span style="color:red;cursor:pointer"> x </span>'))
    $('#selected-users').append(i)
  })
})
