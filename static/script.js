const chatWindow = document.getElementById('chat-window');
const composer = document.getElementById('composer');
const input = document.getElementById('chat-input');
const scoreEl = document.getElementById('score');

function createMessage(role, content, metaText) {
  const wrapper = document.createElement('div');
  wrapper.classList.add('message', role);

  const bubble = document.createElement('div');
  bubble.classList.add('bubble');
  if (content.includes('\n')) {
    const pre = document.createElement('pre');
    pre.textContent = content;
    bubble.appendChild(pre);
  } else {
    bubble.textContent = content;
  }

  const meta = document.createElement('div');
  meta.classList.add('meta');
  meta.textContent = metaText;

  wrapper.appendChild(bubble);
  wrapper.appendChild(meta);
  return wrapper;
}

function pushMessage(role, content, metaText) {
  const msg = createMessage(role, content, metaText);
  chatWindow.appendChild(msg);
  chatWindow.scrollTo({ top: chatWindow.scrollHeight, behavior: 'smooth' });
}

composer.addEventListener('submit', async (event) => {
  event.preventDefault();
  const text = input.value.trim();
  if (!text) {
    return;
  }

  pushMessage('user', text, 'you • challenger');
  input.value = '';

  try {
    const response = await fetch('/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text }),
    });

    if (!response.ok) {
      throw new Error('Network response was not ok');
    }

    const data = await response.json();
    if (typeof data.score === 'number') {
      scoreEl.textContent = data.score;
    }

    const meta = data.command ? 'bot • secret stash' : 'bot • banter mode';
    pushMessage('bot', data.reply || "...", meta);
  } catch (error) {
    pushMessage('bot', "Server's taking a nap. Try again in a sec.", 'bot • offline?');
    console.error(error);
  }
});

window.addEventListener('load', () => {
  input.focus();
});
