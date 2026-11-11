// ==========================================================================
// NORTHSTAR AIR SERVICE - CONVERSATIONAL AGENT JAVASCRIPT
// Handles in-chat interactive cards, typo clarifications, and dummy attachment
// ==========================================================================

let currentSessionId = localStorage.getItem("northstar_session_id") || null;
let lastState = null;
let cachedBookings = [];

// DOM Elements
const chatCanvas = document.getElementById("chat-canvas");
const chatMessages = document.getElementById("chat-messages");
const chatForm = document.getElementById("chat-form");
const chatInput = document.getElementById("chat-input");
const btnSend = document.getElementById("btn-send");
const typingIndicator = document.getElementById("typing-indicator");

// Voice & Audio DOM Elements
const btnVoiceRecord = document.getElementById("btn-voice-record");
const voiceRecordingOverlay = document.getElementById("voice-recording-overlay");
const voiceTimer = document.getElementById("voice-timer");
const btnVoiceRestart = document.getElementById("btn-voice-restart");
const btnVoiceCancel = document.getElementById("btn-voice-cancel");
const btnVoiceStop = document.getElementById("btn-voice-stop");
const btnToggleTts = document.getElementById("btn-toggle-tts");
const voiceWaveBars = document.getElementById("voice-wave-bars");

// Voice & Audio State
let mediaRecorder = null;
let currentMediaStream = null;
let audioChunks = [];
let recordingTimerInterval = null;
let recordingSeconds = 0;
let isRecording = false;
let ttsEnabled = true; // Auto-speech ON by default
let currentAudioPlayer = null;
let audioContext = null;
let audioAnalyser = null;
let audioVisualizerFrame = null;
let maxAudioVolume = 0;

// Sidebar Nav Elements
const btnNewChat = document.getElementById("btn-new-chat");
const navServiceDesk = document.getElementById("nav-service-desk");
const navBookingsLedger = document.getElementById("nav-bookings-ledger");
const cardTryBooking = document.getElementById("card-try-booking");
const btnAttachDummy = document.getElementById("btn-attach-dummy");

// Bookings Ledger Modal Elements
const bookingsModal = document.getElementById("bookings-modal");
const btnCloseModal = document.getElementById("btn-close-modal");
const bookingsTableContainer = document.getElementById("bookings-table-container");
const ledgerSearchInput = document.getElementById("ledger-search-input");
const toastContainer = document.getElementById("toast-container");

// Initialize immediately and also on DOMContentLoaded
function setupAppListeners() {
  initVoiceFeatures();

  if (chatForm) chatForm.onsubmit = handleSendMessage;
  if (btnNewChat) btnNewChat.onclick = handleResetChat;
  if (navBookingsLedger) navBookingsLedger.onclick = openBookingsModal;
  if (btnCloseModal) btnCloseModal.onclick = () => bookingsModal.classList.remove("open");
  
  if (bookingsModal) {
    bookingsModal.onclick = (e) => {
      if (e.target === bookingsModal) bookingsModal.classList.remove("open");
    };
  }

  const micModal = document.getElementById("mic-permission-modal");
  if (micModal) {
    micModal.onclick = (e) => {
      if (e.target === micModal) closeMicPermissionModal();
    };
  }

  if (btnAttachDummy) {
    btnAttachDummy.onclick = () => {
      showToast("Attachment option is a demo dummy feature. Please type your details in chat.");
    };
  }

  if (cardTryBooking) {
    cardTryBooking.onclick = () => {
      chatInput.value = "What is my booking details?";
      chatForm.dispatchEvent(new Event("submit"));
    };
  }

  if (chatInput) {
    chatInput.oninput = () => {
      if (chatInput.value.trim().length > 0) {
        btnSend.classList.add("active");
      } else {
        btnSend.classList.remove("active");
      }
    };

    chatInput.onkeydown = (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        chatForm.dispatchEvent(new Event("submit"));
      }
    };
  }

  if (ledgerSearchInput) {
    ledgerSearchInput.oninput = filterBookingsTable;
  }
}

// Call listeners immediately so buttons are active right away
setupAppListeners();

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => {
    setupAppListeners();
    initializeChat();
  });
} else {
  initializeChat();
}

// ==========================================================================
// CHAT INITIALIZATION & MESSAGING
// ==========================================================================

async function initializeChat() {
  try {
    const res = await fetch("/api/chat/init", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: currentSessionId })
    });
    const data = await res.json();
    currentSessionId = data.session_id;
    localStorage.setItem("northstar_session_id", currentSessionId);
    lastState = data.state;

    // Clear canvas
    chatMessages.innerHTML = "";
    // Only append if session has existing messages; otherwise start completely empty until user says hi!
    if (data.reply && data.reply.trim().length > 0) {
      appendAssistantBubble(data.reply, data.options, data.quick_replies);
    }
  } catch (err) {
    console.error("Init chat error:", err);
    chatMessages.innerHTML = "";
  }
}

async function handleSendMessage(e) {
  if (e) e.preventDefault();
  const text = chatInput.value.trim();
  if (!text) return;

  // Append user message bubble
  appendUserBubble(text);
  chatInput.value = "";
  chatInput.style.height = "auto";
  btnSend.classList.remove("active");
  chatInput.disabled = true;
  btnSend.disabled = true;

  // Show typing indicator
  showTyping(true);

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: currentSessionId,
        message: text
      })
    });

    if (!res.ok) throw new Error("Failed to send message");
    const data = await res.json();

    currentSessionId = data.session_id;
    localStorage.setItem("northstar_session_id", currentSessionId);
    lastState = data.state;

    showTyping(false);
    appendAssistantBubble(data.reply, data.options, data.quick_replies, data.booking, data.audio_base64);
  } catch (err) {
    showTyping(false);
    appendAssistantBubble("Apologies, I encountered a brief network delay. Please try again or rephrase your answer.");
    console.error("Chat error:", err);
  } finally {
    chatInput.disabled = false;
    btnSend.disabled = false;
    chatInput.focus();
    scrollToBottom();
  }
}

async function handleResetChat() {
  try {
    const res = await fetch("/api/chat/reset", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: currentSessionId })
    });
    const data = await res.json();
    currentSessionId = data.session_id;
    localStorage.setItem("northstar_session_id", currentSessionId);
    lastState = data.state;

    // Reset starts completely empty until user sends a greeting
    chatMessages.innerHTML = "";
    if (data.reply && data.reply.trim().length > 0) {
      appendAssistantBubble(data.reply, data.options, data.quick_replies);
    }
    showToast("Conversation cleared. Say 'Hi' to begin.");
  } catch (err) {
    console.error("Reset error:", err);
    chatMessages.innerHTML = "";
  }
}

// ==========================================================================
// MESSAGE BUBBLE RENDERING WITH IN-CHAT OPTION CARDS
// ==========================================================================

function appendUserBubble(text, isVoice = false) {
  const row = document.createElement("div");
  row.className = "user-message-row";
  const voiceIcon = isVoice ? '<span title="Spoken by voice" style="color: #38bdf8; margin-right: 6px;"><i class="fa-solid fa-microphone"></i></span>' : '';
  row.innerHTML = `
    <div class="message-bubble user-bubble">
      ${voiceIcon}${escapeHtml(text)}
    </div>
    <div class="user-avatar">
      <i class="fa-solid fa-user"></i>
    </div>
  `;
  chatMessages.appendChild(row);
  scrollToBottom();
}

function appendAssistantBubble(text, options = null, quickReplies = [], booking = null, audioBase64 = null) {
  const row = document.createElement("div");
  row.className = "assistant-message-row";

  let optionsHtml = "";
  if (options) {
    optionsHtml = renderInChatOptions(options);
  }

  let quickRepliesHtml = "";
  if (quickReplies && quickReplies.length > 0) {
    quickRepliesHtml = `
      <div class="inchat-quick-replies">
        ${quickReplies.map(qr => `
          <button type="button" class="inchat-reply-chip" onclick="handleQuickSelect('${escapeHtml(qr)}')">
            ${escapeHtml(qr)}
          </button>
        `).join("")}
      </div>
    `;
  }

  let voucherHtml = "";
  if (booking) {
    voucherHtml = renderVoucherCard(booking);
  }

  const msgId = "msg-" + Math.random().toString(36).substring(2, 9);

  row.innerHTML = `
    <div class="assistant-avatar">
      <i class="fa-solid fa-robot"></i>
    </div>
    <div class="bubble-wrapper">
      <div class="assistant-header-line">
        <span class="assistant-name">Northstar Assistant</span>
        <span class="assistant-tag">AI</span>
        <button type="button" class="btn-msg-audio" id="audio-btn-${msgId}" title="Listen to response (TTS)" onclick="handleMessageAudioClick(this, '${msgId}')">
          <i class="fa-solid fa-volume-high"></i>
        </button>
      </div>
      <div class="message-bubble assistant-bubble">
        ${formatMarkdown(text)}
        ${voucherHtml}
        ${optionsHtml}
        ${quickRepliesHtml}
      </div>
    </div>
  `;

  // Attach metadata for replay
  row.dataset.msgText = text || "";
  if (audioBase64) {
    row.dataset.audioBase64 = audioBase64;
  }

  chatMessages.appendChild(row);
  scrollToBottom();

  // AT THE SAME TIME: Speak the response via Audio TTS if enabled
  if (ttsEnabled && text && text.trim().length > 0) {
    if (audioBase64) {
      playAudio(audioBase64);
    } else {
      speakViaBrowserTTS(text);
    }
  }
}

// ==========================================================================
// VOICE RECORDING (WHISPER STT) & AUDIO SPEECH (TTS) FUNCTIONS
// ==========================================================================

function initVoiceFeatures() {
  const btnRec = document.getElementById("btn-voice-record");
  const btnRestart = document.getElementById("btn-voice-restart");
  const btnCancel = document.getElementById("btn-voice-cancel");
  const btnStop = document.getElementById("btn-voice-stop");
  const btnTts = document.getElementById("btn-toggle-tts");

  if (btnRec) {
    btnRec.onclick = toggleVoiceRecording;
  }
  if (btnRestart) {
    btnRestart.onclick = restartVoiceRecording;
  }
  if (btnCancel) {
    btnCancel.onclick = cancelVoiceRecording;
  }
  if (btnStop) {
    btnStop.onclick = stopAndSendVoice;
  }
  if (btnTts) {
    btnTts.onclick = toggleTTS;
  }
}

function toggleVoiceRecording() {
  if (isRecording) {
    stopAndSendVoice();
  } else {
    startVoiceRecording();
  }
}
window.toggleVoiceRecording = toggleVoiceRecording;

function toggleTTS() {
  ttsEnabled = !ttsEnabled;
  const btn = document.getElementById("btn-toggle-tts");
  if (ttsEnabled) {
    if (btn) {
      btn.classList.add("active-tts");
      btn.classList.remove("muted");
      btn.title = "Voice Audio Speech (TTS: ON)";
      btn.innerHTML = '<i class="fa-solid fa-volume-high"></i>';
    }
    showToast("Voice Audio Speech enabled (ON)");
  } else {
    if (btn) {
      btn.classList.remove("active-tts");
      btn.classList.add("muted");
      btn.title = "Voice Audio Speech (TTS: MUTED)";
      btn.innerHTML = '<i class="fa-solid fa-volume-xmark"></i>';
    }
    stopCurrentAudio();
    showToast("Voice Audio Speech muted (OFF)");
  }
}
window.toggleTTS = toggleTTS;

function initMediaRecorder(stream) {
  let options = {};
  if (MediaRecorder.isTypeSupported("audio/webm;codecs=opus")) {
    options = { mimeType: "audio/webm;codecs=opus" };
  } else if (MediaRecorder.isTypeSupported("audio/webm")) {
    options = { mimeType: "audio/webm" };
  } else if (MediaRecorder.isTypeSupported("audio/mp4")) {
    options = { mimeType: "audio/mp4" };
  }

  mediaRecorder = new MediaRecorder(stream, options);

  mediaRecorder.ondataavailable = (e) => {
    if (e.data && e.data.size > 0) {
      audioChunks.push(e.data);
    }
  };
}

function startAudioVisualizer(stream) {
  try {
    const AudioCtx = window.AudioContext || window.webkitAudioContext;
    if (!AudioCtx) return;
    audioContext = new AudioCtx();
    if (audioContext.state === "suspended") {
      audioContext.resume().catch(() => {});
    }
    const source = audioContext.createMediaStreamSource(stream);
    audioAnalyser = audioContext.createAnalyser();
    audioAnalyser.fftSize = 64;
    audioAnalyser.smoothingTimeConstant = 0.4;
    source.connect(audioAnalyser);

    const bufferLength = audioAnalyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);
    const bars = document.querySelectorAll(".voice-wave-bars .v-bar");

    function renderWaves() {
      if (!isRecording) return;
      audioVisualizerFrame = requestAnimationFrame(renderWaves);
      audioAnalyser.getByteFrequencyData(dataArray);

      let sum = 0;
      for (let i = 0; i < bufferLength; i++) {
        sum += dataArray[i];
      }
      const avg = sum / bufferLength;
      if (avg > maxAudioVolume) {
        maxAudioVolume = avg;
      }

      bars.forEach((bar, index) => {
        const binIndex = Math.floor((index / bars.length) * (bufferLength / 2));
        const val = dataArray[binIndex] || 0;
        // Dynamically scale height from 6px up to 36px based on real speech energy
        const height = Math.max(6, Math.min(36, Math.round(6 + (val / 160) * 30)));
        bar.style.height = `${height}px`;
        bar.style.opacity = Math.max(0.35, Math.min(1.0, 0.35 + (val / 150) * 0.65)).toFixed(2);
      });
    }

    renderWaves();
  } catch (e) {
    console.warn("Audio visualizer initialization:", e);
  }
}

function stopAudioVisualizer() {
  if (audioVisualizerFrame) {
    cancelAnimationFrame(audioVisualizerFrame);
    audioVisualizerFrame = null;
  }
  if (audioContext) {
    try {
      audioContext.close();
    } catch (e) {}
    audioContext = null;
  }
  audioAnalyser = null;

  // Reset bar heights
  const bars = document.querySelectorAll(".voice-wave-bars .v-bar");
  bars.forEach(bar => {
    bar.style.height = "";
    bar.style.opacity = "";
  });
}

// Microphone Permission Modal Helpers
function showMicPermissionModal(title, subtitle, statusText) {
  const modal = document.getElementById("mic-permission-modal");
  const titleEl = document.getElementById("mic-modal-title");
  const subEl = document.getElementById("mic-modal-subtitle");
  const statusEl = document.getElementById("mic-status-text");

  if (title && titleEl) titleEl.textContent = title;
  if (subtitle && subEl) subEl.textContent = subtitle;
  if (statusText && statusEl) statusEl.textContent = statusText;

  if (modal) modal.classList.add("open");
}
window.showMicPermissionModal = showMicPermissionModal;

function closeMicPermissionModal() {
  const modal = document.getElementById("mic-permission-modal");
  if (modal) modal.classList.remove("open");
}
window.closeMicPermissionModal = closeMicPermissionModal;

function handleRetryMicPermission() {
  closeMicPermissionModal();
  startVoiceRecording();
}
window.handleRetryMicPermission = handleRetryMicPermission;

// Listen to browser permission changes when supported
if (navigator.permissions && navigator.permissions.query) {
  navigator.permissions.query({ name: "microphone" }).then(permissionStatus => {
    permissionStatus.onchange = () => {
      if (permissionStatus.state === "granted") {
        closeMicPermissionModal();
        showToast("Microphone permission granted. You can speak to the assistant!");
      }
    };
  }).catch(() => {});
}

async function startVoiceRecording() {
  // 1. Check for secure context (Browsers block mic on remote plain HTTP)
  const isLocal = location.hostname === "localhost" || location.hostname === "127.0.0.1";
  if (!window.isSecureContext && !isLocal) {
    showMicPermissionModal(
      "HTTPS Connection Required",
      "Browsers block microphone recording over plain HTTP",
      "Modern web browsers (Chrome, Edge, Safari, Firefox) strictly require an HTTPS (SSL) connection or localhost to allow microphone access. Please access via HTTPS or localhost."
    );
    return;
  }

  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    showMicPermissionModal(
      "Microphone Not Supported",
      "Your browser does not support audio recording",
      "Please update your browser to the latest version of Chrome, Edge, Safari, or Firefox."
    );
    return;
  }

  // 2. Open recording overlay UI with Connecting state
  isRecording = true;
  audioChunks = [];
  recordingSeconds = 0;
  maxAudioVolume = 0;

  const overlay = document.getElementById("voice-recording-overlay");
  const form = document.getElementById("chat-form");
  const btnRec = document.getElementById("btn-voice-record");
  const recBadge = document.getElementById("voice-rec-badge");
  const statusText = document.getElementById("voice-rec-status-text");

  if (overlay) {
    overlay.style.display = "flex";
    overlay.classList.remove("live-active");
  }
  if (form) form.style.display = "none";
  if (btnRec) btnRec.classList.add("recording-active");
  if (recBadge) recBadge.classList.add("connecting");
  if (statusText) statusText.textContent = "Connecting mic...";

  updateTimerDisplay();

  // 3. Request microphone access with tuned speech constraints
  const audioConstraints = {
    channelCount: 1,
    sampleRate: { ideal: 16000 },
    echoCancellation: true,
    noiseSuppression: true,
    autoGainControl: true
  };

  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: audioConstraints });
    if (!isRecording) {
      // User cancelled before mic stream opened
      stream.getTracks().forEach(t => t.stop());
      return;
    }
    currentMediaStream = stream;
    initMediaRecorder(stream);
    
    // Gather audio slices every 100ms
    try {
      mediaRecorder.start(100);
    } catch (e) {
      console.warn("MediaRecorder start error:", e);
      mediaRecorder.start();
    }

    // Microphone is now actively recording
    if (overlay) overlay.classList.add("live-active");
    if (recBadge) {
      recBadge.classList.remove("connecting");
      recBadge.classList.remove("processing");
    }
    if (statusText) statusText.textContent = "REC (Speak now)";

    startAudioVisualizer(stream);
    closeMicPermissionModal();

    // Start timer only when microphone hardware is live
    if (recordingTimerInterval) clearInterval(recordingTimerInterval);
    recordingTimerInterval = setInterval(() => {
      recordingSeconds++;
      updateTimerDisplay();
      if (recordingSeconds >= 90) {
        stopAndSendVoice();
      }
    }, 1000);

  } catch (err) {
    console.warn("Microphone access error:", err);
    cleanupRecordingUI();

    if (err.name === "NotAllowedError" || err.name === "PermissionDeniedError") {
      showMicPermissionModal(
        "Microphone Access Denied",
        "Permission was blocked in your browser",
        "Your browser blocked microphone access. Click the lock (🔒) icon in your address bar, set Microphone to 'Allow', then click 'Allow & Try Again'."
      );
    } else if (err.name === "NotFoundError" || err.name === "DevicesNotFoundError") {
      showToast("No microphone device was found on this computer.");
    } else {
      showToast("Could not access microphone: " + (err.message || err.name));
    }
  }
}
window.startVoiceRecording = startVoiceRecording;

function restartVoiceRecording() {
  recordingSeconds = 0;
  maxAudioVolume = 0;
  updateTimerDisplay();
  audioChunks = [];

  if (mediaRecorder) {
    mediaRecorder.onstop = null;
    mediaRecorder.ondataavailable = null;
    try {
      if (mediaRecorder.state !== "inactive") {
        mediaRecorder.stop();
      }
    } catch (e) {}
  }

  if (currentMediaStream) {
    initMediaRecorder(currentMediaStream);
    try {
      mediaRecorder.start(100);
    } catch (e) {
      console.warn("Error restarting MediaRecorder:", e);
    }
  }

  showToast("Recording restarted from 0:00. Speak now...");
}
window.restartVoiceRecording = restartVoiceRecording;

function updateTimerDisplay() {
  const timerElem = document.getElementById("voice-timer");
  if (!timerElem) return;
  const mins = Math.floor(recordingSeconds / 60);
  const secs = recordingSeconds % 60;
  timerElem.textContent = `${mins}:${secs < 10 ? '0' : ''}${secs}`;
}

function cleanupRecordingUI() {
  isRecording = false;
  if (recordingTimerInterval) {
    clearInterval(recordingTimerInterval);
    recordingTimerInterval = null;
  }
  stopAudioVisualizer();

  const overlay = document.getElementById("voice-recording-overlay");
  const form = document.getElementById("chat-form");
  const btnRec = document.getElementById("btn-voice-record");
  const recBadge = document.getElementById("voice-rec-badge");
  const statusText = document.getElementById("voice-rec-status-text");

  if (btnRec) btnRec.classList.remove("recording-active");
  if (overlay) {
    overlay.style.display = "none";
    overlay.classList.remove("live-active");
  }
  if (form) form.style.display = "";
  if (recBadge) {
    recBadge.classList.remove("connecting");
    recBadge.classList.remove("processing");
  }
  if (statusText) statusText.textContent = "REC";
}

function cancelVoiceRecording() {
  if (mediaRecorder && mediaRecorder.state !== "inactive") {
    mediaRecorder.onstop = null;
    try {
      mediaRecorder.stop();
    } catch (e) {}
  }
  if (currentMediaStream) {
    currentMediaStream.getTracks().forEach(track => track.stop());
    currentMediaStream = null;
  }
  audioChunks = [];
  cleanupRecordingUI();
  showToast("Voice recording cancelled.");
}
window.cancelVoiceRecording = cancelVoiceRecording;

async function stopAndSendVoice() {
  if (!isRecording) return;

  const recBadge = document.getElementById("voice-rec-badge");
  const statusText = document.getElementById("voice-rec-status-text");
  if (recBadge) recBadge.classList.add("processing");
  if (statusText) statusText.textContent = "Processing speech...";

  stopAudioVisualizer();

  if (mediaRecorder && mediaRecorder.state !== "inactive") {
    mediaRecorder.onstop = async () => {
      if (currentMediaStream) {
        currentMediaStream.getTracks().forEach(track => track.stop());
        currentMediaStream = null;
      }
      cleanupRecordingUI();

      const totalBytes = audioChunks.reduce((acc, c) => acc + (c.size || 0), 0);
      if (audioChunks.length === 0 || totalBytes < 400) {
        showToast("Recording was too short. Please speak clearly into your mic and try again.");
        return;
      }

      if (maxAudioVolume < 3) {
        showToast("Low or no microphone sound was detected. Please verify your mic is unmuted and speak clearly.");
      }

      const mime = mediaRecorder.mimeType || "audio/webm";
      const audioBlob = new Blob(audioChunks, { type: mime });
      await processVoiceAudioBlob(audioBlob);
    };

    try {
      mediaRecorder.stop();
      return;
    } catch (e) {
      console.warn("Error stopping media recorder:", e);
    }
  }

  // Fallback if mediaRecorder was not running
  if (currentMediaStream) {
    currentMediaStream.getTracks().forEach(track => track.stop());
    currentMediaStream = null;
  }
  cleanupRecordingUI();

  if (audioChunks && audioChunks.length > 0) {
    const audioBlob = new Blob(audioChunks, { type: "audio/webm" });
    await processVoiceAudioBlob(audioBlob);
  } else {
    showToast("No voice recorded. Please allow microphone access to talk with AI.");
  }
}
window.stopAndSendVoice = stopAndSendVoice;

async function processVoiceAudioBlob(blob) {
  showTyping(true);
  chatInput.disabled = true;
  btnSend.disabled = true;

  try {
    const formData = new FormData();
    const ext = blob.type.includes("mp4") ? "mp4" : "webm";
    formData.append("audio", blob, `voice_recording.${ext}`);
    if (currentSessionId) {
      formData.append("session_id", currentSessionId);
    }

    const res = await fetch("/api/voice/chat", {
      method: "POST",
      body: formData
    });

    if (!res.ok) {
      throw new Error(`Voice server error: ${res.status}`);
    }

    const data = await res.json();

    if (!data.success) {
      showTyping(false);
      showToast(data.message || "Could not transcribe audio. Please try speaking again.");
      return;
    }

    // 1. Show user transcribed text in chat bubble with microphone icon
    appendUserBubble(data.user_text, true);

    // 2. Update session
    currentSessionId = data.session_id;
    localStorage.setItem("northstar_session_id", currentSessionId);
    lastState = data.state;

    // 3. Render Assistant reply bubble with cards & quick replies
    showTyping(false);
    appendAssistantBubble(data.reply, data.options, data.quick_replies, data.booking, data.audio_base64);

  } catch (err) {
    showTyping(false);
    console.error("Voice processing error:", err);
    appendAssistantBubble("Sorry, I encountered an error processing your voice recording. Please check your mic or try typing your message.");
  } finally {
    chatInput.disabled = false;
    btnSend.disabled = false;
    chatInput.focus();
    scrollToBottom();
  }
}

// Audio Playback Helpers
function playAudio(audioDataUri, onEndCallback = null) {
  stopCurrentAudio();
  try {
    currentAudioPlayer = new Audio(audioDataUri);
    currentAudioPlayer.onended = () => {
      currentAudioPlayer = null;
      if (onEndCallback) onEndCallback();
    };
    currentAudioPlayer.onerror = (e) => {
      console.warn("Audio playback error:", e);
      currentAudioPlayer = null;
      if (onEndCallback) onEndCallback();
    };
    currentAudioPlayer.play().catch(err => {
      console.warn("Autoplay was prevented by browser policy:", err);
      currentAudioPlayer = null;
      if (onEndCallback) onEndCallback();
    });
  } catch (e) {
    console.warn("playAudio failed:", e);
    currentAudioPlayer = null;
    if (onEndCallback) onEndCallback();
  }
}

function stopCurrentAudio() {
  if (currentAudioPlayer) {
    try {
      currentAudioPlayer.pause();
      currentAudioPlayer.currentTime = 0;
    } catch (e) {}
    currentAudioPlayer = null;
  }
  if (window.speechSynthesis) {
    window.speechSynthesis.cancel();
  }
}

function speakViaBrowserTTS(text) {
  if (!window.speechSynthesis) return;
  stopCurrentAudio();
  try {
    const clean = text
      .replace(/[*_#`~]/g, '')
      .replace(/https?:\/\/\S+/g, '')
      .replace(/[\u{10000}-\u{10ffff}]/gu, '')
      .replace(/[\u2000-\u3300]/gu, '')
      .replace(/[•\-\*\+]/g, '')
      .trim();
    const utterance = new SpeechSynthesisUtterance(clean.substring(0, 320));
    utterance.rate = 1.0;
    utterance.pitch = 1.0;
    window.speechSynthesis.speak(utterance);
  } catch (e) {
    console.warn("Browser speech synthesis error:", e);
  }
}

window.handleMessageAudioClick = async function(btn, msgId) {
  const row = btn.closest(".assistant-message-row");
  if (!row) return;

  if (btn.classList.contains("playing")) {
    stopCurrentAudio();
    btn.classList.remove("playing");
    btn.innerHTML = '<i class="fa-solid fa-volume-high"></i>';
    return;
  }

  // Reset any other playing buttons
  document.querySelectorAll(".btn-msg-audio.playing").forEach(b => {
    b.classList.remove("playing");
    b.innerHTML = '<i class="fa-solid fa-volume-high"></i>';
  });

  btn.classList.add("playing");
  btn.innerHTML = '<i class="fa-solid fa-circle-stop"></i>';

  const resetBtn = () => {
    btn.classList.remove("playing");
    btn.innerHTML = '<i class="fa-solid fa-volume-high"></i>';
  };

  const audioBase64 = row.dataset.audioBase64;
  const text = row.dataset.msgText || "";

  if (audioBase64) {
    playAudio(audioBase64, resetBtn);
  } else {
    try {
      const res = await fetch(`/api/voice/tts?text=${encodeURIComponent(text.substring(0, 320))}`);
      if (res.ok) {
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        playAudio(url, () => {
          URL.revokeObjectURL(url);
          resetBtn();
        });
      } else {
        speakViaBrowserTTS(text);
        setTimeout(resetBtn, 4000);
      }
    } catch (e) {
      speakViaBrowserTTS(text);
      setTimeout(resetBtn, 4000);
    }
  }
};

// Render Interactive Option Cards directly inside Assistant message
function renderInChatOptions(options) {
  if (!options || !options.type) return "";

  // 1. Destination Cards
  if (options.type === "locations" && options.items) {
    return `
      <div class="in-chat-options-container">
        <div class="options-title-bar">
          <i class="fa-solid fa-plane-arrival"></i> Available Arrival Airport Hubs:
        </div>
        <div class="destinations-grid">
          ${options.items.map(loc => `
            <div class="inchat-dest-card" onclick="handleQuickSelect('${escapeHtml(loc.city)}')">
              <div class="inchat-dest-badge">
                <i class="fa-solid fa-plane-arrival"></i>
                <span>${escapeHtml(loc.airport_code)}</span>
              </div>
              <div class="inchat-dest-info">
                <span class="inchat-dest-city">${escapeHtml(loc.city)}</span>
                <span class="inchat-dest-airport">${escapeHtml(loc.airport_name)}</span>
              </div>
            </div>
          `).join("")}
        </div>
      </div>
    `;
  }

  // 2. Hotel Cards
  if (options.type === "hotels" && options.items) {
    return `
      <div class="in-chat-options-container">
        <div class="options-title-bar">
          <i class="fa-solid fa-hotel"></i> Available Properties in ${escapeHtml(options.location_city || 'City')}:
        </div>
        <div class="hotels-cards-list">
          ${options.items.map(h => `
            <div class="inchat-hotel-card" onclick="handleQuickSelect('${escapeHtml(h.name)}')">
              <img src="${h.image_url || 'https://images.unsplash.com/photo-1566073771259-6a8506099945?auto=format&fit=crop&w=600&q=80'}" alt="${escapeHtml(h.name)}" class="inchat-hotel-img" loading="lazy">
              <div class="inchat-hotel-details">
                <div class="inchat-hotel-header">
                  <span class="inchat-hotel-name">${escapeHtml(h.name)}</span>
                  <span class="inchat-hotel-rating">⭐ ${h.rating || 4.8}</span>
                </div>
                <span class="inchat-hotel-address"><i class="fa-solid fa-location-dot"></i> ${escapeHtml(h.address)}</span>
                <div class="inchat-hotel-footer">
                  <span class="inchat-btn-select">Select this hotel <i class="fa-solid fa-arrow-right"></i></span>
                </div>
              </div>
            </div>
          `).join("")}
        </div>
      </div>
    `;
  }

  // 3. Room Type Cards
  if (options.type === "rooms" && options.items) {
    return `
      <div class="in-chat-options-container">
        <div class="options-title-bar">
          <i class="fa-solid fa-bed"></i> Available Room Options${options.hotel_name ? ` at ${escapeHtml(options.hotel_name)}` : ''}:
        </div>
        <div class="rooms-cards-list">
          ${options.items.map(r => `
            <div class="inchat-room-card" onclick="handleQuickSelect('${escapeHtml(r.name)}')">
              <div class="inchat-room-thumb-box">
                <img src="${r.image_url || 'https://images.unsplash.com/photo-1590490360182-c33d57733427?auto=format&fit=crop&w=600&q=80'}" alt="${escapeHtml(r.name)}" class="inchat-room-thumb" loading="lazy">
                ${r.badge ? `<span class="inchat-room-badge">${escapeHtml(r.badge)}</span>` : ''}
              </div>
              <div class="inchat-room-body">
                <div class="inchat-room-title-row">
                  <span class="inchat-room-name">${escapeHtml(r.name)}</span>
                  <span class="inchat-room-price">$${Math.round(r.price_per_night || 0)}/nt</span>
                </div>
                <div class="inchat-room-meta">
                  <span class="inchat-meta-pill"><i class="fa-solid fa-user-group"></i> Up to ${r.capacity_per_room || 2} guests</span>
                </div>
                <div class="inchat-hotel-footer" style="margin-top: 6px;">
                  <span class="inchat-btn-select">Select this room <i class="fa-solid fa-arrow-right"></i></span>
                </div>
              </div>
            </div>
          `).join("")}
        </div>
      </div>
    `;
  }

  // Food & Dining Option Cards
  if (options.type === "food" && options.items) {
    return `
      <div class="in-chat-options-container">
        <div class="options-title-bar">
          <i class="fa-solid fa-utensils"></i> Food & Dining Preference:
        </div>
        <div class="vehicles-grid">
          ${options.items.map(f => `
            <div class="inchat-vehicle-card" onclick="handleQuickSelect('${escapeHtml(f.title)}')">
              <div class="vehicle-header-row">
                <span class="vehicle-title">${escapeHtml(f.title)}</span>
                <span class="vehicle-badge">${escapeHtml(f.badge || '')}</span>
              </div>
              <p class="vehicle-desc">${escapeHtml(f.desc || '')}</p>
            </div>
          `).join("")}
        </div>
      </div>
    `;
  }

  // 4. Vehicle Transfer Option Cards
  if (options.type === "vehicles" && options.items) {
    return `
      <div class="in-chat-options-container">
        <div class="options-title-bar">
          <i class="fa-solid fa-car-side"></i> Airport Transportation Options:
        </div>
        <div class="vehicles-grid">
          ${options.items.map(v => `
            <div class="inchat-vehicle-card" onclick="handleQuickSelect('${escapeHtml(v.title)}')">
              <div class="vehicle-header-row">
                <span class="vehicle-title">${escapeHtml(v.title)}</span>
                <span class="vehicle-badge">${escapeHtml(v.badge || '')}</span>
              </div>
              <p class="vehicle-desc">${escapeHtml(v.desc || '')}</p>
            </div>
          `).join("")}
        </div>
      </div>
    `;
  }

  // 5. Typo Clarification Card ("Did you mean Chennai? Is Chennai right?")
  if (options.type === "clarification") {
    return `
      <div class="in-chat-options-container">
        <div class="inchat-clarify-card">
          <span class="clarify-text">
            <i class="fa-solid fa-circle-question"></i> ${escapeHtml(options.title || 'Did you mean this?')}
          </span>
          <div class="clarify-actions">
            <button type="button" class="btn-clarify-yes" onclick="handleQuickSelect('${escapeHtml(options.confirm_value || options.confirm_text)}')">
              ${escapeHtml(options.confirm_text || 'Yes, correct')}
            </button>
            <button type="button" class="btn-clarify-no" onclick="handleQuickSelect('${escapeHtml(options.cancel_text || 'No, choose another')}')">
              ${escapeHtml(options.cancel_text || 'No')}
            </button>
          </div>
        </div>
      </div>
    `;
  }

  // 6. Confirmation Options
  if (options.type === "confirmation" && options.items) {
    return `
      <div class="in-chat-options-container">
        <div class="inchat-clarify-card" style="display: flex; gap: 10px; justify-content: flex-start; padding: 10px 14px; background: transparent; border: none;">
          ${options.items.map(it => `
            <button type="button" class="${it.primary ? 'btn-clarify-yes' : 'btn-clarify-no'}" onclick="handleQuickSelect('${escapeHtml(it.label)}')">
              ${escapeHtml(it.label)}
            </button>
          `).join("")}
        </div>
      </div>
    `;
  }

  return "";
}

// Render Confirmed Booking Voucher Card
function renderVoucherCard(b) {
  const pickup = b.airport_pickup ? "✅ Yes (Arrival)" : "❌ No";
  const drop = b.airport_drop ? "✅ Yes (Departure)" : "❌ No";
  return `
    <div class="inchat-voucher-card">
      <div class="voucher-header">
        <span class="voucher-brand"><i class="fa-solid fa-plane-up"></i> NORTHSTAR AIR SERVICE</span>
        <span class="voucher-tag">CONFIRMED • ${b.booking_id}</span>
      </div>
      <div class="voucher-details-grid">
        <div class="voucher-row">
          <span class="voucher-label">Property</span>
          <span class="voucher-val">${escapeHtml(b.hotel_name || 'Grand Azure')}</span>
        </div>
        <div class="voucher-row">
          <span class="voucher-label">Destination</span>
          <span class="voucher-val">${escapeHtml(b.location_city || 'City')} (${escapeHtml(b.airport_code || 'Hub')})</span>
        </div>
        <div class="voucher-row">
          <span class="voucher-label">Guest / Org</span>
          <span class="voucher-val">${escapeHtml(b.guest_name || 'Guest')}</span>
        </div>
        <div class="voucher-row">
          <span class="voucher-label">Rooms</span>
          <span class="voucher-val">${b.rooms_count || 1} x ${escapeHtml(b.room_name || 'Room')}</span>
        </div>
        <div class="voucher-row">
          <span class="voucher-label">Dates</span>
          <span class="voucher-val">${b.checkin_date} to ${b.checkout_date}</span>
        </div>
        <div class="voucher-row">
          <span class="voucher-label">Total Amount</span>
          <span class="voucher-val" style="color: #0d9488; font-size: 14px; font-weight: 800;">$${b.total_amount}</span>
        </div>
        <div class="voucher-row">
          <span class="voucher-label">Food / Dining</span>
          <span class="voucher-val">${escapeHtml(b.food_preference || (b.food_included ? 'Yes, Food Included' : 'No Food (Room Only)'))}</span>
        </div>
        <div class="voucher-row">
          <span class="voucher-label">Airport Pick-up</span>
          <span class="voucher-val">${pickup}</span>
        </div>
        <div class="voucher-row">
          <span class="voucher-label">Airport Drop-off</span>
          <span class="voucher-val">${drop}</span>
        </div>
      </div>
    </div>
  `;
}

// Global click handler for in-chat cards and quick reply chips
window.handleQuickSelect = function(text) {
  chatInput.value = text;
  chatForm.dispatchEvent(new Event("submit"));
};

// ==========================================================================
// BOOKINGS LEDGER MODAL MANAGEMENT
// ==========================================================================

async function openBookingsModal() {
  bookingsModal.classList.add("open");
  bookingsTableContainer.innerHTML = `
    <div style="text-align: center; padding: 24px; color: #64748b;">
      <i class="fa-solid fa-spinner fa-spin" style="font-size: 20px; color: #0d9488;"></i>
      <p style="margin-top: 8px;">Loading reservations from MongoDB...</p>
    </div>
  `;

  try {
    const res = await fetch("/api/bookings");
    if (!res.ok) throw new Error("Failed to fetch bookings");
    const data = await res.json();
    cachedBookings = data.bookings || [];
    renderBookingsTable(cachedBookings);
  } catch (err) {
    bookingsTableContainer.innerHTML = `
      <div style="text-align: center; padding: 20px; color: #ef4444;">
        Failed to load bookings ledger.
      </div>
    `;
  }
}

function renderBookingsTable(bookings) {
  if (bookings.length === 0) {
    bookingsTableContainer.innerHTML = `
      <div style="text-align: center; padding: 30px; color: #94a3b8;">
        <i class="fa-regular fa-folder-open" style="font-size: 28px; margin-bottom: 8px;"></i>
        <p>No bookings currently recorded in MongoDB.</p>
      </div>
    `;
    return;
  }

  bookingsTableContainer.innerHTML = `
    <table class="ledger-table">
      <thead>
        <tr>
          <th>Reference</th>
          <th>Guest / Org</th>
          <th>Hotel & Hub</th>
          <th>Dates</th>
          <th>Rooms</th>
          <th>Vehicle</th>
          <th>Total</th>
          <th>Action</th>
        </tr>
      </thead>
      <tbody>
        ${bookings.map(b => {
          const v = (b.airport_pickup && b.airport_drop) ? "Both" : (b.airport_pickup ? "Pick-up" : (b.airport_drop ? "Drop-off" : "None"));
          return `
            <tr id="booking-row-${b.booking_id}">
              <td><strong style="color: #0d9488;">${b.booking_id}</strong></td>
              <td>
                <div style="font-weight: 600;">${escapeHtml(b.guest_name || 'Guest')}</div>
                <div style="font-size: 10px; color: #94a3b8;">${escapeHtml(b.contact_email || b.contact_phone || '')}</div>
              </td>
              <td>
                <div style="font-weight: 600;">${escapeHtml(b.hotel_name || 'Grand Azure')}</div>
                <div style="font-size: 10px; color: #94a3b8;">${escapeHtml(b.location_city || '')} (${escapeHtml(b.airport_code || '')})</div>
              </td>
              <td>${b.checkin_date} to ${b.checkout_date}</td>
              <td>
                <div>${b.rooms_count} x ${escapeHtml(b.room_name || 'Room')}</div>
                <div style="font-size: 10px; color: #64748b; margin-top: 2px;"><i class="fa-solid fa-utensils"></i> ${escapeHtml(b.food_preference || (b.food_included ? 'Food Included' : 'No Food'))}</div>
              </td>
              <td><span class="status-tag confirmed">${v}</span></td>
              <td><strong>$${b.total_amount}</strong></td>
              <td>
                <button type="button" class="btn-delete-booking" onclick="deleteBookingEntry('${b.booking_id}')">
                  <i class="fa-solid fa-trash-can"></i> Delete
                </button>
              </td>
            </tr>
          `;
        }).join("")}
      </tbody>
    </table>
  `;
}

function filterBookingsTable() {
  const query = ledgerSearchInput.value.toLowerCase().trim();
  if (!query) {
    renderBookingsTable(cachedBookings);
    return;
  }
  const filtered = cachedBookings.filter(b => {
    return (
      (b.booking_id && b.booking_id.toLowerCase().includes(query)) ||
      (b.guest_name && b.guest_name.toLowerCase().includes(query)) ||
      (b.hotel_name && b.hotel_name.toLowerCase().includes(query)) ||
      (b.location_city && b.location_city.toLowerCase().includes(query)) ||
      (b.contact_email && b.contact_email.toLowerCase().includes(query))
    );
  });
  renderBookingsTable(filtered);
}

window.deleteBookingEntry = async function(bookingId) {
  if (!confirm(`Are you sure you want to permanently delete reservation ${bookingId}?`)) {
    return;
  }

  try {
    const res = await fetch(`/api/bookings/${bookingId}`, {
      method: "DELETE"
    });
    if (!res.ok) throw new Error("Delete failed");

    cachedBookings = cachedBookings.filter(b => b.booking_id !== bookingId);
    filterBookingsTable();
    showToast(`Booking ${bookingId} deleted successfully.`);
  } catch (err) {
    showToast("Failed to delete booking.");
  }
};

// ==========================================================================
// UTILITY HELPERS
// ==========================================================================

function showTyping(show) {
  if (typingIndicator) {
    typingIndicator.style.display = show ? "flex" : "none";
    if (show) scrollToBottom();
  }
}

function scrollToBottom() {
  if (chatCanvas) {
    setTimeout(() => {
      chatCanvas.scrollTop = chatCanvas.scrollHeight;
    }, 50);
  }
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function formatMarkdown(text) {
  if (!text) return "";
  let html = escapeHtml(text);

  // Bold **text**
  html = html.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");

  // Inline code `code`
  html = html.replace(/`([^`]+)`/g, "<code style='background: #f1f5f9; padding: 2px 4px; border-radius: 4px; font-size: 12px;'>$1</code>");

  // Lists: • or -
  html = html.replace(/^[•\-\*]\s+(.*)$/gm, "<li>$1</li>");
  html = html.replace(/(<li>.*<\/li>)/s, "<ul style='margin: 6px 0 6px 18px;'>$1</ul>");

  // Paragraph breaks
  html = html.replace(/\n\n+/g, "</p><p>");
  html = html.replace(/\n/g, "<br>");

  return `<p>${html}</p>`;
}

function showToast(message) {
  if (!toastContainer) return;
  const t = document.createElement("div");
  t.className = "toast";
  t.textContent = message;
  toastContainer.appendChild(t);
  setTimeout(() => {
    t.style.opacity = "0";
    setTimeout(() => t.remove(), 250);
  }, 2800);
}
