importScripts('https://www.gstatic.com/firebasejs/10.7.0/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/10.7.0/firebase-messaging-compat.js');

firebase.initializeApp({
    apiKey: "AIzaSyBbm4i_bakGIiRs-DiE8Cr_-TDJwyazssw",
    authDomain: "gramacart-c9d1b.firebaseapp.com",
    projectId: "gramacart-c9d1b",
    storageBucket: "gramacart-c9d1b.firebasestorage.app",
    messagingSenderId: "554981060993",
    appId: "1:554981060993:web:730e833afe091123a9f880"
});

const messaging = firebase.messaging();

messaging.onBackgroundMessage(payload => {
    const { title, body } = payload.notification;
    const url = payload.data?.url || '/';

    self.registration.showNotification(title, {
        body: body,
        icon: '/static/images/logo-192.png',
        badge: '/static/images/logo-192.png',
        data: { url },
        actions: [
            { action: 'view', title: 'View' },
            { action: 'dismiss', title: 'Dismiss' }
        ]
    });
});

self.addEventListener('notificationclick', e => {
    e.notification.close();
    if (e.action === 'dismiss') return;
    const url = e.notification.data?.url || '/';
    e.waitUntil(
        clients.matchAll({ type: 'window' }).then(list => {
            for (const client of list) {
                if (client.url === url && 'focus' in client)
                    return client.focus();
            }
            return clients.openWindow(url);
        })
    );
});