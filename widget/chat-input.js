export function attachChatInputHandler(form, input, sendBtn) {
  if (!form || !input) return;
  input.addEventListener('keydown', (event) => {
    if (event.key !== 'Enter') return;
    if (event.shiftKey || event.altKey || event.ctrlKey || event.metaKey || event.isComposing) {
      return;
    }
    event.preventDefault();
    if (sendBtn && sendBtn.disabled) return;
    if (typeof form.requestSubmit === 'function') {
      form.requestSubmit();
    } else if (typeof form.submit === 'function') {
      form.submit();
    }
  });
}

if (typeof window !== 'undefined') {
  window.attachChatInputHandler = attachChatInputHandler;
}
