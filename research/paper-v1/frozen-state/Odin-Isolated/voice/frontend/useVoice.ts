/**
 * Odin-Orchestrator — useVoice hook (self-contained, EN + AR).
 *
 * Extracted and cleaned from the mostafa-app chat page. No dependency on mostafa-app.
 *
 * Design change vs the prototype:
 *  - STT now prefers the LOCAL backend /voice/stt (faster-whisper, offline, EN+AR) by
 *    recording the mic and POSTing the audio. The old browser Web Speech API path is kept
 *    ONLY as an optional fallback, because in Chrome it streams audio to Google servers —
 *    unacceptable for fintech. Set preferLocalSTT=false to use the browser path.
 *  - TTS calls /voice/tts?lang=en|ar (Kokoro for English, macOS/Piper for Arabic).
 */
import { useCallback, useRef, useState } from "react";

export type VoiceLang = "en" | "ar";

export function useVoice(opts: { lang?: VoiceLang; preferLocalSTT?: boolean } = {}) {
  const lang: VoiceLang = opts.lang ?? "en";
  const preferLocalSTT = opts.preferLocalSTT ?? true;

  const [listening, setListening] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const mediaRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  // --- STT: local recorder -> /voice/stt -----------------------------------
  const startLocalRecording = useCallback(async (onText: (t: string) => void) => {
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const rec = new MediaRecorder(stream);
      chunksRef.current = [];
      rec.ondataavailable = (e) => e.data.size && chunksRef.current.push(e.data);
      rec.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        const fd = new FormData();
        fd.append("file", blob, "audio.webm");
        try {
          const r = await fetch(`/voice/stt?language=${lang}`, { method: "POST", body: fd });
          if (!r.ok) throw new Error(`stt ${r.status}`);
          const data = await r.json();
          onText(data.text || "");
        } catch (e: any) {
          setError(e.message || "stt failed");
        }
      };
      mediaRef.current = rec;
      rec.start();
      setListening(true);
    } catch (e: any) {
      setError(e.message || "mic permission denied");
    }
  }, [lang]);

  const stopLocalRecording = useCallback(() => {
    mediaRef.current?.stop();
    mediaRef.current = null;
    setListening(false);
  }, []);

  // --- STT: optional browser fallback (cloud-based; off by default) ---------
  const browserDictate = useCallback((onText: (t: string) => void) => {
    const Rec: any =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!Rec) { setError("Browser speech recognition unavailable (use Chrome/Safari)."); return; }
    const rec = new Rec();
    rec.continuous = true;
    rec.interimResults = true;
    rec.lang = lang === "ar" ? "ar-EG" : "en-US";
    let base = "";
    rec.onstart = () => setListening(true);
    rec.onend = () => setListening(false);
    rec.onerror = (e: any) => { setError(e.error || "mic error"); setListening(false); };
    rec.onresult = (e: any) => {
      let interim = "", final = "";
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const r = e.results[i];
        if (r.isFinal) final += r[0].transcript; else interim += r[0].transcript;
      }
      base = final ? (base + " " + final).trim() : base;
      onText((base + " " + interim).trim());
    };
    rec.start();
  }, [lang]);

  const toggleMic = useCallback((onText: (t: string) => void) => {
    if (listening) { stopLocalRecording(); return; }
    if (preferLocalSTT) startLocalRecording(onText);
    else browserDictate(onText);
  }, [listening, preferLocalSTT, startLocalRecording, browserDictate, stopLocalRecording]);

  // --- TTS: /voice/tts -> fallback to browser SpeechSynthesis ---------------
  const speak = useCallback(async (text: string) => {
    if (!text.trim()) return;
    audioRef.current?.pause();
    audioRef.current = null;
    window.speechSynthesis?.cancel();
    try {
      const r = await fetch(`/voice/tts?text=${encodeURIComponent(text)}&lang=${lang}`);
      if (r.ok) {
        const url = URL.createObjectURL(await r.blob());
        const a = new Audio(url);
        audioRef.current = a;
        a.onended = () => URL.revokeObjectURL(url);
        await a.play();
        return;
      }
    } catch { /* fall through to browser */ }

    if (!("speechSynthesis" in window)) return;
    const utter = new SpeechSynthesisUtterance(text);
    const voices = window.speechSynthesis.getVoices();
    const want = lang === "ar" ? "ar" : "en";
    utter.voice =
      voices.find((v) => v.lang.startsWith(want) && v.localService) ||
      voices.find((v) => v.lang.startsWith(want)) || null;
    window.speechSynthesis.speak(utter);
  }, [lang]);

  const stopSpeaking = useCallback(() => {
    audioRef.current?.pause();
    audioRef.current = null;
    window.speechSynthesis?.cancel();
  }, []);

  return { listening, error, toggleMic, speak, stopSpeaking };
}
