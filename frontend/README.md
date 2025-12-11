# AgroChat — React prototype

This folder is a React/Vite rewrite of the static prototype in the project root.

Quick start (Windows / PowerShell):

1. cd into the folder

```powershell
cd c:\Users\brnds\OneDrive\Desktop\AgroChat\agrochat-react
npm install
npm run dev
```

2. Open the dev server URL shown by Vite (usually http://localhost:5173)

What I built:
- Login page (client-side auth for demo only)
- Chat interface with conversations stored in localStorage
- Sidebar toggles, file attachments, quick answer chips

Notes:
- The right-hand "Conversations" panel has been removed (conversations live in the left-hand sidebar now).
- Place your existing `agrochat-logo.jpg` file inside the project public folder so the app can load it at `/agrochat-logo.jpg`.

Example (Windows / PowerShell):

```powershell
copy "..\agrochat-logo.jpg" .\public\agrochat-logo.jpg
```

If you'd like I can wire this to a backend or add React Router for deep linking.
