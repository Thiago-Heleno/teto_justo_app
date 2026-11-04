import { readFile, writeFile } from "node:fs/promises";

try {
  const ambiente = await readFile(
    new URL("../.env.local", import.meta.url),
    "utf8",
  );
  for (const linha of ambiente.split(/\r?\n/)) {
    const correspondencia = linha.match(/^([A-Z0-9_]+)=(.*)$/);
    if (correspondencia && !process.env[correspondencia[1]]) {
      process.env[correspondencia[1]] = correspondencia[2];
    }
  }
} catch {
  // A configuração de produção é fornecida pelo ambiente do deploy.
}

const config = {
  apiKey: process.env.EXPO_PUBLIC_FIREBASE_API_KEY || "",
  authDomain: process.env.EXPO_PUBLIC_FIREBASE_AUTH_DOMAIN || "",
  projectId: process.env.EXPO_PUBLIC_FIREBASE_PROJECT_ID || "",
  storageBucket: process.env.EXPO_PUBLIC_FIREBASE_STORAGE_BUCKET || "",
  messagingSenderId: process.env.EXPO_PUBLIC_FIREBASE_MESSAGING_SENDER_ID || "",
  appId: process.env.EXPO_PUBLIC_FIREBASE_APP_ID || "",
};

const firebaseConfig = JSON.stringify(config);
const serviceWorker = `importScripts(
  "https://www.gstatic.com/firebasejs/11.10.0/firebase-app-compat.js",
);
importScripts(
  "https://www.gstatic.com/firebasejs/11.10.0/firebase-messaging-compat.js",
);

firebase.initializeApp(${firebaseConfig});
firebase.messaging();
`;

await writeFile(
  new URL("../public/firebase-messaging-sw.js", import.meta.url),
  serviceWorker,
);
