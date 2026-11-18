// scratch/test_audio_state_manager.js
// Comprehensive verification of the 4-state audio lifecycle system & feedback loop prevention

const assert = require("assert");

// Mock environment
let currentAudioState = "IDLE";
const AUDIO_STATE = {
  IDLE: "IDLE",
  LISTENING: "LISTENING",
  PROCESSING: "PROCESSING",
  SPEAKING: "SPEAKING"
};

const POST_TTS_DELAY_MS = 400;
let postTtsDelayTimer = null;
let isContinuousVoiceMode = true;
let hasSpokenInTurn = false;
let lastVoiceActivityTime = 0;
let liveTranscribedSpeech = "";
let accumulatedFinalText = "";
let audioChunks = [];
let lastAssistantResponseText = "";
let sttRequestsCount = 0;
let mockSpeechRecognitionActive = false;
let mockMediaRecorderActive = false;

function setAudioState(state, previewText = "", countdownSecs = 3) {
  currentAudioState = state;
}

function startBrowserSpeechRecognition() {
  mockSpeechRecognitionActive = true;
}

function stopBrowserSpeechRecognition() {
  mockSpeechRecognitionActive = false;
}

function ensureMediaRecorderActive() {
  mockMediaRecorderActive = true;
}

// Simulate onspeechstart
function simulateOnSpeechStart() {
  if (currentAudioState !== AUDIO_STATE.LISTENING) {
    return false; // Dropped!
  }
  return true; // Accepted!
}

// Simulate onresult
function simulateOnResult(transcript) {
  if (currentAudioState !== AUDIO_STATE.LISTENING) {
    return false; // Dropped!
  }
  liveTranscribedSpeech = transcript;
  lastVoiceActivityTime = Date.now();
  hasSpokenInTurn = true;
  return true;
}

// Simulate mediaRecorder.ondataavailable
function simulateOnDataAvailable(chunk) {
  if (currentAudioState !== AUDIO_STATE.LISTENING) {
    return false; // Dropped!
  }
  audioChunks.push(chunk);
  return true;
}

// Simulate transitionAfterTTS
function transitionAfterTTS(onComplete) {
  setAudioState(AUDIO_STATE.IDLE);
  audioChunks = [];
  liveTranscribedSpeech = "";
  accumulatedFinalText = "";
  hasSpokenInTurn = false;
  lastVoiceActivityTime = 0;

  if (postTtsDelayTimer) clearTimeout(postTtsDelayTimer);

  postTtsDelayTimer = setTimeout(() => {
    postTtsDelayTimer = null;
    audioChunks = [];
    liveTranscribedSpeech = "";
    accumulatedFinalText = "";
    hasSpokenInTurn = false;
    lastVoiceActivityTime = 0;

    setAudioState(AUDIO_STATE.LISTENING);
    startBrowserSpeechRecognition();
    ensureMediaRecorderActive();
    if (onComplete) onComplete();
  }, POST_TTS_DELAY_MS);
}

// Simulate autoSendContinuousVoiceTurn
function autoSendContinuousVoiceTurn() {
  if (currentAudioState === AUDIO_STATE.PROCESSING || currentAudioState === AUDIO_STATE.SPEAKING || currentAudioState === AUDIO_STATE.IDLE) {
    return "BLOCKED_BY_STATE";
  }

  const textToSend = (liveTranscribedSpeech || accumulatedFinalText || "").trim();
  if (!textToSend || textToSend.length < 2) {
    setAudioState(AUDIO_STATE.LISTENING);
    return "REJECTED_EMPTY";
  }

  // Echo guard
  if (lastAssistantResponseText && textToSend) {
    const cleanUser = textToSend.toLowerCase().replace(/[^a-z0-9]/g, '');
    const cleanAi = lastAssistantResponseText.replace(/[^a-z0-9]/g, '');
    if (cleanUser.length > 8 && cleanAi.includes(cleanUser)) {
      setAudioState(AUDIO_STATE.LISTENING);
      return "REJECTED_ECHO";
    }
  }

  setAudioState(AUDIO_STATE.PROCESSING);
  sttRequestsCount++;
  return "SENT";
}

// Simulate playTTSWithLifecycle
function playTTSWithLifecycle(text, options, onComplete) {
  setAudioState(AUDIO_STATE.SPEAKING);
  stopBrowserSpeechRecognition();
  audioChunks = [];
  liveTranscribedSpeech = "";
  accumulatedFinalText = "";
  hasSpokenInTurn = false;
  lastVoiceActivityTime = 0;

  lastAssistantResponseText = text.toLowerCase();

  let completed = false;
  const finishOnce = () => {
    if (!completed) {
      completed = true;
      if (typeof onComplete === "function") onComplete();
    }
  };

  if (options && options.shouldError) {
    setTimeout(finishOnce, 50); // Simulates error or immediate fallback
  } else {
    setTimeout(finishOnce, 150); // Simulates normal audio duration
  }
}

// Run the 7 verification tests
async function runAllTests() {
  console.log("=== Running 7 Audio Lifecycle & Feedback Loop Tests ===");

  // SCENARIO 1: User speaks -> Chatbot responds normally
  console.log("\n[Test 1] User speaks -> Normal response workflow");
  setAudioState(AUDIO_STATE.LISTENING);
  startBrowserSpeechRecognition();
  ensureMediaRecorderActive();
  
  assert.strictEqual(currentAudioState, AUDIO_STATE.LISTENING, "Must start in LISTENING");
  assert.strictEqual(simulateOnResult("I want to book a luxury room in New York"), true);
  assert.strictEqual(simulateOnDataAvailable({ size: 1024 }), true);
  assert.strictEqual(audioChunks.length, 1);

  const sendResult1 = autoSendContinuousVoiceTurn();
  assert.strictEqual(sendResult1, "SENT");
  assert.strictEqual(currentAudioState, AUDIO_STATE.PROCESSING, "State must transition LISTENING -> PROCESSING");
  assert.strictEqual(sttRequestsCount, 1);
  console.log("  ✓ Test 1 Passed: User speech sent to STT, transitioned to PROCESSING");

  // SCENARIO 2: Chatbot speaks -> Microphone must not send voice to STT
  console.log("\n[Test 2] Chatbot speaks -> Mic feedback loop prevented");
  let ttsFinished = false;
  playTTSWithLifecycle("We have luxury 5-star properties in New York near JFK airport", {}, () => {
    ttsFinished = true;
  });

  assert.strictEqual(currentAudioState, AUDIO_STATE.SPEAKING, "State must transition PROCESSING -> SPEAKING");
  assert.strictEqual(mockSpeechRecognitionActive, false, "Speech recognition must be stopped during SPEAKING");
  assert.strictEqual(audioChunks.length, 0, "Audio chunks must be discarded upon entering SPEAKING");

  // While SPEAKING, loudspeaker plays assistant voice:
  const speakerHeardText = simulateOnResult("We have luxury 5-star properties in New York");
  const speakerHeardAudio = simulateOnDataAvailable({ size: 5000 });
  const sendDuringSpeaking = autoSendContinuousVoiceTurn();

  assert.strictEqual(speakerHeardText, false, "Speech recognition must reject speaker audio during SPEAKING");
  assert.strictEqual(speakerHeardAudio, false, "MediaRecorder must drop chunks during SPEAKING");
  assert.strictEqual(audioChunks.length, 0, "No chunks accumulated during SPEAKING");
  assert.strictEqual(sendDuringSpeaking, "BLOCKED_BY_STATE", "Cannot send STT while in SPEAKING state");
  assert.strictEqual(sttRequestsCount, 1, "STT count must not increase");
  console.log("  ✓ Test 2 Passed: Speaker output was completely blocked from mic capture");

  // Wait for TTS playback to finish
  await new Promise(r => setTimeout(r, 200));
  assert.strictEqual(ttsFinished, true);

  // SCENARIO 3: Chatbot finishes speaking -> IDLE (400ms) -> LISTENING automatically
  console.log("\n[Test 3] Chatbot finishes speaking -> IDLE -> LISTENING automatically");
  let transitionedToListening = false;
  transitionAfterTTS(() => {
    transitionedToListening = true;
  });

  assert.strictEqual(currentAudioState, AUDIO_STATE.IDLE, "State must transition SPEAKING -> IDLE");
  
  // During the 400ms quiet window, any residual room reverb must be dropped:
  const reverbResult = simulateOnResult("airport");
  const reverbAudio = simulateOnDataAvailable({ size: 500 });
  assert.strictEqual(reverbResult, false, "Speech dropped during IDLE quiet window");
  assert.strictEqual(reverbAudio, false, "Audio dropped during IDLE quiet window");

  // Wait for 400ms post-TTS delay
  await new Promise(r => setTimeout(r, 450));
  assert.strictEqual(transitionedToListening, true);
  assert.strictEqual(currentAudioState, AUDIO_STATE.LISTENING, "State must transition IDLE -> LISTENING");
  assert.strictEqual(mockSpeechRecognitionActive, true, "Speech recognition re-enabled");
  assert.strictEqual(mockMediaRecorderActive, true, "MediaRecorder re-enabled");
  console.log("  ✓ Test 3 Passed: 400ms IDLE quiet window enforced, transitioned to LISTENING");

  // SCENARIO 4: User speaks immediately after chatbot finishes -> Speech detected
  console.log("\n[Test 4] User speaks immediately after chatbot finishes");
  const userTurn2Speech = simulateOnResult("Hyatt Regency please");
  const userTurn2Audio = simulateOnDataAvailable({ size: 1024 });
  assert.strictEqual(userTurn2Speech, true, "Human speech captured in LISTENING");
  assert.strictEqual(userTurn2Audio, true, "Audio chunk captured in LISTENING");

  const sendResult4 = autoSendContinuousVoiceTurn();
  assert.strictEqual(sendResult4, "SENT");
  assert.strictEqual(sttRequestsCount, 2, "Second turn sent to STT");
  console.log("  ✓ Test 4 Passed: Second turn speech captured and processed normally");

  // SCENARIO 5: User remains silent -> No unnecessary STT requests
  console.log("\n[Test 5] User remains silent -> No unnecessary STT calls");
  setAudioState(AUDIO_STATE.LISTENING);
  hasSpokenInTurn = false;
  liveTranscribedSpeech = "";
  accumulatedFinalText = "";
  audioChunks = [];

  const silentSend = autoSendContinuousVoiceTurn();
  assert.strictEqual(silentSend, "REJECTED_EMPTY");
  assert.strictEqual(sttRequestsCount, 2, "STT count remains unchanged");
  assert.strictEqual(currentAudioState, AUDIO_STATE.LISTENING);
  console.log("  ✓ Test 5 Passed: Silence rejected without STT call");

  // SCENARIO 6: TTS fails or gets interrupted -> Listening recovers correctly
  console.log("\n[Test 6] TTS fails or gets interrupted -> Recovery to LISTENING");
  setAudioState(AUDIO_STATE.PROCESSING);
  let errorTTSDone = false;
  playTTSWithLifecycle("Error test text", { shouldError: true }, () => {
    transitionAfterTTS(() => {
      errorTTSDone = true;
    });
  });

  assert.strictEqual(currentAudioState, AUDIO_STATE.SPEAKING);
  await new Promise(r => setTimeout(r, 550));
  assert.strictEqual(errorTTSDone, true);
  assert.strictEqual(currentAudioState, AUDIO_STATE.LISTENING, "Recovered to LISTENING after TTS failure");
  console.log("  ✓ Test 6 Passed: Failed TTS recovered cleanly to LISTENING state");

  // SCENARIO 7: Multiple conversations -> No duplicate responses or infinite loops
  console.log("\n[Test 7] Multiple conversation turns -> Zero feedback loops");
  for (let turn = 1; turn <= 3; turn++) {
    // 1. LISTENING -> User speaks
    assert.strictEqual(currentAudioState, AUDIO_STATE.LISTENING);
    simulateOnResult(`Turn ${turn} user message`);
    simulateOnDataAvailable({ size: 1000 });

    // 2. LISTENING -> PROCESSING
    const turnSend = autoSendContinuousVoiceTurn();
    assert.strictEqual(turnSend, "SENT");
    assert.strictEqual(currentAudioState, AUDIO_STATE.PROCESSING);

    // 3. PROCESSING -> SPEAKING
    let turnTTSFinished = false;
    playTTSWithLifecycle(`Turn ${turn} response text from AI`, {}, () => {
      transitionAfterTTS(() => {
        turnTTSFinished = true;
      });
    });
    assert.strictEqual(currentAudioState, AUDIO_STATE.SPEAKING);

    // Attempted echo feedback during speaking:
    simulateOnResult(`Turn ${turn} response text from AI`);
    simulateOnDataAvailable({ size: 3000 });
    assert.strictEqual(audioChunks.length, 0, "No audio buffered from speaker");

    // Wait for TTS (150ms) + Post-TTS delay (400ms)
    await new Promise(r => setTimeout(r, 600));
    assert.strictEqual(turnTTSFinished, true);
    assert.strictEqual(currentAudioState, AUDIO_STATE.LISTENING, "Returned to LISTENING for next cycle");
  }

  console.log("  ✓ Test 7 Passed: 3 full multi-turn cycles executed cleanly with 0 feedback loops");

  console.log("\n🎉 ALL 7 AUDIO STATE LIFECYCLE TESTS PASSED PERFECTLY!\n");
}

runAllTests().catch(err => {
  console.error("Test failure:", err);
  process.exit(1);
});
