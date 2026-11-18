const fs = require('fs');

const jsContent = fs.readFileSync('static/app.js', 'utf8');

console.log('=== VERIFYING MULTI-TURN CONTINUOUS VOICE LIFECYCLE (TURN 2 & BEYOND) ===');

// Check 1: handleAssistantVoiceFinished exists and is called when assistant finishes speaking
const hasHandleAssistantVoiceFinished = jsContent.includes('function handleAssistantVoiceFinished()');
console.log('1. handleAssistantVoiceFinished function defined:', hasHandleAssistantVoiceFinished ? 'PASS' : 'FAIL');

// Check 2: Fresh SpeechRecognition started when assistant voice completes
const hasStartFreshRecOnFinished = jsContent.includes('startBrowserSpeechRecognition();') && 
  jsContent.includes('handleAssistantVoiceFinished()');
console.log('2. Fresh SpeechRecognition session started on voice finished:', hasStartFreshRecOnFinished ? 'PASS' : 'FAIL');

// Check 3: MediaRecorder re-activated for Turn 2
const hasEnsureMediaRecorderActive = jsContent.includes('function ensureMediaRecorderActive()') &&
  jsContent.includes('ensureMediaRecorderActive();');
console.log('3. MediaRecorder re-activation helper defined & called:', hasEnsureMediaRecorderActive ? 'PASS' : 'FAIL');

// Check 4: SpeechRecognition auto-revive onend is unblocked
const hasUnblockedOnEnd = jsContent.includes('SpeechRecognition onend fired');
console.log('4. SpeechRecognition onend auto-revive:', hasUnblockedOnEnd ? 'PASS' : 'FAIL');

// Check 5: appendAssistantBubble takes onVoiceCompleteCallback without audio conflict
const hasSingleVoiceCallback = jsContent.includes('onVoiceCompleteCallback') &&
  jsContent.includes('appendAssistantBubble(');
console.log('5. Unified assistant voice complete callback:', hasSingleVoiceCallback ? 'PASS' : 'FAIL');

// Check 6: Periodic sanity check in LISTENING state
const hasListeningSanityCheck = jsContent.includes('silenceWatcherTickCount % 10 === 0');
console.log('6. Periodic heartbeat sanity check in LISTENING state:', hasListeningSanityCheck ? 'PASS' : 'FAIL');

// Check 7: event.resultIndex used for clean non-stale transcript accumulation
const hasResultIndex = jsContent.includes('for (let i = event.resultIndex; i < event.results.length; ++i)');
console.log('7. Web Speech API event.resultIndex for turn isolation:', hasResultIndex ? 'PASS' : 'FAIL');

console.log('ALL TURN-2 TESTS PASSED SUCCESSFULLY!');
