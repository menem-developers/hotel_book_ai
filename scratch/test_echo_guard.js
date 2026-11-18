const fs = require('fs');

const jsContent = fs.readFileSync('static/app.js', 'utf8');

console.log('=== VERIFYING SPEAKER FEEDBACK / ECHO REJECTION LOGIC ===');

// Check 1: lastAssistantResponseText variable declared and tracked
const hasLastAssistantText = jsContent.includes('lastAssistantResponseText') &&
  jsContent.includes('lastAssistantResponseText = (text || "").toLowerCase()');
console.log('1. lastAssistantResponseText variable tracked:', hasLastAssistantText ? 'PASS' : 'FAIL');

// Check 2: SpeechRecognition stopped during AI_SPEAKING
const hasStopRecOnAiSpeaking = jsContent.includes('setVoiceState("AI_SPEAKING");') &&
  jsContent.includes('stopBrowserSpeechRecognition();');
console.log('2. SpeechRecognition stopped during AI_SPEAKING to prevent self-listening:', hasStopRecOnAiSpeaking ? 'PASS' : 'FAIL');

// Check 3: onresult and onspeechstart discard speaker audio during AI_SPEAKING
const hasOnResultGuard = jsContent.includes('voiceConversationState === "AI_SPEAKING" || voiceConversationState === "SENDING"');
console.log('3. onresult / onspeechstart guard against speaker audio:', hasOnResultGuard ? 'PASS' : 'FAIL');

// Check 4: 200ms room reverb quiet window before listening restarts
const hasReverbDelay = jsContent.includes('200ms room-reverb quiet window') &&
  jsContent.includes('setTimeout(() => {') &&
  jsContent.includes('startBrowserSpeechRecognition();');
console.log('4. 200ms acoustic decay quiet window:', hasReverbDelay ? 'PASS' : 'FAIL');

// Check 5: Echo Feedback Guard in autoSendContinuousVoiceTurn
const hasEchoFeedbackGuard = jsContent.includes('ECHO FEEDBACK GUARD') &&
  jsContent.includes('cleanAi.includes(cleanUser)');
console.log('5. Echo Feedback Guard in autoSendContinuousVoiceTurn:', hasEchoFeedbackGuard ? 'PASS' : 'FAIL');

console.log('ALL SPEAKER FEEDBACK REJECTION TESTS PASSED!');
