import { getApp, getApps, initializeApp } from "firebase/app";
import {
  deleteToken,
  getMessaging,
  getToken,
  isSupported,
} from "firebase/messaging";

import { requisitar } from "./api.ts";

const CHAVE_TOKEN_WEB = "teto_justo_push_token_web";

const firebaseConfig = {
  apiKey: process.env.EXPO_PUBLIC_FIREBASE_API_KEY,
  authDomain: process.env.EXPO_PUBLIC_FIREBASE_AUTH_DOMAIN,
  projectId: process.env.EXPO_PUBLIC_FIREBASE_PROJECT_ID,
  storageBucket: process.env.EXPO_PUBLIC_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: process.env.EXPO_PUBLIC_FIREBASE_MESSAGING_SENDER_ID,
  appId: process.env.EXPO_PUBLIC_FIREBASE_APP_ID,
};

const vapidKey = process.env.EXPO_PUBLIC_FIREBASE_VAPID_KEY;

export function webPushDisponivel() {
  return (
    typeof window !== "undefined" &&
    "Notification" in window &&
    "serviceWorker" in navigator &&
    Object.values(firebaseConfig).every(Boolean) &&
    Boolean(vapidKey)
  );
}

export async function webPushAtivo() {
  return (
    webPushDisponivel() &&
    Notification.permission === "granted" &&
    Boolean(localStorage.getItem(CHAVE_TOKEN_WEB))
  );
}

async function firebaseMessaging() {
  if (!webPushDisponivel() || !(await isSupported())) return null;
  const app = getApps().length ? getApp() : initializeApp(firebaseConfig);
  return getMessaging(app);
}

function erroSuporte(mensagem: string) {
  const erro = new Error(mensagem);
  erro.name = "AvisoPush";
  return erro;
}

export async function ativarWebPush() {
  if (!webPushDisponivel()) {
    throw erroSuporte(
      "Este navegador ou esta versão do app não tem notificações configuradas.",
    );
  }
  // Deve ser a primeira chamada assíncrona: o Safari exige o gesto do clique.
  if ((await Notification.requestPermission()) !== "granted") return false;

  const messaging = await firebaseMessaging();
  if (!messaging || !vapidKey) {
    throw erroSuporte(
      "Este navegador não suporta notificações. No iPhone, adicione o app à Tela de Início e abra por lá.",
    );
  }
  const registro = await navigator.serviceWorker.register(
    "/firebase-messaging-sw.js",
  );
  const token = await getToken(messaging, {
    vapidKey,
    serviceWorkerRegistration: registro,
  });
  if (!token) throw new Error("O Firebase não forneceu um token web.");

  const anterior = localStorage.getItem(CHAVE_TOKEN_WEB);
  if (anterior && anterior !== token) {
    await requisitar<void>("/usuarios/eu/dispositivos", undefined, {
      method: "DELETE",
      body: { token: anterior },
    });
  }
  await requisitar("/usuarios/eu/dispositivos", undefined, {
    method: "POST",
    body: { token, plataforma: "web" },
  });
  localStorage.setItem(CHAVE_TOKEN_WEB, token);
  return true;
}

export async function removerWebPush() {
  const token = localStorage.getItem(CHAVE_TOKEN_WEB);
  if (!token) return;

  await requisitar<void>("/usuarios/eu/dispositivos", undefined, {
    method: "DELETE",
    body: { token },
  });
  localStorage.removeItem(CHAVE_TOKEN_WEB);

  // Invalida o token no Firebase para este navegador parar de receber avisos.
  const messaging = await firebaseMessaging().catch(() => null);
  if (messaging) await deleteToken(messaging).catch(() => {});
}
