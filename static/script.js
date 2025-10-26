const chatWindow = document.getElementById('chat-window');
const composer = document.getElementById('composer');
const input = document.getElementById('chat-input');
const scoreEl = document.getElementById('score-value');

function createMessage(role, content) {
  const wrapper = document.createElement('div');
  wrapper.classList.add('message', role);

  const bubble = document.createElement('div');
  bubble.classList.add('bubble');
  bubble.textContent = content;

  wrapper.appendChild(bubble);
  return wrapper;
}

function pushMessage(role, content) {
  const msg = createMessage(role, content);
  chatWindow.appendChild(msg);
  chatWindow.scrollTo({ top: chatWindow.scrollHeight, behavior: 'smooth' });
}

composer.addEventListener('submit', async (event) => {
  event.preventDefault();
  const text = input.value.trim();
  if (!text) {
    return;
  }

  pushMessage('user', text);
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

    pushMessage('reply', data.reply || '...');
  } catch (error) {
    pushMessage('reply', 'Server error. Try again soon.');
    console.error(error);
  }
});

window.addEventListener('load', () => {
  input.focus();
});
