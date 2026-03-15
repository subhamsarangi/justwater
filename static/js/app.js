function showToast(message, type) {
  const toast = $('#app-toast');
  $('#toast-body').text(message);
  toast.removeClass('toast-error');
  if (type === 'error') toast.addClass('toast-error');
  const bsToast = new bootstrap.Toast(toast[0]);
  bsToast.show();
}

function initWordCounter(textareaId, counterId, btnId, max) {
  const textarea = $('#' + textareaId);
  const counter  = $('#' + counterId);
  const btn      = $('#' + btnId);

  function update() {
    const words = textarea.val().trim() === '' ? 0 : textarea.val().trim().split(/\s+/).length;
    counter.text(words + ' / ' + max + ' words');
    if (words > max) {
      counter.addClass('over');
      btn.prop('disabled', true);
    } else {
      counter.removeClass('over');
      btn.prop('disabled', false);
    }
  }

  textarea.on('input', update);
  update();
}
