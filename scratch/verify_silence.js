const fs = require('fs');

const html = fs.readFileSync('static/index.html', 'utf8');
const js = fs.readFileSync('static/app.js', 'utf8');
const css = fs.readFileSync('static/style.css', 'utf8');

console.log('--- Checking Hands-Free Voice UX & 3-Second Silence Logic ---');
console.log('1. Manual Send Now button in HTML:', html.includes('btn-voice-send-now') ? 'FAIL (still present)' : 'PASS (Cleanly removed!)');
console.log('2. Hands-Free Indicator in HTML:', html.includes('voice-handsfree-indicator') ? 'PASS' : 'FAIL');
console.log('3. Hands-Free text in HTML:', html.includes('Auto-sends on 3s pause') ? 'PASS' : 'FAIL');
console.log('4. Exit Voice button in HTML:', html.includes('btn-voice-cancel') ? 'PASS' : 'FAIL');

console.log('5. startVoiceSilenceWatcher in JS:', js.includes('startVoiceSilenceWatcher') ? 'PASS' : 'FAIL');
console.log('6. 3000ms silence check in JS:', js.includes('silenceElapsed >= 3000') ? 'PASS' : 'FAIL');
console.log('7. Countdown state in JS:', js.includes('PAUSE_COUNTDOWN') ? 'PASS' : 'FAIL');
console.log('8. Auto-send trigger in JS:', js.includes('autoSendContinuousVoiceTurn()') ? 'PASS' : 'FAIL');
console.log('9. CSS voice-handsfree-indicator:', css.includes('.voice-handsfree-indicator') ? 'PASS' : 'FAIL');
console.log('ALL CHECKS COMPLETE');
