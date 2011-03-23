jQuery(function($){
  $('#user-select').live('change', function(e){
    var mailto = $(this).val(),
        label = this.options[this.selectedIndex].text
    // Check that we have an email in either value or label
    // XXX: this may not be needed when we can ldap look up email in the controller
    if (!mailto || (mailto.indexOf('@') == -1 && label.indexOf('@') == -1)) {
      $('#filebox-errors').text($.format(_("$1 is either not an email or the user's email is not known."), label)).fadeIn()
      setTimeout(function(){$('#filebox-errors').empty().fadeOut()}, 5000)
      return
    }
    var added = false
    $(this.form, 'input[name="user"]').each(function(i, x) {
      if ($(x).val() == mailto) {
        added = true
        return
      }
    })
    if (added)
      return
    var i = $('<div class="user-entry">')
    i.text(label).click(function(e){$(this).remove()})
    i.attr('title', 'Click to remove')
    i.append($('<input type="hidden" name="user"/>').val(mailto))
    i.append($('<span> x </span>'))
    $('#selected-users').append(i)
  })
  $('#share-files').click(function(e) {
    $('#browser-filebox').dialog({
      title: _("Send Selected Files by Email")
    })
    return false
  })
  // The list of files is "live" (may be updated with ajax), so we need to
  // use the live bind to attach to updated rows.
  $('#dirlist .fileselect').live('click', function(e){
    var sel = $('#filebox-files'),
        cb = $(this),
    // Read the filename from a hidden span set in stream in contextmenuplugin
        link = cb.closest('tr').find('td.name span.filenameholder'),
        href = link.text(),
        send = $('#send');
    // Add/remove filenames from the filebox when checkboxes change
    if (cb.checked()) {
      var cls = link.attr('class'),
          text = link.text();

      // Hint whether we added a dir or a file
      if (link.hasClass('dir')) {
        text += ' [dir]';
        send.attr('disabled', true);
      } else if (link.hasClass('file'))
        text += ' [file]'
        send.attr('disabled', false);
      // Add the option and pre-select it
      var o = $('<option>').text(text)
                           .val(href)
                           .attr('selected', true)
      sel.append(o)
    } else {
      // Find the option and remove it
      sel.children('option[value="' + href + '"]').remove()
      var send_enabled = false;

      sel.children().each(function (idx, item) {
        send_enabled = true;
        if (item.text.match(/\[dir\]$/)) {
          send_enabled = false;
          return;
        }
      });
      send.attr('disabled', !send_enabled);
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
        $('#send').attr('disabled', false)
        if (data.files.length && data.recipients.length) {
          $('#filebox-notice').text('Sent ' + data.files.join(', ') + ' to: ' + data.recipients.join(', ')).fadeIn()
        }
        // Clear recipients
        $('#selected-users').empty()
        if (data.failures.length) {
          $('#filebox-errors').text('Errors: ' + data.failures.join(', ')).fadeIn()
        } else {
          // Clear message
          $('#subject, #message').val('')
          $('#sourcesharer').slideUp()
        }
      },
      error: function(xhr, textStatus, errorThrown) {
        $('#filebox-errors').text('Errors: ' + xhr.responseText).fadeIn()
        btn.attr('disabled', false)
        $('#send').attr('disabled', false)
      }
    })
  })
})
