jQuery(function($){
  $('#user-select').live('change', function(e){
    var mailto = $(this).val(),
        label = this.options ? this.options[this.selectedIndex].text : mailto
    // Check that we have an email in either value or label
    // XXX: this may not be needed when we can ldap look up email in the
    // controller
    if (!mailto || (mailto.indexOf('@') == -1 && label.indexOf('@') == -1)) {
      $('#filebox-errors').text($.format(_("$1 is either not an email or the user's email is not known."), label)).fadeIn()
      document.getElementById('user-select').value='';
      document.getElementById('user-select').selectedIndex = '0';
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
    document.getElementById('user-select').selectedIndex = '0';
    // i.append($('<span> x </span>'))
    $('#selected-users').append(i)
  })
  // Dialog for sending files
  $('.share-files-multiple').click(function(e) { 
    e.preventDefault();
    open_send_dialogue();
  });
  $('.share-files').click(function(e) { open_send_dialogue($(this)); });
  
  // One function for both single and multiple send funcs
  function open_send_dialogue(to_send) {
    
    // If no specific file selected, send all checked files
    if(to_send === undefined) to_send = $("#dirlist input[type=checkbox]:checked");
    
    var sel = $("#filebox-files"),
      dialog = $('#browser-filebox');
      
    sel.html("");
    
    // Set the to send values based on selected elements
    to_send.each(function() {   
      // Retrieve name and type (dir/file) from a hidden span set in stream in contextmenuplugin  
      var cb = $(this),
        link = cb.closest('tr').find('td.name span.filenameholder'),
        href = link.text(),
        text = link.text();
      // Hint whether we added a dir or a file
      if (link.hasClass('dir')) text += ' [dir]';
      else if (link.hasClass('file')) text += ' [file]';
      // Add the option and pre-select it
      var o = $('<option>').text(text)
                         .val(href)
                         .attr('selected', true)
      sel.append(o)
    });

    // Reset all form values
    document.getElementById('user-select').selectedIndex = '0';  // Back to top of select list
    $('#selected-users').empty(); // Clear selected users
    $('.buttons', dialog).remove(); // Hide buttons from template
    $('#filebox-errors, #filebox-notice').empty().hide(); // Remove messages
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
          'class': 'btn btn-primary btn-mini'
        },
        { text: _("Send"),
          click: function() {
            do_send()
          },
          'class': 'btn btn-primary btn-mini'
        }
      ]
    }).dialog('open')
    return false;  
  }
  
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
