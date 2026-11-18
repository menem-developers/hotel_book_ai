// ==========================================================================
// NORTHSTAR AIR SERVICE - CONVERSATIONAL AGENT JAVASCRIPT
// Handles in-chat interactive cards, typo clarifications, and dummy attachment
// ==========================================================================

let currentSessionId = localStorage.getItem("northstar_session_id") || null;
let currentLanguage = localStorage.getItem("northstar_language") || "en";
let lastState = null;
let cachedBookings = [];

// Multilingual Configurations for English, Hindi, and Spanish
const LANG_CONFIG = {
  en: {
    flag: "🇬🇧",
    shortName: "English",
    name: "English",
    voice: "en-US-AriaNeural",
    browserVoice: "en-US",
    placeholder: "Reply to the assistant (Type or click mic)...",
    tag: "Voice & Text",
    disclaimer: "AI responses can be inaccurate. Confirm bookings and policy with an authorized agent.",
    greeting: "Hello and welcome! 🌟 I'm your **Northstar AI Assistant**. How can I assist you today?",
    toast: "Language set to English (Neural Voice: Aria)"
  },
  hi: {
    flag: "🇮🇳",
    shortName: "हिन्दी",
    name: "हिन्दी (Hindi)",
    voice: "hi-IN-SwaraNeural",
    browserVoice: "hi-IN",
    placeholder: "सहायक को उत्तर दें (टाइप करें या माइक दबाएं)...",
    tag: "वॉयस और टेक्स्ट",
    disclaimer: "एआई प्रतिक्रियाएं सांकेतिक हो सकती हैं। कृपया अपनी बुकिंग की पुष्टि करें।",
    greeting: "नमस्ते और स्वागत है! 🌟 मैं आपकी **नॉर्थस्टार AI सहायक** हूँ। आज मैं आपकी क्या सहायता कर सकती हूँ?",
    toast: "भाषा हिन्दी सेट की गई (Swara Neural आवाज़ सक्रिय)"
  },
  es: {
    flag: "🇪🇸",
    shortName: "Español",
    name: "Español (Spanish)",
    voice: "es-ES-ElviraNeural",
    browserVoice: "es-ES",
    placeholder: "Responda al asistente (Escriba o use el micrófono)...",
    tag: "Voz y Texto",
    disclaimer: "Las respuestas de IA pueden ser aproximadas. Confirme sus reservas con un agente autorizado.",
    greeting: "¡Hola y bienvenido! 🌟 Soy tu **asistente de Northstar AI**. ¿En qué puedo ayudarte hoy?",
    toast: "Idioma cambiado a Español (Voz Neural Elvira activa)"
  }
};

function applyLanguageUI(lang) {
  if (!LANG_CONFIG[lang]) lang = "en";
  currentLanguage = lang;
  localStorage.setItem("northstar_language", lang);

  const cfg = LANG_CONFIG[lang];

  // Sync navbar dropdown button
  const flagEl = document.getElementById("current-lang-flag");
  if (flagEl) flagEl.textContent = cfg.flag;
  const nameEl = document.getElementById("current-lang-name");
  if (nameEl) nameEl.textContent = cfg.shortName || cfg.name;

  // Sync dropdown menu active state
  document.querySelectorAll(".lang-menu-item").forEach(item => item.classList.remove("active"));
  const activeItem = document.getElementById(`lang-item-${lang}`);
  if (activeItem) activeItem.classList.add("active");

  if (chatInput) chatInput.placeholder = cfg.placeholder;
  const channelTag = document.getElementById("channel-tag");
  if (channelTag) channelTag.textContent = cfg.tag;
  const disclaimerEl = document.getElementById("chat-disclaimer");
  if (disclaimerEl) disclaimerEl.textContent = cfg.disclaimer;
}

function toggleLangDropdown(e) {
  if (e) {
    e.stopPropagation();
    e.preventDefault();
  }
  const menu = document.getElementById("lang-dropdown-menu");
  const btn = document.getElementById("lang-dropdown-btn");
  if (!menu) return;
  const isOpen = menu.classList.contains("open");
  if (isOpen) {
    menu.classList.remove("open");
    if (btn) {
      btn.classList.remove("open");
      btn.setAttribute("aria-expanded", "false");
    }
  } else {
    menu.classList.add("open");
    if (btn) {
      btn.classList.add("open");
      btn.setAttribute("aria-expanded", "true");
    }
  }
}

function closeLangDropdown() {
  const menu = document.getElementById("lang-dropdown-menu");
  const btn = document.getElementById("lang-dropdown-btn");
  if (menu) menu.classList.remove("open");
  if (btn) {
    btn.classList.remove("open");
    btn.setAttribute("aria-expanded", "false");
  }
}

window.toggleLangDropdown = toggleLangDropdown;
window.closeLangDropdown = closeLangDropdown;
window.chooseLanguage = function(lang) {
  closeLangDropdown();
  selectLanguage(lang, true);
};

// Close dropdown on click outside
document.addEventListener("click", function(e) {
  const wrapper = document.getElementById("lang-dropdown-wrapper");
  if (wrapper && !wrapper.contains(e.target)) {
    closeLangDropdown();
  }
});

// Close dropdown on Escape key
document.addEventListener("keydown", function(e) {
  if (e.key === "Escape") {
    closeLangDropdown();
  }
});

async function selectLanguage(lang, triggerGreeting = true) {
  if (!LANG_CONFIG[lang]) lang = "en";
  applyLanguageUI(lang);
  const cfg = LANG_CONFIG[lang];
  showToast(cfg.toast);

  if (triggerGreeting) {
    showTyping(true);
    try {
      const res = await fetch("/api/chat/init", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: currentSessionId,
          language: lang,
          tts_enabled: isNavbarSpeakEnabled()
        })
      });
      showTyping(false);
      if (res.ok) {
        const data = await res.json();
        currentSessionId = data.session_id;
        localStorage.setItem("northstar_session_id", currentSessionId);
        lastState = data.state;
        chatMessages.innerHTML = "";
        appendAssistantBubble(data.reply, data.options, data.quick_replies, null, data.audio_base64);
      } else {
        chatMessages.innerHTML = "";
        appendAssistantBubble(cfg.greeting, null, ["🏨 Book a Hotel", "🌤️ Check Today's Weather", "✨ How can you assist me?"]);
      }
    } catch (e) {
      showTyping(false);
      chatMessages.innerHTML = "";
      appendAssistantBubble(cfg.greeting, null, ["🏨 Book a Hotel", "🌤️ Check Today's Weather", "✨ How can you assist me?"]);
    }
  }
}
window.selectLanguage = selectLanguage;
window.changeLanguage = function(val) {
  selectLanguage(val, true);
};

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
const savedTtsPref = localStorage.getItem("northstar_tts_enabled");
let ttsEnabled = savedTtsPref !== null ? savedTtsPref === "true" : true; // Persist user voice speech preference
let currentAudioPlayer = null;

// ==========================================================================
// REAL-TIME AUDIO STATE MANAGEMENT SYSTEM
// Required 4 Canonical States: IDLE, LISTENING, PROCESSING, SPEAKING
// Workflow: LISTENING -> PROCESSING -> SPEAKING -> IDLE -> LISTENING
// ==========================================================================
const AUDIO_STATE = {
  IDLE: "IDLE",
  LISTENING: "LISTENING",
  PROCESSING: "PROCESSING",
  SPEAKING: "SPEAKING"
};

let currentAudioState = AUDIO_STATE.IDLE;
const POST_TTS_DELAY_MS = 400; // Configurable post-playback delay (300-500ms)
let postTtsDelayTimer = null;

// ChatGPT-style Continuous Hands-Free Voice Conversation State
let isContinuousVoiceMode = false;
let voiceSilenceMasterInterval = null;
let lastVoiceActivityTime = 0;
let hasSpokenInTurn = false;
let activeVoiceAbortController = null;
let lastAssistantResponseText = "";

function isNavbarSpeakEnabled() {
  const saved = localStorage.getItem("northstar_tts_enabled");
  if (saved !== null) {
    ttsEnabled = (saved === "true");
  } else {
    const btn = document.getElementById("btn-toggle-tts");
    if (btn) {
      if (btn.classList.contains("muted")) {
        ttsEnabled = false;
      } else if (btn.classList.contains("active-tts")) {
        ttsEnabled = true;
      }
    }
  }
  return !!ttsEnabled;
}
window.isNavbarSpeakEnabled = isNavbarSpeakEnabled;

function updateTtsButtonUI() {
  const isEnabled = isNavbarSpeakEnabled();
  const btn = document.getElementById("btn-toggle-tts");
  if (btn) {
    if (isEnabled) {
      btn.classList.add("active-tts");
      btn.classList.remove("muted");
      btn.setAttribute("aria-pressed", "true");
      btn.title = "Voice Audio Speech: ENABLED (Click to mute and switch to text-only)";
      btn.innerHTML = '<i class="fa-solid fa-volume-high"></i>';
    } else {
      btn.classList.remove("active-tts");
      btn.classList.add("muted");
      btn.setAttribute("aria-pressed", "false");
      btn.title = "Voice Audio Speech: MUTED / OFF (Click to enable AI voice)";
      btn.innerHTML = '<i class="fa-solid fa-volume-xmark"></i>';
    }
  }

  // Toggle body class for CSS suppression of audio buttons
  if (typeof document !== "undefined" && document.body) {
    document.body.classList.toggle("tts-muted", !isEnabled);
  }

  // Synchronize all message audio buttons across the chat canvas
  if (typeof document !== "undefined") {
    document.querySelectorAll(".btn-msg-audio").forEach(el => {
      el.style.display = isEnabled ? "inline-flex" : "none";
      if (!isEnabled) {
        el.classList.remove("playing");
        el.innerHTML = '<i class="fa-solid fa-volume-high"></i>';
      }
    });
  }
}
window.updateTtsButtonUI = updateTtsButtonUI;
let audioContext = null;
let audioAnalyser = null;
let audioVisualizerFrame = null;
let maxAudioVolume = 0;
let ambientNoiseBaseline = 0;

// High-accuracy live in-browser speech recognition (Human Voice Only)
let browserSpeechRecognition = null;
let liveTranscribedSpeech = "";
let accumulatedFinalText = "";

function startBrowserSpeechRecognition() {
  if (!isContinuousVoiceMode) return;
  const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRec) {
    console.warn("SpeechRecognition API not supported in this browser. Fallback VAD will be used.");
    return;
  }
  try {
    if (browserSpeechRecognition) {
      browserSpeechRecognition.onend = null;
      browserSpeechRecognition.onerror = null;
      browserSpeechRecognition.onresult = null;
      browserSpeechRecognition.onspeechstart = null;
      browserSpeechRecognition.onspeechend = null;
      try { browserSpeechRecognition.abort(); } catch (e) {}
      browserSpeechRecognition = null;
    }
    browserSpeechRecognition = new SpeechRec();
    browserSpeechRecognition.continuous = true;
    browserSpeechRecognition.interimResults = true;
    const localeMap = { "hi": "hi-IN", "es": "es-ES", "en": "en-US" };
    browserSpeechRecognition.lang = localeMap[currentLanguage] || "en-US";
    liveTranscribedSpeech = "";
    accumulatedFinalText = "";

    // Fired ONLY when acoustic model detects human speech (ignores fan noise & room sounds)
    browserSpeechRecognition.onspeechstart = () => {
      if (!isContinuousVoiceMode) return;
      // CRITICAL: Block speaker audio feedback during PROCESSING, SPEAKING, and IDLE
      if (currentAudioState !== AUDIO_STATE.LISTENING) {
        console.log(`[Voice] Ignored speech start during ${currentAudioState} state.`);
        return;
      }
      console.log("[Voice] Human speech onset detected by SpeechRecognition.");
      handleBargeInInterruption();
    };

    // Fired when human speech stops
    browserSpeechRecognition.onspeechend = () => {
      if (!isContinuousVoiceMode) return;
      if (currentAudioState !== AUDIO_STATE.LISTENING) return;
      console.log("[Voice] Human speech ended detected by SpeechRecognition (3s pause countdown eligible).");
      // Intentionally do NOT update lastVoiceActivityTime so the silence watcher counts 3s
    };

    browserSpeechRecognition.onresult = (event) => {
      if (!isContinuousVoiceMode && !isRecording) return;
      // CRITICAL: Strictly ignore any speech recognition results unless actively in LISTENING state
      if (currentAudioState !== AUDIO_STATE.LISTENING) {
        console.log(`[Voice] Ignored speech recognition result during ${currentAudioState} state.`);
        return;
      }

      let currentFinal = "";
      let currentInterim = "";
      for (let i = event.resultIndex; i < event.results.length; ++i) {
        if (event.results[i].isFinal) {
          accumulatedFinalText += event.results[i][0].transcript + " ";
        } else {
          currentInterim += event.results[i][0].transcript;
        }
      }

      const combined = (accumulatedFinalText + currentInterim).trim();

      // Only true human speech creates non-empty transcripts (fan/ambient sound is ignored)
      if (combined && combined.length > 0) {
        liveTranscribedSpeech = combined;
        lastVoiceActivityTime = Date.now();
        hasSpokenInTurn = true;

        // Barge-in: if AI was speaking, interrupt immediately!
        handleBargeInInterruption();

        setAudioState(AUDIO_STATE.LISTENING, combined);
      }
    };

    browserSpeechRecognition.onerror = (e) => {
      if (e.error !== "no-speech" && e.error !== "aborted") {
        console.warn("Browser SpeechRecognition notice:", e.error);
      }
    };

    // Auto-revive recognition if browser closes session during continuous hands-free mode
    browserSpeechRecognition.onend = () => {
      console.log("[Voice] SpeechRecognition onend fired. isContinuousVoiceMode =", isContinuousVoiceMode, "state =", currentAudioState);
      if (isContinuousVoiceMode && currentAudioState === AUDIO_STATE.LISTENING) {
        setTimeout(() => {
          if (isContinuousVoiceMode && currentAudioState === AUDIO_STATE.LISTENING) {
            ensureSpeechRecognitionActive();
          }
        }, 80);
      }
    };

    browserSpeechRecognition.start();
  } catch (e) {
    console.warn("SpeechRecognition start exception:", e);
  }
}

function stopBrowserSpeechRecognition() {
  if (browserSpeechRecognition) {
    browserSpeechRecognition.onend = null;
    browserSpeechRecognition.onspeechstart = null;
    browserSpeechRecognition.onspeechend = null;
    browserSpeechRecognition.onresult = null;
    try {
      browserSpeechRecognition.abort();
    } catch (e) {}
    browserSpeechRecognition = null;
  }
}

function ensureSpeechRecognitionActive() {
  if (!isContinuousVoiceMode || currentAudioState !== AUDIO_STATE.LISTENING) return;
  const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRec) return;

  if (!browserSpeechRecognition) {
    startBrowserSpeechRecognition();
    return;
  }

  try {
    browserSpeechRecognition.start();
  } catch (err) {
    // If it threw because recognition is already running, that's fine (InvalidStateError)
    // Otherwise, recreate instance
    if (err.name !== "InvalidStateError") {
      startBrowserSpeechRecognition();
    }
  }
}

function ensureMediaRecorderActive() {
  if (!isContinuousVoiceMode || !currentMediaStream || currentAudioState !== AUDIO_STATE.LISTENING) return;

  if (!mediaRecorder || mediaRecorder.state === "inactive") {
    console.log("[Voice] Re-activating MediaRecorder for next turn.");
    initMediaRecorder(currentMediaStream);
    try {
      mediaRecorder.start(100);
    } catch (e) {
      try { mediaRecorder.start(); } catch (e2) {}
    }
  } else if (mediaRecorder.state === "paused") {
    try {
      mediaRecorder.resume();
    } catch (e) {}
  }
}

// --------------------------------------------------------------------------
// Audio Lifecycle Transition: SPEAKING -> IDLE -> LISTENING
// --------------------------------------------------------------------------
function transitionAfterTTS() {
  if (!isContinuousVoiceMode) {
    setAudioState(AUDIO_STATE.IDLE);
    return;
  }

  console.log(`[AudioLifecycle] Assistant playback complete. Entering IDLE state with ${POST_TTS_DELAY_MS}ms quiet window.`);

  // 1. Workflow step: SPEAKING -> IDLE
  setAudioState(AUDIO_STATE.IDLE);

  // 2. Clear or discard buffered audio captured during TTS playback
  audioChunks = [];
  liveTranscribedSpeech = "";
  accumulatedFinalText = "";
  hasSpokenInTurn = false;
  lastVoiceActivityTime = 0;

  if (postTtsDelayTimer) {
    clearTimeout(postTtsDelayTimer);
  }

  // 3. Post-playback quiet delay (default 400ms) for room reverb & speaker sound to dissipate
  postTtsDelayTimer = setTimeout(() => {
    postTtsDelayTimer = null;
    if (!isContinuousVoiceMode) return;

    // Reset audio buffers once more before resuming LISTENING
    audioChunks = [];
    liveTranscribedSpeech = "";
    accumulatedFinalText = "";
    hasSpokenInTurn = false;
    lastVoiceActivityTime = 0;

    // 4. Workflow step: IDLE -> LISTENING
    setAudioState(AUDIO_STATE.LISTENING);

    // 5. Resume microphone processing: start fresh speech recognition & ensure recorder is active
    startBrowserSpeechRecognition();
    ensureMediaRecorderActive();
    console.log("[AudioLifecycle] Completed full cycle: SPEAKING -> IDLE -> LISTENING. Ready for next human speech.");
  }, POST_TTS_DELAY_MS);
}
window.transitionAfterTTS = transitionAfterTTS;
const handleAssistantVoiceFinished = transitionAfterTTS; // backwards-compatible alias

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
  updateTtsButtonUI();

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

// ==========================================================================
// AUTHENTICATION LOGIC (ADMIN LOGIN / LOGOUT)
// ==========================================================================
function checkAuthState() {
  const token = localStorage.getItem("northstar_auth_token");
  if (!token) {
    showLoginScreen();
  } else {
    showDashboardScreen();
    initializeChat();
  }
}

function showLoginScreen() {
  const loginPage = document.getElementById("login-page-container");
  const appContainer = document.getElementById("app-container");
  if (loginPage) loginPage.style.display = "flex";
  if (appContainer) appContainer.style.display = "none";
  const userInp = document.getElementById("login-username");
  const passInp = document.getElementById("login-password");
  if (userInp) {
    userInp.value = "";
    setTimeout(() => userInp.focus(), 100);
  }
  if (passInp) {
    passInp.value = "";
  }
  const err = document.getElementById("login-error-alert");
  if (err) err.style.display = "none";
}

function showDashboardScreen() {
  const loginPage = document.getElementById("login-page-container");
  const appContainer = document.getElementById("app-container");
  if (loginPage) loginPage.style.display = "none";
  if (appContainer) appContainer.style.display = "flex";
  applyLanguageUI(currentLanguage);
}

function togglePasswordVisibility() {
  const pwd = document.getElementById("login-password");
  const icon = document.getElementById("password-eye-icon");
  if (!pwd) return;
  if (pwd.type === "password") {
    pwd.type = "text";
    if (icon) {
      icon.classList.remove("fa-eye");
      icon.classList.add("fa-eye-slash");
    }
  } else {
    pwd.type = "password";
    if (icon) {
      icon.classList.remove("fa-eye-slash");
      icon.classList.add("fa-eye");
    }
  }
}

async function handleLoginSubmit(e) {
  if (e) e.preventDefault();
  const usernameInput = document.getElementById("login-username");
  const passwordInput = document.getElementById("login-password");
  const alertEl = document.getElementById("login-error-alert");
  const alertText = document.getElementById("login-error-text");
  const btnSubmit = document.getElementById("btn-login-submit");
  const btnText = document.getElementById("btn-login-text");
  const btnIcon = document.getElementById("btn-login-icon");
  const btnSpinner = document.getElementById("btn-login-spinner");

  const username = usernameInput ? usernameInput.value.trim() : "";
  const password = passwordInput ? passwordInput.value.trim() : "";

  if (!username || !password) {
    if (alertEl) {
      alertEl.style.display = "flex";
      if (alertText) alertText.textContent = "Please enter both username and password.";
    }
    return;
  }

  // Set loading state
  if (btnSubmit) btnSubmit.disabled = true;
  if (btnText) btnText.textContent = "Verifying...";
  if (btnIcon) btnIcon.style.display = "none";
  if (btnSpinner) btnSpinner.style.display = "inline-block";
  if (alertEl) alertEl.style.display = "none";

  try {
    const res = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password })
    });
    const data = await res.json();

    if (res.ok && data.success) {
      localStorage.setItem("northstar_auth_token", data.token || "nstar_authenticated");
      localStorage.setItem("northstar_auth_user", data.username || "admin");

      showToast("Signed in successfully as Administrator.");

      // Check for redirect param
      const urlParams = new URLSearchParams(window.location.search);
      const redirectUrl = urlParams.get("redirect");
      if (redirectUrl && redirectUrl.startsWith("/")) {
        window.location.href = redirectUrl;
        return;
      }

      showDashboardScreen();
      initializeChat();
    } else {
      if (alertEl) {
        alertEl.style.display = "flex";
        if (alertText) alertText.textContent = data.detail || data.message || "Invalid username or password. Please try again.";
      }
    }
  } catch (err) {
    console.error("Login request error:", err);
    if (alertEl) {
      alertEl.style.display = "flex";
      if (alertText) alertText.textContent = "Connection error. Please check server and try again.";
    }
  } finally {
    if (btnSubmit) btnSubmit.disabled = false;
    if (btnText) btnText.textContent = "Sign in to Dashboard";
    if (btnIcon) btnIcon.style.display = "inline-block";
    if (btnSpinner) btnSpinner.style.display = "none";
  }
}

async function handleLogout() {
  const token = localStorage.getItem("northstar_auth_token");
  try {
    if (token) {
      await fetch("/api/auth/logout", {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${token}`
        }
      });
    }
  } catch (err) {
    console.warn("Logout error:", err);
  }

  localStorage.removeItem("northstar_auth_token");
  localStorage.removeItem("northstar_auth_user");
  showLoginScreen();
  showToast("Logged out successfully.");
}

window.togglePasswordVisibility = togglePasswordVisibility;
window.handleLoginSubmit = handleLoginSubmit;
window.handleLogout = handleLogout;
window.checkAuthState = checkAuthState;
window.showLoginScreen = showLoginScreen;
window.showDashboardScreen = showDashboardScreen;

// Call listeners immediately so buttons are active right away
setupAppListeners();

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => {
    setupAppListeners();
    checkAuthState();
  });
} else {
  checkAuthState();
}

// ==========================================================================
// CHAT INITIALIZATION & MESSAGING
// ==========================================================================

async function initializeChat() {
  applyLanguageUI(currentLanguage);

  try {
    const res = await fetch("/api/chat/init", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: currentSessionId,
        language: currentLanguage,
        tts_enabled: isNavbarSpeakEnabled()
      })
    });
    const data = await res.json();
    currentSessionId = data.session_id;
    localStorage.setItem("northstar_session_id", currentSessionId);
    lastState = data.state;

    // Clear canvas and render wish message only
    chatMessages.innerHTML = "";
    appendAssistantBubble(data.reply, data.options, data.quick_replies, null, data.audio_base64);
  } catch (err) {
    console.error("Init chat error:", err);
    chatMessages.innerHTML = "";
    const cfg = LANG_CONFIG[currentLanguage] || LANG_CONFIG.en;
    appendAssistantBubble(cfg.greeting, null, ["🏨 Book a Hotel", "🌤️ Check Today's Weather", "✨ How can you assist me?"]);
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
    const speakEnabled = isNavbarSpeakEnabled();
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: currentSessionId,
        message: text,
        language: currentLanguage,
        tts_enabled: speakEnabled
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
    const errText = currentLanguage === "hi" 
      ? "क्षमा करें, नेटवर्क में देरी हुई है। कृपया पुनः प्रयास करें।"
      : (currentLanguage === "es" 
        ? "Lo sentimos, hubo un retraso de red. Por favor intente de nuevo."
        : "Apologies, I encountered a brief network delay. Please try again.");
    appendAssistantBubble(errText);
    console.error("Chat error:", err);
  } finally {
    chatInput.disabled = false;
    btnSend.disabled = false;
    chatInput.focus();
    scrollToBottom();
  }
}

async function handleResetChat() {
  showTyping(true);
  try {
    const res = await fetch("/api/chat/reset", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: currentSessionId,
        language: currentLanguage,
        tts_enabled: isNavbarSpeakEnabled()
      })
    });
    showTyping(false);
    const data = await res.json();
    currentSessionId = data.session_id;
    localStorage.setItem("northstar_session_id", currentSessionId);
    lastState = data.state;

    // Clear canvas and render wish message only
    chatMessages.innerHTML = "";
    appendAssistantBubble(data.reply, data.options, data.quick_replies, null, data.audio_base64);
    showToast("Started fresh conversation.");
  } catch (err) {
    showTyping(false);
    console.error("Reset error:", err);
    chatMessages.innerHTML = "";
    const cfg = LANG_CONFIG[currentLanguage] || LANG_CONFIG.en;
    appendAssistantBubble(cfg.greeting, null, ["🏨 Book a Hotel", "🌤️ Check Today's Weather", "✨ How can you assist me?"]);
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

function appendAssistantBubble(text, options = null, quickReplies = [], booking = null, audioBase64 = null, onVoiceCompleteCallback = null) {
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
  const speakOn = isNavbarSpeakEnabled();

  row.innerHTML = `
    <div class="assistant-avatar">
      <i class="fa-solid fa-robot"></i>
    </div>
    <div class="bubble-wrapper">
      <div class="assistant-header-line">
        <span class="assistant-name">Northstar Assistant</span>
        <span class="assistant-tag">AI</span>
        <button type="button" class="btn-msg-audio" id="audio-btn-${msgId}" title="Listen to response (TTS)" onclick="handleMessageAudioClick(this, '${msgId}')" style="display: ${speakOn ? 'inline-flex' : 'none'};">
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

  // Attach metadata for replay ONLY if voice is enabled
  row.dataset.msgText = text || "";
  lastAssistantResponseText = (text || "").toLowerCase();
  if (speakOn && audioBase64) {
    row.dataset.audioBase64 = audioBase64;
  }

  chatMessages.appendChild(row);
  scrollToBottom();

  // AT THE SAME TIME: Speak the response via Audio TTS ONLY if navbar speak button is enabled
  if (speakOn && text && text.trim().length > 0) {
    playTTSWithLifecycle(audioBase64, text, () => {
      if (typeof onVoiceCompleteCallback === "function") {
        onVoiceCompleteCallback();
      } else if (isContinuousVoiceMode) {
        transitionAfterTTS();
      }
    });
  } else {
    // If navbar speak is muted/disabled, ensure any running audio is stopped immediately
    stopCurrentAudio();
    if (typeof onVoiceCompleteCallback === "function") {
      setTimeout(onVoiceCompleteCallback, 200);
    } else if (isContinuousVoiceMode) {
      transitionAfterTTS();
    }
  }
}

// ==========================================================================
// CHATGPT-STYLE CONTINUOUS HANDS-FREE VOICE CONVERSATION ENGINE
// ==========================================================================

function initVoiceFeatures() {
  const btnRec = document.getElementById("btn-voice-record");
  const btnRestart = document.getElementById("btn-voice-restart");
  const btnCancel = document.getElementById("btn-voice-cancel");
  const btnStop = document.getElementById("btn-voice-stop");
  const btnSendNow = document.getElementById("btn-voice-send-now");
  const btnTts = document.getElementById("btn-toggle-tts");

  if (btnRec) {
    btnRec.onclick = toggleVoiceRecording;
  }
  if (btnRestart) {
    btnRestart.onclick = restartVoiceRecording;
  }
  if (btnCancel) {
    btnCancel.onclick = stopContinuousVoiceMode;
  }
  if (btnStop) {
    btnStop.onclick = stopContinuousVoiceMode;
  }
  if (btnSendNow) {
    btnSendNow.onclick = triggerImmediateSend;
  }
  if (btnTts) {
    btnTts.onclick = toggleTTS;
  }
}

function toggleVoiceRecording() {
  if (isContinuousVoiceMode || isRecording) {
    stopContinuousVoiceMode();
  } else {
    startContinuousVoiceMode();
  }
}
window.toggleVoiceRecording = toggleVoiceRecording;

function toggleTTS() {
  const currentlyActive = isNavbarSpeakEnabled();
  ttsEnabled = !currentlyActive;
  localStorage.setItem("northstar_tts_enabled", ttsEnabled ? "true" : "false");
  updateTtsButtonUI();
  if (ttsEnabled) {
    showToast("Voice Mode enabled! Continuous hands-free conversation active (ChatGPT Style).");
    if (!isContinuousVoiceMode) {
      startContinuousVoiceMode();
    }
  } else {
    stopCurrentAudio();
    if (isContinuousVoiceMode) {
      stopContinuousVoiceMode();
    }
    showToast("Voice Audio Speech muted (OFF) - Direct text mode");
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
    // CRITICAL: Strictly drop all incoming audio chunks unless actively in LISTENING state
    if (currentAudioState !== AUDIO_STATE.LISTENING) {
      return;
    }
    if (e.data && e.data.size > 0) {
      audioChunks.push(e.data);
    }
  };
}

function handleBargeInInterruption() {
  let wasInterrupted = false;

  if (postTtsDelayTimer) {
    clearTimeout(postTtsDelayTimer);
    postTtsDelayTimer = null;
  }

  // 1. Immediately cut off playing assistant audio
  if (currentAudioPlayer) {
    stopCurrentAudio();
    wasInterrupted = true;
  }

  // 2. Immediately cancel browser speech synthesis
  if (window.speechSynthesis && (window.speechSynthesis.speaking || window.speechSynthesis.pending)) {
    window.speechSynthesis.cancel();
    wasInterrupted = true;
  }

  // 3. Immediately abort any in-flight response request
  if (activeVoiceAbortController) {
    activeVoiceAbortController.abort();
    activeVoiceAbortController = null;
    showTyping(false);
    wasInterrupted = true;
  }

  // 4. Reset playing button animations on messages
  document.querySelectorAll(".btn-msg-audio.playing").forEach(b => {
    b.classList.remove("playing");
    b.innerHTML = '<i class="fa-solid fa-volume-high"></i>';
  });

  if (wasInterrupted) {
    console.log("[Voice] Barge-in: interrupted assistant speech in real time.");
  }
}

function setAudioState(state, previewText = "", countdownSecs = 3) {
  currentAudioState = state;
  console.log(`[AudioState] -> ${state}`);

  const recBadge = document.getElementById("voice-rec-badge");
  const statusText = document.getElementById("voice-rec-status-text");
  if (!recBadge || !statusText) return;

  recBadge.className = "voice-rec-badge";

  switch (state) {
    case AUDIO_STATE.IDLE:
      recBadge.classList.add("idle");
      statusText.innerHTML = '<i class="fa-solid fa-pause"></i> Ready (Mic Paused)';
      break;

    case AUDIO_STATE.LISTENING:
      if (previewText) {
        recBadge.classList.add("hearing");
        const snippet = previewText.slice(-24);
        statusText.innerHTML = `<i class="fa-solid fa-microphone-lines"></i> Hearing you "${snippet}"`;
      } else if (countdownSecs < 3) {
        recBadge.classList.add("countdown");
        statusText.innerHTML = `<i class="fa-solid fa-hourglass-half"></i> Sending in ${countdownSecs}s...`;
      } else {
        recBadge.classList.add("listening");
        statusText.innerHTML = '<i class="fa-solid fa-ear-listen"></i> Listening (Speak anytime)...';
      }
      break;

    case AUDIO_STATE.PROCESSING:
      recBadge.classList.add("processing");
      statusText.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Processing speech...';
      break;

    case AUDIO_STATE.SPEAKING:
      recBadge.classList.add("speaking");
      statusText.innerHTML = '<i class="fa-solid fa-volume-high"></i> AI Speaking (Muted mic)';
      break;

    default:
      recBadge.classList.add("idle");
      statusText.textContent = state;
  }
}
window.setAudioState = setAudioState;

function setVoiceState(state, previewText = "", countdownSecs = 3) {
  if (state === "AI_SPEAKING") {
    setAudioState(AUDIO_STATE.SPEAKING, previewText, countdownSecs);
  } else if (state === "SENDING") {
    setAudioState(AUDIO_STATE.PROCESSING, previewText, countdownSecs);
  } else if (state === "USER_SPEAKING" || state === "PAUSE_COUNTDOWN" || state === "LISTENING") {
    setAudioState(AUDIO_STATE.LISTENING, previewText, countdownSecs);
  } else if (state === "CONNECTING") {
    currentAudioState = AUDIO_STATE.IDLE;
    const recBadge = document.getElementById("voice-rec-badge");
    const statusText = document.getElementById("voice-rec-status-text");
    if (recBadge && statusText) {
      recBadge.className = "voice-rec-badge connecting";
      statusText.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Connecting mic...';
    }
  } else {
    setAudioState(AUDIO_STATE.IDLE, previewText, countdownSecs);
  }
}
window.setVoiceState = setVoiceState;

let silenceWatcherTickCount = 0;

function startVoiceSilenceWatcher() {
  stopVoiceSilenceWatcher();
  silenceWatcherTickCount = 0;

  voiceSilenceMasterInterval = setInterval(() => {
    if (!isContinuousVoiceMode) {
      stopVoiceSilenceWatcher();
      return;
    }

    // CRITICAL: Only monitor silence and countdown while in LISTENING state
    if (currentAudioState !== AUDIO_STATE.LISTENING) {
      return;
    }

    silenceWatcherTickCount++;
    // Every ~1 second while in LISTENING, ensure recognition is running for user's next turn
    if (silenceWatcherTickCount % 10 === 0) {
      ensureSpeechRecognitionActive();
      ensureMediaRecorderActive();
    }

    // If user has not spoken yet in this turn, keep in LISTENING
    if (!hasSpokenInTurn) {
      return;
    }

    // The user has spoken! Calculate silence elapsed since the last detected speech:
    const silenceElapsed = Date.now() - lastVoiceActivityTime;

    if (silenceElapsed >= 3000) {
      // EXACTLY 3.0s OF SILENCE (NO HUMAN SPOKE) -> AUTO-SEND TURN HANDS-FREE!
      console.log(`[Voice] 3.0s pause reached (${silenceElapsed}ms). Auto-submitting speech turn!`);
      autoSendContinuousVoiceTurn();
    } else if (silenceElapsed >= 400) {
      // User paused speaking; countdown: 3s -> 2s -> 1s
      const secsLeft = Math.max(1, Math.ceil((3000 - silenceElapsed) / 1000));
      setAudioState(AUDIO_STATE.LISTENING, liveTranscribedSpeech, secsLeft);
    } else {
      // User is actively speaking
      setAudioState(AUDIO_STATE.LISTENING, liveTranscribedSpeech);
    }
  }, 100);
}

function stopVoiceSilenceWatcher() {
  if (voiceSilenceMasterInterval) {
    clearInterval(voiceSilenceMasterInterval);
    voiceSilenceMasterInterval = null;
  }
}

function triggerImmediateSend() {
  if (!isContinuousVoiceMode) return;
  console.log("[Voice] User triggered immediate send.");
  autoSendContinuousVoiceTurn();
}
window.triggerImmediateSend = triggerImmediateSend;

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
    audioAnalyser.smoothingTimeConstant = 0.35;
    source.connect(audioAnalyser);

    const bufferLength = audioAnalyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);
    const bars = document.querySelectorAll(".voice-wave-bars .v-bar");

    function renderWaves() {
      if (!isContinuousVoiceMode && !isRecording) return;
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

      // Visualizer bars bounce to show microphone is active
      bars.forEach((bar, index) => {
        const binIndex = Math.floor((index / bars.length) * (bufferLength / 2));
        const val = dataArray[binIndex] || 0;
        const height = Math.max(6, Math.min(36, Math.round(6 + (val / 160) * 30)));
        bar.style.height = `${height}px`;
        bar.style.opacity = Math.max(0.35, Math.min(1.0, 0.35 + (val / 150) * 0.65)).toFixed(2);
      });

      // Adaptive Noise Tracking (Used strictly as fallback when browser has no SpeechRecognition API)
      // When SpeechRecognition is active, it handles human voice phoneme detection exclusively,
      // ensuring fan sounds, air conditioning, and room ambient noises never block pause or auto-send.
      const hasNativeSpeechRec = !!(window.SpeechRecognition || window.webkitSpeechRecognition);
      if (!hasNativeSpeechRec && isContinuousVoiceMode) {
        if (ambientNoiseBaseline === 0) {
          ambientNoiseBaseline = avg;
        } else {
          // Track room background noise / fan hum
          ambientNoiseBaseline = ambientNoiseBaseline * 0.98 + avg * 0.02;
        }

        // Only count as human speech if audio surges substantially above the steady fan baseline
        if (avg > ambientNoiseBaseline + 25 && avg > 32) {
          lastVoiceActivityTime = Date.now();
          hasSpokenInTurn = true;
          handleBargeInInterruption();

          if (voiceConversationState !== "USER_SPEAKING") {
            setVoiceState("USER_SPEAKING", liveTranscribedSpeech);
          }
        }
      }
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

  const bars = document.querySelectorAll(".voice-wave-bars .v-bar");
  bars.forEach(bar => {
    bar.style.height = "";
    bar.style.opacity = "";
  });
}

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
  startContinuousVoiceMode();
}
window.handleRetryMicPermission = handleRetryMicPermission;

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

async function startContinuousVoiceMode() {
  const isLocal = location.hostname === "localhost" || location.hostname === "127.0.0.1";
  if (!window.isSecureContext && !isLocal) {
    showMicPermissionModal(
      "HTTPS Connection Required",
      "Browsers block microphone recording over plain HTTP",
      "Modern web browsers strictly require an HTTPS (SSL) connection or localhost to allow microphone access. Please access via HTTPS or localhost."
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

  // Ensure speech output is enabled so user hears AI voice response
  ttsEnabled = true;
  localStorage.setItem("northstar_tts_enabled", "true");
  updateTtsButtonUI();

  isContinuousVoiceMode = true;
  isRecording = true;
  audioChunks = [];
  recordingSeconds = 0;
  maxAudioVolume = 0;
  hasSpokenInTurn = false;
  liveTranscribedSpeech = "";
  accumulatedFinalText = "";
  ambientNoiseBaseline = 0;
  lastVoiceActivityTime = 0;

  const overlay = document.getElementById("voice-recording-overlay");
  const form = document.getElementById("chat-form");
  const btnRec = document.getElementById("btn-voice-record");

  if (overlay) {
    overlay.style.display = "flex";
    overlay.classList.remove("live-active");
  }
  if (form) form.style.display = "none";
  if (btnRec) btnRec.classList.add("recording-active");

  setVoiceState("CONNECTING");
  updateTimerDisplay();

  const audioConstraints = {
    channelCount: 1,
    sampleRate: { ideal: 16000 },
    echoCancellation: true,
    noiseSuppression: true,
    autoGainControl: true
  };

  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: audioConstraints });
    if (!isContinuousVoiceMode) {
      stream.getTracks().forEach(t => t.stop());
      return;
    }

    currentMediaStream = stream;
    initMediaRecorder(stream);

    try {
      mediaRecorder.start(100);
    } catch (e) {
      console.warn("MediaRecorder start error:", e);
      mediaRecorder.start();
    }

    if (overlay) overlay.classList.add("live-active");
    startAudioVisualizer(stream);
    startBrowserSpeechRecognition();
    closeMicPermissionModal();

    setAudioState(AUDIO_STATE.LISTENING);
    startVoiceSilenceWatcher();

    if (recordingTimerInterval) clearInterval(recordingTimerInterval);
    recordingTimerInterval = setInterval(() => {
      recordingSeconds++;
      updateTimerDisplay();
    }, 1000);

    showToast("🎙️ ChatGPT Voice Mode active! Speak anytime — automatically sends after a 3s pause.");

  } catch (err) {
    console.warn("Microphone access error:", err);
    stopContinuousVoiceMode();

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
window.startContinuousVoiceMode = startContinuousVoiceMode;
window.startVoiceRecording = startContinuousVoiceMode; // alias for backwards compatibility

function stopContinuousVoiceMode() {
  if (postTtsDelayTimer) {
    clearTimeout(postTtsDelayTimer);
    postTtsDelayTimer = null;
  }
  isContinuousVoiceMode = false;
  isRecording = false;
  hasSpokenInTurn = false;
  liveTranscribedSpeech = "";
  accumulatedFinalText = "";
  ambientNoiseBaseline = 0;
  lastVoiceActivityTime = 0;
  stopVoiceSilenceWatcher();

  if (activeVoiceAbortController) {
    activeVoiceAbortController.abort();
    activeVoiceAbortController = null;
  }

  stopCurrentAudio();

  if (recordingTimerInterval) {
    clearInterval(recordingTimerInterval);
    recordingTimerInterval = null;
  }

  stopAudioVisualizer();
  stopBrowserSpeechRecognition();

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

  const overlay = document.getElementById("voice-recording-overlay");
  const form = document.getElementById("chat-form");
  const btnRec = document.getElementById("btn-voice-record");

  if (btnRec) btnRec.classList.remove("recording-active");
  if (overlay) {
    overlay.style.display = "none";
    overlay.classList.remove("live-active");
  }
  if (form) form.style.display = "";

  setAudioState(AUDIO_STATE.IDLE);
  showToast("Exited ChatGPT voice mode. Direct text input restored.");
}
window.stopContinuousVoiceMode = stopContinuousVoiceMode;
window.cancelVoiceRecording = stopContinuousVoiceMode; // alias
window.stopAndSendVoice = triggerImmediateSend; // alias

function restartVoiceRecording() {
  if (postTtsDelayTimer) {
    clearTimeout(postTtsDelayTimer);
    postTtsDelayTimer = null;
  }
  recordingSeconds = 0;
  maxAudioVolume = 0;
  hasSpokenInTurn = false;
  liveTranscribedSpeech = "";
  accumulatedFinalText = "";
  ambientNoiseBaseline = 0;
  audioChunks = [];
  lastVoiceActivityTime = 0;
  startVoiceSilenceWatcher();
  updateTimerDisplay();
  setAudioState(AUDIO_STATE.LISTENING);
  showToast("Recording reset to 0:00. Listening...");
}
window.restartVoiceRecording = restartVoiceRecording;

function updateTimerDisplay() {
  const timerElem = document.getElementById("voice-timer");
  if (!timerElem) return;
  const mins = Math.floor(recordingSeconds / 60);
  const secs = recordingSeconds % 60;
  timerElem.textContent = `${mins}:${secs < 10 ? '0' : ''}${secs}`;
}

async function autoSendContinuousVoiceTurn() {
  if (!isContinuousVoiceMode) return;
  // Guard against calling while already PROCESSING, SPEAKING, or in post-TTS IDLE
  if (currentAudioState === AUDIO_STATE.PROCESSING || currentAudioState === AUDIO_STATE.SPEAKING || currentAudioState === AUDIO_STATE.IDLE) {
    console.warn(`[Voice] autoSendContinuousVoiceTurn rejected: already in ${currentAudioState} state.`);
    return;
  }

  // Flush any pending audio slice from MediaRecorder
  if (mediaRecorder && mediaRecorder.state === "recording") {
    try {
      mediaRecorder.requestData();
    } catch (e) {}
  }

  const textToSend = (liveTranscribedSpeech || accumulatedFinalText || "").trim();
  const chunksToSend = audioChunks.slice();

  // Reset speech buffers for this upcoming turn
  hasSpokenInTurn = false;
  liveTranscribedSpeech = "";
  accumulatedFinalText = "";
  audioChunks = [];
  lastVoiceActivityTime = 0;

  // HUMAN VOICE VALIDATION:
  // If SpeechRecognition is supported in browser, require that human words were actually transcribed.
  // Ambient room sounds, fan hum, or background noises produce empty text — so we stay silent in LISTENING.
  const hasNativeSpeechRec = !!(window.SpeechRecognition || window.webkitSpeechRecognition);
  if (hasNativeSpeechRec && (!textToSend || textToSend.length < 2)) {
    console.log("[Voice] No human words detected in turn (fan/ambient sound rejected). Staying silent in LISTENING.");
    setAudioState(AUDIO_STATE.LISTENING);
    return;
  }

  // If no native speech recognition API is available on browser, ensure audio chunks exist
  if (!hasNativeSpeechRec && !textToSend && chunksToSend.length === 0) {
    setAudioState(AUDIO_STATE.LISTENING);
    return;
  }

  // ECHO FEEDBACK GUARD:
  // Reject if the captured text is just an echo of the assistant's own response coming out of the speakers
  if (lastAssistantResponseText && textToSend) {
    const cleanUser = textToSend.toLowerCase().replace(/[^a-z0-9]/g, '');
    const cleanAi = lastAssistantResponseText.replace(/[^a-z0-9]/g, '');
    if (cleanUser.length > 8 && cleanAi.includes(cleanUser)) {
      console.warn("[Voice] Discarded speaker audio feedback echo:", textToSend);
      setAudioState(AUDIO_STATE.LISTENING);
      hasSpokenInTurn = false;
      liveTranscribedSpeech = "";
      accumulatedFinalText = "";
      audioChunks = [];
      lastVoiceActivityTime = 0;
      return;
    }
  }

  // Workflow transition: LISTENING -> PROCESSING
  setAudioState(AUDIO_STATE.PROCESSING);
  showTyping(true);

  // Stop browser speech recognition so no interim events fire during fetch
  stopBrowserSpeechRecognition();
  activeVoiceAbortController = new AbortController();

  try {
    const formData = new FormData();
    const mime = mediaRecorder ? (mediaRecorder.mimeType || "audio/webm") : "audio/webm";
    const ext = mime.includes("mp4") ? "mp4" : "webm";
    const audioBlob = chunksToSend.length > 0 ? new Blob(chunksToSend, { type: mime }) : new Blob(["dummy"], { type: "audio/webm" });

    formData.append("audio", audioBlob, `voice_recording.${ext}`);
    formData.append("language", currentLanguage);
    formData.append("tts_enabled", isNavbarSpeakEnabled() ? "true" : "false");
    if (textToSend) {
      formData.append("client_transcript", textToSend);
    }
    if (currentSessionId) {
      formData.append("session_id", currentSessionId);
    }

    const res = await fetch("/api/voice/chat", {
      method: "POST",
      body: formData,
      signal: activeVoiceAbortController.signal
    });

    if (!res.ok) {
      throw new Error(`Voice server error: ${res.status}`);
    }

    const data = await res.json();
    activeVoiceAbortController = null;
    showTyping(false);

    if (!data.success) {
      showToast(data.message || "Could not understand speech. Please speak again.");
      if (isContinuousVoiceMode) {
        transitionAfterTTS();
      }
      return;
    }

    // 1. Append user transcribed message
    appendUserBubble(data.user_text || textToSend, true);

    // 2. Update session state
    currentSessionId = data.session_id;
    localStorage.setItem("northstar_session_id", currentSessionId);
    lastState = data.state;

    // 3. Render Assistant reply bubble with cards & quick replies, and seamlessly wire voice completion
    appendAssistantBubble(
      data.reply,
      data.options,
      data.quick_replies,
      data.booking,
      data.audio_base64,
      transitionAfterTTS
    );

  } catch (err) {
    showTyping(false);
    activeVoiceAbortController = null;
    if (err.name === "AbortError") {
      console.log("[Voice] In-flight request was interrupted by new user speech.");
    } else {
      console.warn("Voice turn processing error:", err);
      showToast("Error processing voice turn. Listening again...");
      if (isContinuousVoiceMode) {
        transitionAfterTTS();
      }
    }
  }
}

// Audio Playback Helpers
function playAudio(audioDataUri, onEndCallback = null) {
  if (!isNavbarSpeakEnabled()) {
    stopCurrentAudio();
    if (onEndCallback) onEndCallback();
    return;
  }
  stopCurrentAudio();
  try {
    currentAudioPlayer = new Audio(audioDataUri);
    let finished = false;
    const done = () => {
      if (!finished) {
        finished = true;
        currentAudioPlayer = null;
        if (typeof onEndCallback === "function") onEndCallback();
      }
    };
    currentAudioPlayer.onended = done;
    currentAudioPlayer.onerror = (e) => {
      console.warn("Audio playback error:", e);
      done();
    };
    currentAudioPlayer.play().catch(err => {
      console.warn("Autoplay was prevented by browser policy:", err);
      done();
    });
  } catch (e) {
    console.warn("playAudio failed:", e);
    currentAudioPlayer = null;
    if (typeof onEndCallback === "function") onEndCallback();
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
    try {
      window.speechSynthesis.cancel();
    } catch (e) {}
  }
}

// Preload and cache speech synthesis voices so they are ready immediately
let cachedSpeechVoices = [];
function reloadSpeechVoices() {
  if (typeof window !== "undefined" && window.speechSynthesis) {
    cachedSpeechVoices = window.speechSynthesis.getVoices() || [];
  }
}
if (typeof window !== "undefined" && window.speechSynthesis) {
  reloadSpeechVoices();
  window.speechSynthesis.onvoiceschanged = reloadSpeechVoices;
}

function getStrictFemaleVoice(targetLang) {
  let voices = cachedSpeechVoices;
  if (!voices || voices.length === 0) {
    if (typeof window !== "undefined" && window.speechSynthesis) {
      voices = window.speechSynthesis.getVoices() || [];
      cachedSpeechVoices = voices;
    }
  }
  if (!voices || voices.length === 0) return null;

  const shortLang = (targetLang || "en").toLowerCase().split("-")[0];
  const maleKeywords = [
    "david", "mark", "ravi", "george", "guy", "jorge", "pablo", "diego",
    "madhav", "stefan", "cosimo", "richard", "james", "john", "paul",
    "mike", "steve", "male", "hombre", "varon"
  ];
  const femaleKeywords = [
    "zira", "heera", "aria", "jenny", "swara", "elvira", "samantha", "victoria",
    "karen", "susan", "eva", "monica", "paulina", "kalpana", "veena",
    "hazel", "helena", "laura", "alva", "lucia", "sabina", "martha", "elena", "female"
  ];

  // 1. Language match + Explicit female keyword (and strictly not male)
  let selected = voices.find(v => {
    const vName = (v.name || "").toLowerCase();
    const vLang = (v.lang || "").toLowerCase();
    const isLang = vLang === targetLang.toLowerCase() || vLang.startsWith(shortLang);
    return isLang && femaleKeywords.some(k => vName.includes(k)) && !maleKeywords.some(k => vName.includes(k));
  });
  if (selected) return selected;

  // 2. Language match + strictly not male
  selected = voices.find(v => {
    const vName = (v.name || "").toLowerCase();
    const vLang = (v.lang || "").toLowerCase();
    const isLang = vLang === targetLang.toLowerCase() || vLang.startsWith(shortLang);
    return isLang && !maleKeywords.some(k => vName.includes(k));
  });
  if (selected) return selected;

  // 3. ANY female voice on the system regardless of language (e.g. Zira, Heera)
  selected = voices.find(v => {
    const vName = (v.name || "").toLowerCase();
    return femaleKeywords.some(k => vName.includes(k)) && !maleKeywords.some(k => vName.includes(k));
  });
  if (selected) return selected;

  // 4. Any voice that does NOT contain male keywords
  selected = voices.find(v => {
    const vName = (v.name || "").toLowerCase();
    return !maleKeywords.some(k => vName.includes(k));
  });
  return selected;
}

function speakViaBrowserTTS(text, onEndCallback = null) {
  if (!window.speechSynthesis) {
    if (typeof onEndCallback === "function") onEndCallback();
    return;
  }
  if (!isNavbarSpeakEnabled()) {
    stopCurrentAudio();
    if (typeof onEndCallback === "function") onEndCallback();
    return;
  }
  stopCurrentAudio();

  try {
    const clean = text
      .replace(/[*_#`~]/g, '')
      .replace(/https?:\/\/\S+/g, '')
      .replace(/[\u{10000}-\u{10ffff}]/gu, '')
      .replace(/[\u2000-\u3300]/gu, '')
      .replace(/[•\-\*\+]/g, '')
      .trim();
    const utterance = new SpeechSynthesisUtterance(clean.substring(0, 260));
    const langCfg = LANG_CONFIG[currentLanguage] || LANG_CONFIG.en;
    const targetLang = (langCfg.browserVoice || "en-US").toLowerCase();

    utterance.lang = langCfg.browserVoice || "en-US";
    utterance.rate = 1.0;
    // Higher pitch guarantees a pleasant female timbre
    utterance.pitch = 1.35;

    const femaleVoice = getStrictFemaleVoice(targetLang);
    if (femaleVoice) {
      utterance.voice = femaleVoice;
    }

    let finished = false;
    let safetyTimer = null;
    const onDone = () => {
      if (!finished) {
        finished = true;
        if (safetyTimer) clearTimeout(safetyTimer);
        if (typeof onEndCallback === "function") onEndCallback();
      }
    };

    utterance.onend = onDone;
    utterance.onerror = (e) => {
      console.warn("Browser SpeechSynthesis error:", e);
      onDone();
    };

    // Watchdog safety timeout in case browser drops onend
    const estimatedDuration = Math.max(1500, clean.length * 85);
    safetyTimer = setTimeout(onDone, estimatedDuration + 1500);

    window.speechSynthesis.speak(utterance);
  } catch (e) {
    console.warn("Browser speech synthesis error:", e);
    if (typeof onEndCallback === "function") onEndCallback();
  }
}

// --------------------------------------------------------------------------
// Unified TTS Playback with Audio State Lifecycle Management
// Ensures SPEAKING state is set BEFORE audio begins and maintained until complete
// --------------------------------------------------------------------------
function playTTSWithLifecycle(audioBase64, text, onComplete) {
  // CRITICAL: Immediately enter SPEAKING state before sound starts
  if (isContinuousVoiceMode) {
    setAudioState(AUDIO_STATE.SPEAKING);
    // Mute microphone capture immediately: stop speech recognition & discard buffer
    stopBrowserSpeechRecognition();
    audioChunks = [];
    liveTranscribedSpeech = "";
    accumulatedFinalText = "";
    hasSpokenInTurn = false;
    lastVoiceActivityTime = 0;
  }

  let completed = false;
  const finishOnce = () => {
    if (!completed) {
      completed = true;
      if (typeof onComplete === "function") {
        onComplete();
      }
    }
  };

  if (!isNavbarSpeakEnabled() || !text || text.trim().length === 0) {
    stopCurrentAudio();
    finishOnce();
    return;
  }

  // 1. If we have audioBase64 from Edge TTS
  if (audioBase64) {
    playAudio(audioBase64, finishOnce);
    return;
  }

  // 2. Fetch server Edge TTS audio stream, fallback to female browser TTS
  try {
    const cleanSnippet = text.replace(/[*_#`~]/g, '').trim().substring(0, 600);
    const audioUrl = `/api/voice/tts?text=${encodeURIComponent(cleanSnippet)}&lang=${encodeURIComponent(currentLanguage || 'en')}`;
    const tempAudio = new Audio(audioUrl);

    tempAudio.oncanplaythrough = () => {
      if (!isNavbarSpeakEnabled()) {
        finishOnce();
        return;
      }
      stopCurrentAudio();
      currentAudioPlayer = tempAudio;
      tempAudio.onended = () => {
        currentAudioPlayer = null;
        finishOnce();
      };
      tempAudio.onerror = () => {
        currentAudioPlayer = null;
        speakViaBrowserTTS(text, finishOnce);
      };
      tempAudio.play().catch(() => {
        currentAudioPlayer = null;
        speakViaBrowserTTS(text, finishOnce);
      });
    };

    tempAudio.onerror = () => {
      speakViaBrowserTTS(text, finishOnce);
    };
  } catch (e) {
    speakViaBrowserTTS(text, finishOnce);
  }
}
window.playTTSWithLifecycle = playTTSWithLifecycle;

window.handleMessageAudioClick = async function(btn, msgId) {
  if (!isNavbarSpeakEnabled()) {
    stopCurrentAudio();
    if (btn) {
      btn.style.display = "none";
      btn.classList.remove("playing");
      btn.innerHTML = '<i class="fa-solid fa-volume-high"></i>';
    }
    showToast("Voice speech is currently muted in top navbar. Click the speaker in the top bar to enable voice.");
    return;
  }

  const row = btn.closest(".assistant-message-row");
  if (!row) return;

  if (btn.classList.contains("playing")) {
    stopCurrentAudio();
    btn.classList.remove("playing");
    btn.innerHTML = '<i class="fa-solid fa-volume-high"></i>';
    if (isContinuousVoiceMode) {
      transitionAfterTTS();
    }
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
    if (isContinuousVoiceMode) {
      transitionAfterTTS();
    }
  };

  const audioBase64 = row.dataset.audioBase64;
  const text = row.dataset.msgText || "";

  playTTSWithLifecycle(audioBase64, text, resetBtn);
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
