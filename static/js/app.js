// Global State
let activeFileId = null;
let chatHistory = [];
let audioFiles = []; // to keep track of generated audio

// DOM Elements
const elements = {
    leftSidebar: document.getElementById('left-sidebar'),
    rightSidebar: document.getElementById('right-sidebar'),
    fileUpload: document.getElementById('file-upload'),
    uploadStatus: document.getElementById('upload-status'),
    filesList: document.getElementById('files-list'),
    audioList: document.getElementById('audio-list'),
    activeFileTitle: document.getElementById('active-file-title'),
    chatHistory: document.getElementById('chat-history'),
    chatForm: document.getElementById('chat-form'),
    chatInput: document.getElementById('chat-input'),
    chatSubmit: document.getElementById('chat-submit'),
    docLangSelect: document.getElementById('doc-lang-select'),
    documentContent: document.getElementById('document-content'),
    docLoading: document.getElementById('doc-loading')
};

// Initialization
document.addEventListener('DOMContentLoaded', () => {
    loadFiles();
    setupEventListeners();
});

function setupEventListeners() {
    elements.fileUpload.addEventListener('change', handleFileUpload);
    elements.chatForm.addEventListener('submit', handleChatSubmit);

    // Enable input if file is selected
    elements.chatInput.addEventListener('input', (e) => {
        elements.chatSubmit.disabled = e.target.value.trim() === '' || !activeFileId;
    });
}

// UI Toggles
function toggleSidebar(side) {
    if (side === 'left') {
        elements.leftSidebar.classList.toggle('collapsed');
    } else if (side === 'right') {
        elements.rightSidebar.classList.toggle('collapsed');
    }
}

// File Management
async function loadFiles() {
    try {
        const response = await fetch('/api/files');
        const files = await response.json();
        renderFilesList(files);
    } catch (error) {
        console.error('Error loading files:', error);
    }
}

async function handleFileUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    elements.uploadStatus.textContent = 'Uploading and parsing...';

    try {
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Upload failed');
        }

        elements.uploadStatus.textContent = 'Upload successful!';
        setTimeout(() => { elements.uploadStatus.textContent = ''; }, 3000);

        loadFiles(); // Refresh list
    } catch (error) {
        elements.uploadStatus.textContent = `Error: ${error.message}`;
        elements.uploadStatus.style.color = 'red';
    } finally {
        event.target.value = ''; // Reset input
    }
}

function renderFilesList(files) {
    elements.filesList.innerHTML = '';

    if (files.length === 0) {
        elements.filesList.innerHTML = '<li class="empty-state" style="margin-top:0">No files uploaded.</li>';
        return;
    }

    files.forEach(file => {
        const li = document.createElement('li');
        li.className = `list-item ${file.file_id === activeFileId ? 'active' : ''}`;
        li.onclick = () => selectFile(file.file_id, file.filename);

        li.innerHTML = `
            <div class="list-item-icon"><i class="fas fa-book"></i></div>
            <div class="list-item-content">
                <div class="list-item-title" title="${file.filename}">${file.filename}</div>
                <div class="list-item-meta">${file.metadata.author || 'Unknown Author'}</div>
            </div>
        `;
        elements.filesList.appendChild(li);
    });
}

function selectFile(fileId, filename) {
    activeFileId = fileId;
    elements.activeFileTitle.textContent = filename;

    // Reset Chat
    chatHistory = [];
    elements.chatHistory.innerHTML = `
        <div class="welcome-message">
            <div class="welcome-icon"><i class="fas fa-robot"></i></div>
            <h3>Connected to ${filename}</h3>
            <p>You can now ask questions about this document or ask for a summary.</p>
        </div>
    `;

    // Enable input
    elements.chatInput.disabled = false;
    elements.chatInput.placeholder = "Ask a question about this document...";
    elements.chatInput.focus();

    // Update active class in list
    document.querySelectorAll('#files-list .list-item').forEach(el => {
        el.classList.remove('active');
    });

    // Re-render to catch active state properly
    loadFiles();

    // Load Document Content in Right Sidebar
    if (elements.rightSidebar.classList.contains('collapsed')) {
        toggleSidebar('right');
    }
    elements.docLangSelect.value = 'ar'; // Reset to original
    loadDocumentContent();
}

// Document Viewer
async function loadDocumentContent() {
    if (!activeFileId) return;

    const lang = elements.docLangSelect.value;
    elements.docLoading.classList.remove('hidden');
    elements.documentContent.style.opacity = '0.5';

    if (lang === 'ar') {
        elements.documentContent.setAttribute('dir', 'rtl');
    } else {
        elements.documentContent.removeAttribute('dir');
    }

    try {
        const response = await fetch(`/api/file/${activeFileId}/content?lang=${lang}`);
        if (!response.ok) throw new Error('Failed to fetch content');

        const data = await response.json();
        elements.documentContent.textContent = data.content;
    } catch (error) {
        elements.documentContent.innerHTML = `<span style="color:red">Error: ${error.message}</span>`;
    } finally {
        elements.docLoading.classList.add('hidden');
        elements.documentContent.style.opacity = '1';
    }
}

// Chat Interaction
async function handleChatSubmit(event) {
    event.preventDefault();
    if (!activeFileId) return;

    const message = elements.chatInput.value.trim();
    if (!message) return;

    // 1. Add User Message to UI
    appendMessage('user', message);
    elements.chatInput.value = '';
    elements.chatSubmit.disabled = true;

    // 2. Show typing indicator
    const typingId = showTypingIndicator();

    try {
        // 3. Send to API
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                file_id: activeFileId,
                message: message,
                history: chatHistory
            })
        });

        if (!response.ok) throw new Error('Failed to generate response');

        const data = await response.json();

        // 4. Update History
        chatHistory.push({ role: 'user', content: message });
        chatHistory.push({ role: 'assistant', content: data.response });

        // 5. Remove typing indicator & Add AI Message to UI
        removeElement(typingId);
        appendMessage('ai', data.response, true);

    } catch (error) {
        removeElement(typingId);
        appendMessage('ai', `Error: ${error.message}`);
    }
}

function appendMessage(role, text, withActions = false) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${role === 'user' ? 'msg-user' : 'msg-ai'}`;

    const icon = role === 'user' ? 'fa-user' : 'fa-robot';

    // Format newlines
    const formattedText = text.replace(/\n/g, '<br>');

    let actionsHtml = '';
    if (withActions && role === 'ai') {
        const uniqueId = 'msg-' + Date.now();
        msgDiv.id = uniqueId;
        msgDiv.setAttribute('data-text', text); // Store raw text for audio generation

        actionsHtml = `
            <div class="message-actions">
                <button class="msg-action-btn" onclick="generateAudioFromMsg('${uniqueId}', 'id')">
                    <i class="fas fa-headphones"></i> Audio (ID)
                </button>
                <button class="msg-action-btn" onclick="generateAudioFromMsg('${uniqueId}', 'en')">
                    <i class="fas fa-headphones"></i> Audio (EN)
                </button>
                <button class="msg-action-btn" onclick="generateAudioFromMsg('${uniqueId}', 'ar')">
                    <i class="fas fa-headphones"></i> Audio (AR)
                </button>
            </div>
        `;
    }

    msgDiv.innerHTML = `
        <div class="message-avatar"><i class="fas ${icon}"></i></div>
        <div class="message-content-wrapper">
            <div class="message-content">${formattedText}</div>
            ${actionsHtml}
        </div>
    `;

    elements.chatHistory.appendChild(msgDiv);
    scrollToBottom();
}

function showTypingIndicator() {
    const id = 'typing-' + Date.now();
    const msgDiv = document.createElement('div');
    msgDiv.className = 'message msg-ai';
    msgDiv.id = id;

    msgDiv.innerHTML = `
        <div class="message-avatar"><i class="fas fa-robot"></i></div>
        <div class="message-content-wrapper">
            <div class="message-content typing-indicator">
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
            </div>
        </div>
    `;

    elements.chatHistory.appendChild(msgDiv);
    scrollToBottom();
    return id;
}

function removeElement(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}

function scrollToBottom() {
    elements.chatHistory.scrollTop = elements.chatHistory.scrollHeight;
}

// Audio Generation
async function generateAudioFromMsg(msgId, lang) {
    const msgEl = document.getElementById(msgId);
    if (!msgEl) return;

    const text = msgEl.getAttribute('data-text');
    if (!text) return;

    // UI Feedback on button
    const btns = msgEl.querySelectorAll('.msg-action-btn');
    const targetBtn = Array.from(btns).find(b => b.innerText.includes(`(${lang.toUpperCase()})`));

    if (targetBtn) {
        targetBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generating...';
        targetBtn.disabled = true;
    }

    try {
        const response = await fetch('/api/generate_audio', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: text, lang: lang })
        });

        if (!response.ok) throw new Error('Audio generation failed');

        const data = await response.json();

        // Add to audio list
        audioFiles.push(data);
        renderAudioList();

        if (targetBtn) {
            targetBtn.innerHTML = '<i class="fas fa-check"></i> Done';
            setTimeout(() => {
                targetBtn.innerHTML = `<i class="fas fa-headphones"></i> Audio (${lang.toUpperCase()})`;
                targetBtn.disabled = false;
            }, 2000);
        }

    } catch (error) {
        console.error(error);
        if (targetBtn) {
            targetBtn.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Error';
            setTimeout(() => {
                targetBtn.innerHTML = `<i class="fas fa-headphones"></i> Audio (${lang.toUpperCase()})`;
                targetBtn.disabled = false;
            }, 3000);
        }
    }
}

function renderAudioList() {
    elements.audioList.innerHTML = '';

    if (audioFiles.length === 0) {
        elements.audioList.innerHTML = '<li class="empty-state" style="margin-top:0">No audio generated.</li>';
        return;
    }

    // Show left sidebar if collapsed
    if (elements.leftSidebar.classList.contains('collapsed')) {
        toggleSidebar('left');
    }

    audioFiles.slice().reverse().forEach(audio => { // show newest first
        const li = document.createElement('li');
        li.className = 'list-item';
        li.style.flexDirection = 'column';
        li.style.alignItems = 'flex-start';
        li.style.cursor = 'default';

        li.innerHTML = `
            <div style="display:flex; align-items:center; gap:0.5rem; margin-bottom: 0.25rem;">
                <div class="list-item-icon" style="color:var(--accent-color)"><i class="fas fa-file-audio"></i></div>
                <div class="list-item-title" style="font-size:0.85rem">Audio Response (${audio.filename.split('_').pop().split('.')[0].toUpperCase()})</div>
                <a href="${audio.url}" download="${audio.filename}" style="margin-left:auto; font-size:0.8rem; color:var(--text-secondary)"><i class="fas fa-download"></i></a>
            </div>
            <div class="audio-player-container">
                <audio controls preload="none">
                    <source src="${audio.url}" type="audio/mpeg">
                    Your browser does not support the audio element.
                </audio>
            </div>
        `;
        elements.audioList.appendChild(li);
    });
}
