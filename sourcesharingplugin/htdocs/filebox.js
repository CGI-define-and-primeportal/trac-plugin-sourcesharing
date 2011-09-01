jQuery(function($){
  $('#user-select').live('change', function(e){
    var mailto = $(this).val(),
        label = this.options ? this.options[this.selectedIndex].text : mailto
    // Check that we have an email in either value or label
    // XXX: this may not be needed when we can ldap look up email in the
    // controller
    if (!mailto || (mailto.indexOf('@') == -1 && label.indexOf('@') == -1)) {
      $('#filebox-errors').text($.format(_("$1 is either not an email or the user's email is not known."), label)).fadeIn()
      setTimeout(function(){$('#filebox-errors').empty().fadeOut()}, 5000)
      return
    }
    var added = false
    $('input[name="user"]', this.form).each(function(i, x) {
      if ($(x).val() == mailto) {
        added = true
        return
      }
    })
    if (added)
      return
    var i = $('<div class="user-entry">')
    i.append($('<button>').text(label)).click(function(e){$(this).remove()})
    i.attr('title', 'Click to remove')
    i.append($('<input type="hidden" name="user"/>').val(mailto))
    // i.append($('<span> x </span>'))
    $('#selected-users').append(i)
  })
  // Dialog for sending files
  var dialog = $('#browser-filebox') 
  $('#share-files').click(function(e) {
    // Hide buttons from template
    $('.buttons', dialog).remove()
    // Remove messages
    $('#filebox-errors, #filebox-notice').empty().hide()
    // Open the dialog
    dialog.dialog({
      title: _("Send Selected Files by Email"),
      width: 480,
      closeOnEscape: false,
      buttons: [
        { text: _("Cancel"),
          click: function() {
            $(this).dialog('close')
          },
          'class': 'sprite-button sprite-buttonCancel sprite-buttonSpecial'
        },
        { text: _("Send"),
          click: function() {
            do_send()
          },
          'class': 'sprite-button sprite-buttonSend sprite-buttonSpecial'
        }
      ]
    }).dialog('open')
    return false
  })
  // The list of files is "live" (may be updated with ajax), so we need to
  // use the live bind to attach to updated rows.
  $('#dirlist .fileselect').live('click', function(e){
    var sel = $('#filebox-files'),
        cb = $(this),
        // Read the filename from a hidden span set in stream in contextmenuplugin
        link = cb.closest('tr').find('td.name span.filenameholder'),
        href = link.text()
    // Add/remove filenames from the filebox when checkboxes change
    if (cb.checked()) {
      var cls = link.attr('class'),
          text = link.text();

      // Hint whether we added a dir or a file
      if (link.hasClass('dir')) {
        text += ' [dir]';
      } else if (link.hasClass('file'))
        text += ' [file]'
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
    }
  })

  // Disable unimplemented buttons
  $('#delete, #mkdir, #upload').click(function(e){ alert('Not implemented yet'); return false })
  // Override the normal http form post ("normal" posting isn't handled yet)
  $('#filebox-form').submit(function(e){return false})
  // Send the files

  function do_send() {
    if (!$('#filebox-files').val()) {
      alert('No files selected')
      return false
    } else if (!$('input[name="user"]').val()) {
      alert('No recipients selected')
      return false
    }
    var fields = $('#filebox-form').serializeArray()
    // Send it
    $.ajax({
      url: $('#filebox-form').attr('action'),
      type: 'POST',
      data: $.param(fields),
      success: function(data, textStatus, xhr){
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
          setTimeout(function(){dialog.dialog('close'); $('#filebox-errors, #filebox-notice').empty()}, 3000)
        }
      },
      error: function(xhr, textStatus, errorThrown) {
        $('#filebox-errors').text('Errors: ' + xhr.responseText).fadeIn()
      }
    })
  }
})
