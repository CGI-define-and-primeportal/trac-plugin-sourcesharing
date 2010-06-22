jQuery(function($){
  $('#dirlist .fileselect').live('click', function(e){
    var sel = $('#filebox-files')
    var cb = $(this)
    var link = cb.closest('tr').find('td.name span.filenameholder')
    var href = link.text()
    if (cb.checked()) {
      var cls = link.attr('class')
      var text = link.text()
      if (link.hasClass('dir'))
        text += ' [dir]'
      else if (link.hasClass('file'))
        text += ' [file]'
      var o = $('<option>').text(text)
                           .val(href)
                           .attr('selected', true)
      sel.append(o)
    } else {
      sel.children('option[value="' + href + '"]').remove()
    }
  })
})