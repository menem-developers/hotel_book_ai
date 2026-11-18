import requests

data = {
    'language': 'en',
    'tts_enabled': 'true',
    'client_transcript': 'I want to book a hotel in New York for 2 guests'
}
files = {
    'audio': ('test.webm', b'RIFF....dummy', 'audio/webm')
}

res = requests.post('http://127.0.0.1:8000/api/voice/chat', data=data, files=files)
print('Status code:', res.status_code)
json_data = res.json()
print('Success:', json_data.get('success'))
print('User text:', json_data.get('user_text'))
print('Reply snippet:', json_data.get('reply', '')[:100])
print('Has audio_base64:', bool(json_data.get('audio_base64')))
