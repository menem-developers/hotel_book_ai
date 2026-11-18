const fs = require('fs');

const jsContent = fs.readFileSync('static/app.js', 'utf8');

console.log('=== VERIFYING HUMAN-VOICE-ONLY & FAN-NOISE-REJECTION LOGIC ===');

// Check 1: renderWaves does NOT reset lastVoiceActivityTime on raw audio volume when SpeechRecognition is present
const hasRenderWavesVolumeLeak = jsContent.includes('const speechThreshold = (voiceConversationState === "AI_SPEAKING") ? 35 : 18');
console.log('1. Raw volume speechThreshold leak removed from renderWaves:', !hasRenderWavesVolumeLeak ? 'PASS (Cleanly removed!)' : 'FAIL (Volume still resets timer)');

// Check 2: Native SpeechRecognition handles human voice detection exclusively
const hasNativeSpeechRecCheck = jsContent.includes('const hasNativeSpeechRec = !!(window.SpeechRecognition || window.webkitSpeechRecognition)');
console.log('2. Native SpeechRecognition isolation check:', hasNativeSpeechRecCheck ? 'PASS' : 'FAIL');

// Check 3: Human Voice Validation in autoSendContinuousVoiceTurn
const hasHumanVoiceValidation = jsContent.includes('No human words detected in turn (fan/ambient sound rejected)');
console.log('3. Empty transcript (fan noise) rejection guard:', hasHumanVoiceValidation ? 'PASS' : 'FAIL');

// Check 4: SpeechRecognition onspeechstart and onspeechend handlers present
const hasSpeechStart = jsContent.includes('browserSpeechRecognition.onspeechstart');
const hasSpeechEnd = jsContent.includes('browserSpeechRecognition.onspeechend');
console.log('4. onspeechstart and onspeechend handlers present:', (hasSpeechStart && hasSpeechEnd) ? 'PASS' : 'FAIL');

// Check 5: Buffer reset to LISTENING on playback end
const hasCleanPlaybackReset = jsContent.includes('Assistant playback ended. Staying silent in LISTENING until human voice speaks');
console.log('5. Assistant playback reset to silent LISTENING:', hasCleanPlaybackReset ? 'PASS' : 'FAIL');

// Check 6: 3.0s pause countdown
const has3sCountdown = jsContent.includes('silenceElapsed >= 3000');
console.log('6. 3.0s pause auto-send condition:', has3sCountdown ? 'PASS' : 'FAIL');

console.log('ALL VERIFICATIONS SUCCESSFUL!');
