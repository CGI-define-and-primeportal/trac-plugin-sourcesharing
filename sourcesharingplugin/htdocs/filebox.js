jQuery(function($){
  // The list of files is "live" (may be updated with ajax), so we need to
  // use the live bind to attach to updated rows.
  $('#dirlist .fileselect').live('click', function(e){
    if (! $('#left').hasClass('shrunk')) {
      $('#left').addClass('shrunk').animate({width: '79%'},1000,function() {
        $('#right').addClass('grown').fadeIn('slow');
      });
    };
    var sel = $('#filebox-files')
    var cb = $(this)
    // Read the filename from a hidden span set in stream in contextmenuplugin
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
    $('#filebox-notice').fadeOut()
  })
  // Disable unimplemented buttons
  $('#delete, #mkdir, #upload').click(function(e){ alert('Not implemented yet'); return false })
  // Override the normal http form post ("normal" posting isn't handled yet)
  $('#filebox-form').submit(function(e){return false})
  // Send the files
  $('#do_send').click(function(e){
    // Grab data
    var btn = $(this).attr('disabled', true)
    if (!$('#filebox-files').val()) {
      alert('No files selected')
      btn.attr('disabled', false)
      return false
    } else if (!$('input[name="user"]').val()) {
      alert('No recipients selected')
      btn.attr('disabled', false)
      return false
    }
    var fields = $('#filebox-form').serializeArray()
    // Send it
    $.ajax({
      url: $('#filebox-form').attr('action'),
      type: 'POST',
      data: $.param(fields),
      success: function(data, textStatus, xhr){
        btn.attr('disabled', false)
        // Clear form
        $('#subject, #message').val('')
        $('#selected-users').empty()
        // Hide send files form
        $('#sourcesharer').slideUp()
        $('#send').attr('disabled', false)
        if (data.files.length && data.recipients.length) {
          $('#filebox-notice').text('Sent ' + data.files.join(', ') + ' to: ' + data.recipients.join(', ')).fadeIn()
        }
        if (data.failures.length) {
          $('#filebox-errors').text('Errors: ' + data.failures.join(', ')).fadeIn()
        }
      },
      error: function(xhr, textStatus, errorThrown) {
        $('#filebox-errors').text('Errors: ' + xhr.responseText).fadeIn()
        btn.attr('disabled', false)
      }
    })
  })
})