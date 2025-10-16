import { describe, it, expect, vi, beforeEach } from 'vitest';
import { attachChatInputHandler } from '../chat-input.js';

describe('attachChatInputHandler', () => {
  let form;
  let input;
  let sendBtn;

  beforeEach(() => {
    form = document.createElement('form');
    form.requestSubmit = vi.fn();
    input = document.createElement('textarea');
    sendBtn = document.createElement('button');
    sendBtn.disabled = false;
  });

  it('submits form on Enter without modifiers', () => {
    attachChatInputHandler(form, input, sendBtn);
    const event = new KeyboardEvent('keydown', { key: 'Enter', cancelable: true });
    input.dispatchEvent(event);
    expect(event.defaultPrevented).toBe(true);
    expect(form.requestSubmit).toHaveBeenCalledTimes(1);
  });

  it('keeps newline on Shift+Enter', () => {
    attachChatInputHandler(form, input, sendBtn);
    const event = new KeyboardEvent('keydown', { key: 'Enter', shiftKey: true, cancelable: true });
    input.dispatchEvent(event);
    expect(event.defaultPrevented).toBe(false);
    expect(form.requestSubmit).not.toHaveBeenCalled();
  });

  it('does nothing when send button disabled', () => {
    sendBtn.disabled = true;
    attachChatInputHandler(form, input, sendBtn);
    const event = new KeyboardEvent('keydown', { key: 'Enter', cancelable: true });
    input.dispatchEvent(event);
    expect(event.defaultPrevented).toBe(true);
    expect(form.requestSubmit).not.toHaveBeenCalled();
  });

  it('fallbacks to form.submit when requestSubmit is unavailable', () => {
    const submit = vi.fn();
    form.requestSubmit = undefined;
    form.submit = submit;
    attachChatInputHandler(form, input, sendBtn);
    const event = new KeyboardEvent('keydown', { key: 'Enter', cancelable: true });
    input.dispatchEvent(event);
    expect(submit).toHaveBeenCalledTimes(1);
  });
});
