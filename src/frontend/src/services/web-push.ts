import { getApp, getApps, initializeApp } from "firebase/app";
import {
  getMessaging,
  getToken,
  isSupported,
  onMessage,
} from "firebase/messaging";

import { requisitar } from "./api.ts";

const firebaseConfig = {
  apiKey: process.env.EXPO_PUBLIC_FIREBASE_API_KEY,
  authDomain: process.env.EXPO_PUBLIC_FIREBASE_AUTH_DOMAIN,
  projectId: process.env.EXPO_PUBLIC_FIREBASE_PROJECT_ID,
  storageBucket: process.env.EXPO_PUBLIC_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: process.env.EXPO_PUBLIC_FIREBASE_MESSAGING_SENDER_ID,
  appId: process.env.EXPO_PUBLIC_FIREBASE_APP_ID,
};

const vapidKey = process.env.EXPO_PUBLIC_FIREBASE_VAPID_KEY;

function firebaseConfigurado() {
  return Object.values(firebaseConfig).every(Boolean) && Boolean(vapidKey);
}

export function webPushDisponivel() {
  if (
    typeof window === "undefined" ||
    !("Notification" in window) ||
    !("serviceWorker" in navigator) ||
    !firebaseConfigurado()
  ) {
    return false;
  }
  return true;
}

export function permissaoWebPush(): NotificationPermission | "indisponivel" {
  if (typeof window === "undefined" || !("Notification" in window)) {
    return "indisponivel";
  }
  return Notification.permission;
}

async function firebaseMessaging() {
  if (!webPushDisponivel() || !(await isSupported())) return null;
  const app = getApps().length ? getApp() : initializeApp(firebaseConfig);
  return getMessaging(app);
}

export async function registrarServiceWorkerWeb() {
  if (typeof window === "undefined" || !("serviceWorker" in navigator)) {
    return false;
  }
  await navigator.serviceWorker.register("/firebase-messaging-sw.js");
  return true;
}

export async function ativarWebPush() {
  const messaging = await firebaseMessaging();
  if (!messaging || !vapidKey) return false;
  const permissao = await Notification.requestPermission();
  if (permissao !== "granted") return false;
  await registrarServiceWorkerWeb();
  const token = await getToken(messaging, { vapidKey });
  if (!token) throw new Error("O Firebase não forneceu um token web.");

  await requisitar("/usuarios/eu/dispositivos", undefined, {
    method: "POST",
    body: { token, plataforma: "web" },
  });
  return true;
}

export async function ouvirMensagensWeb(
  aoReceber: (payload: {
    notification?: { title?: string; body?: string };
  }) => void,
) {
  const messaging = await firebaseMessaging();
  if (!messaging) return () => {};
  return onMessage(messaging, aoReceber);
}

export async function removerWebPush() {
  return;
}
