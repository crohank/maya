# Phone setup

Phone browsers only allow the camera and microphone on https pages, so Maya
serves https with its own local certificate authority (CA). Nothing is installed
on the Windows laptop. The phone and the laptop must be on the same Wi-Fi.

## 1. Find the laptop's LAN IP

In a Windows terminal:

```
ipconfig
```

Use the `IPv4 Address` of the Wi-Fi adapter (for example `10.0.0.34` or
`192.168.1.23`). Ignore `172.x` addresses from the WSL or Hyper-V adapters.
`scripts/run_app.sh` prints the phone URLs it found when it starts.

## 2. Start Maya

From Git Bash in the project folder:

```
bash scripts/run_app.sh
```

The first run creates `certs/` (CA plus a server certificate for `localhost`,
`127.0.0.1` and every LAN IPv4 address from `ipconfig`). If the laptop later gets
a different IP, reissue the server certificate; the CA stays the same, so the
phone does not need to trust it again:

```
MAYA_NEW_CERT=1 bash scripts/run_app.sh
MAYA_HOSTS="192.168.1.23" MAYA_NEW_CERT=1 bash scripts/run_app.sh   # pick the IP yourself
```

Windows Firewall may ask whether to allow Docker on private networks the first
time a phone connects. Allow it for private networks only.

## 3. Trust the certificate

### iPhone (Safari)

1. Open `https://<laptop-ip>:8443/ca.crt` in Safari. Safari warns that the site is
   not private: tap Show Details, then visit this website. Tap Allow to download
   the configuration profile.
2. Settings, General, VPN and Device Management (on older iOS: Profiles). Tap
   "Maya Local CA", then Install, enter the passcode, Install again.
3. Settings, General, About, Certificate Trust Settings. Turn on full trust for
   "Maya Local CA".
4. Open `https://<laptop-ip>:8443`. There should be no warning. Tap Ask about what
   is in front of me and allow the camera and microphone.

### Android (Chrome)

1. Open `https://<laptop-ip>:8443/ca.crt` in Chrome. On the warning page tap
   Advanced, then Proceed. The file `maya-local-ca.crt` downloads.
2. Settings, Security and privacy, More security settings, Encryption and
   credentials, Install a certificate, CA certificate. Tap Install anyway and
   pick `maya-local-ca.crt` from Downloads. (Menu names vary by maker; search
   Settings for "CA certificate".)
3. Fully close Chrome and open `https://<laptop-ip>:8443`. Allow the camera and
   microphone.

### Quick path without installing the CA

Both browsers let you continue past the certificate warning (Chrome: Advanced,
Proceed; Safari: Show Details, visit this website). The camera usually still
works for that tab, but the warning comes back on every visit. Use the CA for the
demo.

## Optional: mkcert

If you prefer [mkcert](https://github.com/FiloSottile/mkcert), it does the same
job (a local CA plus a server certificate). This is optional and changes the
laptop, so it is not part of the default setup:

```
mkcert -install
mkcert -cert-file certs/cert.pem -key-file certs/key.pem localhost 127.0.0.1 <laptop-ip>
```

Then copy the mkcert root CA (`mkcert -CAROOT` shows the folder, file
`rootCA.pem`) to `certs/ca.crt` so `/ca.crt` serves it, and install it on the
phone as above.

## Troubleshooting

- Page loads but says "Not a secure page": you opened `http://`. Use `https://`.
- Camera button says permission was refused: iPhone Settings, Safari, Camera and
  Microphone set to Ask or Allow; Android Chrome, the lock icon in the address bar,
  Permissions.
- No sound on iPhone: turn off silent mode, and tap a button once so Safari allows
  audio playback.
