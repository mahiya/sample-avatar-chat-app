let speechRecognizer;
let avatarSynthesizer;
let isSpeaking = false;
let generatingAnswer = false;
let enableMicrophone = true;
const speakTextQueue = [];

let speechServiceToken;
let speechServiceRegion;
const iceServers = [];

const talkingAvatarCharacter = "lisa"
const talkingAvatarStyle = "casual-sitting"
const sttLocales = ["ja-JP"]
const ttsVoice = "ja-JP-NanamiNeural";
const speakRate = "50%";

async function init() {
    let resp = await (await fetch("/api/token")).json();
    speechServiceToken = resp.token;
    speechServiceRegion = resp.region;

    const iceServer = (await (await fetch("/api/turnServer")).json());
    iceServers.push(iceServer);

    document.getElementById("btnStart").disabled = false;
}

async function connectAvatar() {
    document.getElementById("btnStart").disabled = true;

    const speechSynthesisConfig = SpeechSDK.SpeechConfig.fromAuthorizationToken(speechServiceToken, speechServiceRegion)
    const avatarConfig = new SpeechSDK.AvatarConfig(talkingAvatarCharacter, talkingAvatarStyle)
    avatarConfig.customized = false;
    avatarSynthesizer = new SpeechSDK.AvatarSynthesizer(speechSynthesisConfig, avatarConfig)
    const peerConnection = new RTCPeerConnection({ iceServers });

    peerConnection.ontrack = function (event) {

        const $remoteVideo = document.getElementById('remoteVideo')
        for (var i = 0; i < $remoteVideo.childNodes.length; i++) {
            if ($remoteVideo.childNodes[i].localName === event.track.kind) {
                $remoteVideo.removeChild($remoteVideo.childNodes[i])
            }
        }

        if (event.track.kind === 'audio') {
            let audioElement = document.createElement('audio');
            audioElement.id = 'audioPlayer';
            audioElement.srcObject = event.streams[0];
            audioElement.autoplay = true;
            $remoteVideo.appendChild(audioElement);
        } else if (event.track.kind === 'video') {
            let videoElement = document.createElement('video');
            videoElement.id = 'videoPlayer';
            videoElement.srcObject = event.streams[0];
            videoElement.autoplay = true;
            videoElement.playsInline = true;
            $remoteVideo.appendChild(videoElement);
        }
    }

    peerConnection.addTransceiver('video', { direction: 'sendrecv' })
    peerConnection.addTransceiver('audio', { direction: 'sendrecv' })

    // アバターを開始する
    await avatarSynthesizer.startAvatarAsync(peerConnection);

    // 音声認識を開始する
    await startMicrophone();
}

function speak(text) {
    if (!text) return;
    if (isSpeaking) {
        speakTextQueue.push(text);
    } else {
        speakNext(text);
    }
}

async function speakNext(text) {
    isSpeaking = true;
    const ssml = `<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xmlns:mstts='http://www.w3.org/2001/mstts' xml:lang='ja-JP'><voice name='${ttsVoice}'><prosody rate='${speakRate}'><mstts:ttsembedding><mstts:leadingsilence-exact value='0'/>${escapeHtml(text)}</mstts:ttsembedding></prosody></voice></speak>`;
    await avatarSynthesizer.speakSsmlAsync(ssml);
    if (speakTextQueue.length > 0) {
        speakNext(speakTextQueue.shift());
    } else {
        isSpeaking = false;
    }
}

function escapeHtml(text) {
    return text.replace(/[&<>"'\/]/g, (match) => ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;',
        '/': '&#x2F;'
    }[match]));
}

async function startMicrophone() {

    // Azure Speech SDK の設定を行う
    const speechRecognitionConfig = SpeechSDK.SpeechConfig.fromAuthorizationToken(speechServiceToken, speechServiceRegion);
    speechRecognitionConfig.setProperty(SpeechSDK.PropertyId.SpeechServiceConnection_LanguageIdMode, "Continuous");
    const autoDetectSourceLanguageConfig = SpeechSDK.AutoDetectSourceLanguageConfig.fromLanguages(sttLocales);
    speechRecognizer = SpeechSDK.SpeechRecognizer.FromConfig(speechRecognitionConfig, autoDetectSourceLanguageConfig, SpeechSDK.AudioConfig.fromDefaultMicrophoneInput());

    // 音声認識した際の処理を設定する
    speechRecognizer.recognized = async (s, e) => {
        if (e.result.reason === SpeechSDK.ResultReason.RecognizedSpeech) {
            const recognized = e.result.text.trim()
            if (!enableMicrophone) return; // マイクが無効化されている場合は無視する
            if (isSpeaking || generatingAnswer) return; // アバターが話している間は無視する
            if (!recognized) return;
            getResponse(recognized)
            speak("はい。少々お待ちください。")
        }
    }

    // 音声認識を開始する
    await speechRecognizer.startContinuousRecognitionAsync();
}

function toggleMic() {
    $icon = document.querySelector("#btnMic i");
    $icon.classList.remove("bi-mic");
    $icon.classList.remove("bi-mic-mute");
    enableMicrophone = !enableMicrophone;
    if (enableMicrophone) {
        $icon.classList.add("bi-mic");
    } else {
        $icon.classList.add("bi-mic-mute");
    }
}

async function getResponse(message) {

    // Web API 経由で Azure OpenAI Service からメッセージの返信を取得する
    generatingAnswer = true;
    const resp = await fetch(`/api/completion`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message }),
    });
    generatingAnswer = false;

    // ストリーム形式で返ってくる Completion を逐次読み取る
    const reader = resp.body.getReader();
    let queuedText = "";
    let lastContent = "";
    while (true) {
        const { done, value } = await reader.read();
        const text = new TextDecoder("utf-8").decode(value);
        const jsonVal = text.split("\n").filter(s => s).pop(); // 複数行のJSONが返ってくる場合があるので最後の行を取得
        if (!jsonVal) break;

        // 句読点等で分割し、逐次読み上げる処理をする
        try {
            const result = JSON.parse(jsonVal);
            let content = result.content.replaceAll("\n", "");
            lastContent = content;
            content = content.replace(queuedText, "");
            const phrases = this.splitSentence(content);
            for (const phrase of phrases) {
                speak(phrase);
                queuedText += phrase;
            }
        } catch { } // JSONパースに失敗した場合は無視する(入力途中はあり得る)
    }
    // 最後の文章(区切り)を読み上げる
    const phrase = lastContent.replace(queuedText, "");
    if (phrase)
        speak(phrase);
}

function splitSentence(s) {
    // 句読点のリスト
    const speakTextSplitChars = ['.', '?', '!', ':', ';', '。', '？', '！', '：', '；'];

    // 句読点を正規表現の形式に変換し、キャプチャグループを追加
    const splitCharsRegex = new RegExp(`([^${speakTextSplitChars.join('')}]+[${speakTextSplitChars.join('')}])`, 'g');

    // 文字列を分割し、空白をトリム
    return s.match(splitCharsRegex).map(str => str.trim());
}


window.onload = init;