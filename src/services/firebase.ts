
import { initializeApp } from "firebase/app";
import { getFirestore } from "firebase/firestore";
import { getStorage } from "firebase/storage";

// Firebase configuration
const firebaseConfig = {
  apiKey: "AIzaSyDQRm7BU_rKcovj0t0YfHTdi1e8MfPKOZw",
  authDomain: "morkovka-kmv-bot.firebaseapp.com",
  projectId: "morkovka-kmv-bot",
  storageBucket: "morkovka-kmv-bot.appspot.com",
  messagingSenderId: "823746043147",
  appId: "1:823746043147:web:cda0112be2c58360178ea1"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const db = getFirestore(app);
const storage = getStorage(app);

export { app, db, storage };
