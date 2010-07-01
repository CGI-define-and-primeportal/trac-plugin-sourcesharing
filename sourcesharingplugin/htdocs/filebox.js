jQuery(function($){
  // The list of files is "live" (may be updated with ajax), so we need to
  // use the live bind to attach to updated rows.
  $('#dirlist .fileselect').live('click', function(e){
    var sel = $('#filebox-files')
    var cb = $(this)
    // Read the filename from a hidden span set in stream in sourcesharer 
    var link = cb.closest('tr').find('td.name span.filenameholder')
    var href = link.text()
    // Add/remove filenames from the filebox when checkboxes change
    if (cb.checked()) {
      var cls = link.attr('class')
      var text = link.text()
      // Hint whether we added a dir or a file
      if (link.hasClass('dir'))
        text += ' [dir]'
      else if (link.hasClass('file'))
        text += ' [file]'
      // Add the option and pre-select it
      var o = $('<option>').text(text)
                           .val(href)
                           .attr('selected', true)
      sel.append(o)
    } else {
      // Find the option and remove it
      sel.children('option[value="' + href + '"]').remove()
    }
  })
  // Handle send button
  $('#send').click(function(e) {
    // Show the "send file" extra form options
    $('#sourcesharer').slideDown()
    $(this).attr('disabled', true)
  })
  // Handle cancel button
  $('#cancel').click(function(e){
    // Hide the "send file" extra form options
    $('#sourcesharer').slideUp()
    $('#send').attr('disabled', false)
  })
  // Override the normal http form post ("normal" posting isn't handled yet)
  $('#filebox-form').submit(function(e){return false})
  // Send the files
  $('#do_send').click(function(e){
    // Grab data
    var fields = $('#filebox-form').serializeArray()
    var data = ''
    $.each(fields, function(i, f){
      data += f.name + ': ' + f.value + '\n'
    })
    data += $.param(fields)
    alert('Sending: \n' + data)
  })
})
