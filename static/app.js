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
const voiceRecordingBar = document.getElementById("voice-recording-bar");
const voiceTimer = document.getElementById("voice-timer");
const btnVoiceCancel = document.getElementById("btn-voice-cancel");
const btnVoiceOk = document.getElementById("btn-voice-ok");
const btnToggleTts = document.getElementById("btn-toggle-tts");

// Voice & Audio State
let mediaRecorder = null;
let audioChunks = [];
let recordingTimerInterval = null;
let recordingSeconds = 0;
let isRecording = false;
let ttsEnabled = true; // Auto-speech ON by default
let currentAudioPlayer = null;

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

// Initialize on Load
document.addEventListener("DOMContentLoaded", async () => {
  await initializeChat();
  initVoiceFeatures();

  // Attach Event Listeners
  chatForm.addEventListener("submit", handleSendMessage);
  btnNewChat.addEventListener("click", handleResetChat);
  navBookingsLedger.addEventListener("click", openBookingsModal);
  btnCloseModal.addEventListener("click", () => bookingsModal.classList.remove("open"));
  
  // Close modal when clicking outside
  bookingsModal.addEventListener("click", (e) => {
    if (e.target === bookingsModal) bookingsModal.classList.remove("open");
  });

  // Dummy attachment handler
  if (btnAttachDummy) {
    btnAttachDummy.addEventListener("click", () => {
      showToast("Attachment option is a demo dummy feature. Please type your details in chat.");
    });
  }

  // Try an existing booking sample card
  if (cardTryBooking) {
    cardTryBooking.addEventListener("click", () => {
      chatInput.value = "What is my booking details?";
      chatForm.dispatchEvent(new Event("submit"));
    });
  }

  // Input changes toggle send button state
  chatInput.addEventListener("input", () => {
    if (chatInput.value.trim().length > 0) {
      btnSend.classList.add("active");
    } else {
      btnSend.classList.remove("active");
    }
  });

  // Support Enter to submit (Shift+Enter for new line)
  chatInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      chatForm.dispatchEvent(new Event("submit"));
    }
  });

  // Live filter for bookings ledger
  if (ledgerSearchInput) {
    ledgerSearchInput.addEventListener("input", filterBookingsTable);
  }
});

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
  if (btnVoiceRecord) {
    btnVoiceRecord.addEventListener("click", () => {
      if (isRecording) {
        stopAndSendVoice();
      } else {
        startVoiceRecording();
      }
    });
  }

  if (btnVoiceOk) {
    btnVoiceOk.addEventListener("click", stopAndSendVoice);
  }

  if (btnVoiceCancel) {
    btnVoiceCancel.addEventListener("click", cancelVoiceRecording);
  }

  if (btnToggleTts) {
    btnToggleTts.addEventListener("click", () => {
      ttsEnabled = !ttsEnabled;
      if (ttsEnabled) {
        btnToggleTts.classList.add("active-tts");
        btnToggleTts.classList.remove("muted");
        btnToggleTts.title = "Voice Audio Speech (TTS: ON)";
        btnToggleTts.innerHTML = '<i class="fa-solid fa-volume-high"></i>';
        showToast("Voice Audio Speech enabled (ON)");
      } else {
        btnToggleTts.classList.remove("active-tts");
        btnToggleTts.classList.add("muted");
        btnToggleTts.title = "Voice Audio Speech (TTS: MUTED)";
        btnToggleTts.innerHTML = '<i class="fa-solid fa-volume-xmark"></i>';
        stopCurrentAudio();
        showToast("Voice Audio Speech muted (OFF)");
      }
    });
  }
}

async function startVoiceRecording() {
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    showToast("Microphone access is not supported by your browser.");
    return;
  }

  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    audioChunks = [];

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

    mediaRecorder.start(200);
    isRecording = true;

    // UI Updates
    btnVoiceRecord.classList.add("recording-active");
    if (voiceRecordingBar) voiceRecordingBar.style.display = "flex";
    if (btnSend) btnSend.style.display = "none";
    recordingSeconds = 0;
    updateTimerDisplay();

    recordingTimerInterval = setInterval(() => {
      recordingSeconds++;
      updateTimerDisplay();
      if (recordingSeconds >= 60) {
        stopAndSendVoice();
      }
    }, 1000);

  } catch (err) {
    console.error("Microphone access error:", err);
    showToast("Could not access microphone. Please allow microphone permission in browser.");
  }
}

function updateTimerDisplay() {
  if (!voiceTimer) return;
  const mins = Math.floor(recordingSeconds / 60);
  const secs = recordingSeconds % 60;
  voiceTimer.textContent = `${mins}:${secs < 10 ? '0' : ''}${secs}`;
}

function cleanupRecordingUI() {
  isRecording = false;
  if (recordingTimerInterval) {
    clearInterval(recordingTimerInterval);
    recordingTimerInterval = null;
  }
  if (btnVoiceRecord) btnVoiceRecord.classList.remove("recording-active");
  if (voiceRecordingBar) voiceRecordingBar.style.display = "none";
  if (btnSend) btnSend.style.display = "";
}

function cancelVoiceRecording() {
  if (mediaRecorder && mediaRecorder.state !== "inactive") {
    mediaRecorder.onstop = null;
    mediaRecorder.stop();
    mediaRecorder.stream.getTracks().forEach(track => track.stop());
  }
  audioChunks = [];
  cleanupRecordingUI();
  showToast("Voice recording cancelled.");
}

async function stopAndSendVoice() {
  if (!mediaRecorder || mediaRecorder.state === "inactive") return;

  mediaRecorder.onstop = async () => {
    mediaRecorder.stream.getTracks().forEach(track => track.stop());

    if (audioChunks.length === 0) {
      cleanupRecordingUI();
      showToast("No voice audio was captured.");
      return;
    }

    const mime = mediaRecorder.mimeType || "audio/webm";
    const audioBlob = new Blob(audioChunks, { type: mime });
    cleanupRecordingUI();

    await processVoiceAudioBlob(audioBlob);
  };

  mediaRecorder.stop();
}

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
    });
  } catch (e) {
    console.warn("playAudio failed:", e);
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
      .replace(/[\U00010000-\U0010ffff]/gu, '')
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
