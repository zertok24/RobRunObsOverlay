import argparse, json, os, re, shutil, subprocess, sys, threading, time, webbrowser
from datetime import datetime
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
RES_DIR = Path(getattr(sys, "_MEIPASS", HERE))
DATA_DIR = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "RobRunObsOverlay"
ARCHIVE_DIR = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "RobRunTracker/archive"
LOG_DIR = Path(os.environ.get("USERPROFILE", str(Path.home()))) / "AppData/LocalLow/Kefir/ROB RUN"
HEADER = re.compile(r"^\[(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)\.\d+\] \[\d+\]$")
FIRST_TS = re.compile(rb"\[(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)\.\d+\]")
RE_STATE = re.compile(r"Change state: (\w+) -> (\w+)")
RE_INIT_STATE = re.compile(r"Init state: (\w+)")
RE_STEP = re.compile(r'NetworkStep - Changed on "(\w+)"')
RE_ROLE = re.compile(r"Role changed: \w+ -> (\w+)")
RE_INIT_ROLE = re.compile(r"Init role: (\w+)")
RE_PING = re.compile(r"GetPing completed id=battle .*ping=(\d+)")
RE_TAKEN = re.compile(r"Item taken in hands: (\w+)")
RE_SWITCH = re.compile(r"Item switched: \w+ -> (\w+)")
RE_REMOVED = re.compile(r"Item removed from hands: \w+")
GAP_MAX = 600


VERSION = "1.0.0"
UPDATE_REPO = "zertok24/RobRunObsOverlay"
UPDATE_ASSET = "RobRunObsOverlay.exe"

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_NAME = "RobRunObsOverlay"


def set_autostart(enable):
    if os.name != "nt":
        return
    import winreg
    flag = DATA_DIR / "no_autostart"
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
            if enable:
                if getattr(sys, "frozen", False):
                    cmd = f'"{sys.executable}" --no-browser'
                else:
                    cmd = f'"{sys.executable}" "{Path(__file__).resolve()}" --no-browser'
                winreg.SetValueEx(k, RUN_NAME, 0, winreg.REG_SZ, cmd)
                flag.unlink(missing_ok=True)
            else:
                try:
                    winreg.DeleteValue(k, RUN_NAME)
                except FileNotFoundError:
                    pass
                flag.parent.mkdir(parents=True, exist_ok=True)
                flag.touch()
    except OSError as e:
        print(f"Demarrage automatique impossible : {e}")


def _ver(text):
    return tuple(int(x) for x in re.findall(r"\d+", text)[:4])


def self_update(argv):
    if not (getattr(sys, "frozen", False) and UPDATE_REPO and os.name == "nt"):
        return
    exe = Path(sys.executable)
    old = exe.with_name(exe.name + ".old")
    try:
        old.unlink(missing_ok=True)
        req = urllib.request.Request(
            f"https://api.github.com/repos/{UPDATE_REPO}/releases/latest",
            headers={"User-Agent": "RobRunObsOverlay"})
        with urllib.request.urlopen(req, timeout=5) as r:
            rel = json.load(r)
        if _ver(rel["tag_name"]) <= _ver(VERSION):
            return
        url = next(x["browser_download_url"] for x in rel["assets"] if x["name"] == UPDATE_ASSET)
        print(f" Mise a jour {VERSION} -> {rel['tag_name']} : telechargement...")
        new = exe.with_name(exe.name + ".new")
        with urllib.request.urlopen(url, timeout=60) as r, open(new, "wb") as f:
            shutil.copyfileobj(r, f)
        if new.stat().st_size < 1_000_000:
            new.unlink(missing_ok=True)
            return
        exe.rename(old)
        new.rename(exe)
        print(" Mise a jour installee, redemarrage...")
        env = {**os.environ, "PYINSTALLER_RESET_ENVIRONMENT": "1"}
        subprocess.Popen([str(exe), *argv], env=env, cwd=str(exe.parent))
        sys.exit(0)
    except SystemExit:
        raise
    except Exception as e:
        print(f" (mise a jour ignoree : {e})")


def is_autostart():
    if os.name != "nt":
        return False
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as k:
            winreg.QueryValueEx(k, RUN_NAME)
        return True
    except OSError:
        return False


def fresh_state(wipe_start=None):
    return {
        "wipe_started": wipe_start,
        "deaths": 0, "knockouts": 0, "revives": 0, "vehicles": 0, "robber_runs": 0,
        "raids": 0, "raids_survived": 0, "raids_died": 0,
        "battle_seconds": 0.0, "play_seconds": 0.0, "sessions": 0,
        "offsets": {}, "last_ts": None,
        "in_battle": False, "battle_start": None, "battle_died": False,
        "state": "Idle", "role": None, "item": None, "ping": None,
    }


def epoch(text):
    return datetime.strptime(text, "%Y-%m-%d %H:%M:%S").timestamp()


def log_sig(path):
    try:
        with open(path, "rb") as f:
            m = FIRST_TS.search(f.read(40000))
    except OSError:
        return None
    return m.group(1).decode() if m else None


def pretty_item(name):
    return re.sub(r"_m?\d+$", "", name)


class Tracker:
    def __init__(self, state_path, wipe_start=None):
        self.path = state_path
        self.lock = threading.Lock()
        self.pending_ts = None
        self.dirty = False
        if state_path.exists():
            old = json.loads(state_path.read_text("utf-8"))
            self.s = {**fresh_state(wipe_start), **old}
            if not old.get("offsets") and old.get("log_sig"):
                self.s["offsets"] = {old["log_sig"]: old.get("offset", 0)}
        else:
            self.s = fresh_state(wipe_start)
            self.dirty = True

    def end_battle(self, ts):
        s = self.s
        if not s["in_battle"]:
            return
        if ts and s["battle_start"]:
            s["battle_seconds"] += max(0, ts - s["battle_start"])
        s["raids_died" if s["battle_died"] else "raids_survived"] += 1
        s["in_battle"], s["battle_start"], s["battle_died"] = False, None, False

    def handle(self, ts, msg):
        s = self.s
        if s["last_ts"] is not None and 0 < ts - s["last_ts"] < GAP_MAX:
            s["play_seconds"] += ts - s["last_ts"]
        s["last_ts"] = ts
        if not s["wipe_started"]:
            s["wipe_started"] = datetime.fromtimestamp(ts).isoformat(timespec="seconds")

        if m := RE_STATE.search(msg):
            old, new = m.groups()
            s["state"] = new
            if new == "Dead":
                s["deaths"] += 1
                s["battle_died"] = s["battle_died"] or s["in_battle"]
            elif new == "KnockedOut":
                s["knockouts"] += 1
            elif new == "InVehicle":
                s["vehicles"] += 1
            if old == "KnockedOut" and new == "Idle":
                s["revives"] += 1
        elif m := RE_INIT_STATE.search(msg):
            s["state"] = m.group(1)
        elif m := RE_STEP.search(msg):
            if m.group(1) == "InBattle":
                if not s["in_battle"]:
                    s.update(in_battle=True, battle_start=ts, battle_died=False)
                    s["raids"] += 1
            else:
                self.end_battle(ts)
        elif m := RE_ROLE.search(msg):
            s["role"] = m.group(1)
            if m.group(1) == "robber":
                s["robber_runs"] += 1
        elif m := RE_INIT_ROLE.search(msg):
            s["role"] = m.group(1)
        elif m := RE_PING.search(msg):
            s["ping"] = int(m.group(1))
        elif m := (RE_TAKEN.search(msg) or RE_SWITCH.search(msg)):
            s["item"] = pretty_item(m.group(1))
        elif RE_REMOVED.search(msg):
            s["item"] = None
        else:
            return
        self.dirty = True

    def reset(self, offsets):
        self.s = fresh_state(datetime.now().isoformat(timespec="seconds"))
        self.s["offsets"] = offsets
        self.pending_ts = None
        self.dirty = True

    def sync(self, log):
        s = self.s
        try:
            size = log.stat().st_size
            with open(log, "rb") as f:
                m = FIRST_TS.search(f.read(40000))
        except FileNotFoundError:
            return False
        if not m:
            return False
        sig = m.group(1).decode()
        offsets = s["offsets"]
        if sig not in offsets:
            self.end_battle(s["last_ts"])
            s.update(last_ts=None, state="Idle", item=None)
            s["sessions"] += 1
            offsets[sig] = 0
            self.pending_ts = None
            self.dirty = True
        off = offsets[sig] if size >= offsets[sig] else 0
        if size == off:
            return False
        with open(log, "rb") as f:
            f.seek(off)
            data = f.read()
        cut = data.rfind(b"\n")
        if cut < 0:
            return False
        offsets[sig] = off + cut + 1
        for line in data[: cut + 1].decode("utf-8", "replace").splitlines():
            h = HEADER.match(line)
            if h:
                self.pending_ts = epoch(h.group(1))
            elif self.pending_ts is not None:
                self.handle(self.pending_ts, line)
                self.pending_ts = None
        return True

    def public(self):
        s = self.s
        done = s["raids_survived"] + s["raids_died"]
        keys = ["deaths", "knockouts", "revives", "vehicles", "robber_runs", "raids",
                "raids_survived", "raids_died", "state", "role", "item", "ping",
                "in_battle", "battle_start", "sessions", "wipe_started"]
        out = {k: s[k] for k in keys}
        out["battle_seconds"] = int(s["battle_seconds"])
        out["play_seconds"] = int(s["play_seconds"])
        out["survival_pct"] = round(100 * s["raids_survived"] / done) if done else None
        out["raids_done"] = done
        out["wipe_started"] = s["wipe_started"] or datetime.now().isoformat(timespec="seconds")
        out["server_time"] = time.time()
        return out

    def save(self):
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.s, indent=1), "utf-8")
        tmp.replace(self.path)
        self.dirty = False


class Server(ThreadingHTTPServer):
    allow_reuse_address = False


def is_ours(port):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/ping", timeout=2) as r:
            return r.headers.get("X-RobRunObsOverlay") == "1"
    except Exception:
        return False


def make_handler(tracker, overlay):
    class H(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path.split("?")[0] == "/stats.json":
                with tracker.lock:
                    body = json.dumps(tracker.public()).encode()
                ctype = "application/json"
            elif self.path.split("?")[0] == "/ping":
                body, ctype = b"ok", "text/plain"
            elif self.path.split("?")[0] == "/logo.png":
                found = [p for p in (RES_DIR / "logo.png", DATA_DIR / "logo.png", HERE / "logo.png") if p.is_file()]
                if not found:
                    self.send_error(404)
                    return
                body, ctype = found[0].read_bytes(), "image/png"
            elif self.path.split("?")[0] in ("/", "/overlay.html"):
                body, ctype = overlay.read_bytes(), "text/html; charset=utf-8"
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("X-RobRunObsOverlay", "1")
            self.send_header("Content-Type", ctype)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *a):
            pass
    return H


def summary(p):
    h, m = divmod(p["play_seconds"] // 60, 60)
    surv = "--" if p["survival_pct"] is None else f"{p['survival_pct']}%"
    return (f"raids {p['raids']} (survie {surv}) | morts {p['deaths']} | "
            f"KO {p['knockouts']} | sessions {p['sessions']} | jeu {h}h{m:02d}")


def main():
    ap = argparse.ArgumentParser(description="Stats ROB RUN pour overlay OBS")
    ap.add_argument("--log", type=Path, default=LOG_DIR / "Player.log")
    ap.add_argument("--state", type=Path, default=DATA_DIR / "stats_state.json")
    ap.add_argument("--no-browser", action="store_true", help="n'ouvre pas la page dans le navigateur")
    ap.add_argument("--port", type=int, default=47821)
    ap.add_argument("--reset", action="store_true", help="nouveau wipe : efface le cumul et repart de zero")
    ap.add_argument("--wipe-start", help="optionnel : date de debut du wipe, ex. 2026-11-04 (sinon = 1er evenement lu)")
    ap.add_argument("--archive", type=Path, default=ARCHIVE_DIR,
                    help="sessions archivees par RobRunTracker, lues si le dossier existe")
    ap.add_argument("--once", action="store_true", help="lit le log, affiche le resume et quitte")
    ap.add_argument("--no-autostart", action="store_true", help="desactive le lancement au demarrage de Windows")
    ap.add_argument("--autostart", action="store_true", help="reactive le lancement au demarrage de Windows")
    ap.add_argument("--no-update", action="store_true", help="ne cherche pas de mise a jour")
    a = ap.parse_args()

    if not (a.once or a.no_update or a.no_autostart):
        self_update(sys.argv[1:])
    a.state.parent.mkdir(parents=True, exist_ok=True)
    if a.no_autostart:
        set_autostart(False)
        print("Lancement au demarrage de Windows : desactive.")
        return
    if a.autostart or not (DATA_DIR / "no_autostart").exists():
        set_autostart(True)
    old_state = HERE / "stats_state.json"
    if old_state.exists() and not a.state.exists() and not a.reset:
        shutil.copy(old_state, a.state)
    if a.reset and a.state.exists():
        a.state.unlink()
    start = f"{a.wipe_start}T00:00:00" if a.wipe_start else None
    t = Tracker(a.state, start)
    prev = a.log.with_name("Player-prev.log")
    live = {log_sig(prev), log_sig(a.log)}
    if a.archive.is_dir():
        old = [(log_sig(p), p) for p in a.archive.iterdir() if p.is_file()]
        old = [(g, p) for g, p in old if g and g not in live and g not in t.s["offsets"]]
        for g, p in sorted(old, key=lambda x: x[0]):
            t.sync(p)
        if old:
            print(f"{len(old)} ancienne(s) session(s) lue(s) dans {a.archive}")
    t.sync(prev)
    t.sync(a.log)
    t.save()
    if a.once:
        print(summary(t.public()))
        return

    overlay = RES_DIR / "overlay.html"
    srv = None
    for port in range(a.port, a.port + 20):
        try:
            cand = Server(("127.0.0.1", port), make_handler(t, overlay))
        except OSError:
            continue
        threading.Thread(target=cand.serve_forever, daemon=True).start()
        if is_ours(port):
            srv, a.port = cand, port
            break
        cand.shutdown()
        cand.server_close()
    if srv is None:
        sys.exit("Aucun port libre trouve (47821-47840). Ferme les autres programmes et relance.")
    url = f"http://localhost:{a.port}/"
    if os.name == "nt":
        os.system("title RobRunObsOverlay")
        try:
            subprocess.run("clip", input=url.encode(), check=False)
        except OSError:
            pass
    print("=" * 60)
    print(f" RobRunObsOverlay v{VERSION} - c'est lance !   (discord: zertok)")
    print("=" * 60)
    print(" Laisse cette fenetre ouverte (tu peux la reduire).")
    print(" Il se lance tout seul au demarrage de Windows (desactiver : --no-autostart).")
    print(" Pour l'afficher dans OBS :")
    print("   Sources > + > Navigateur, puis colle l'adresse dans URL :")
    print(f"   {url}   (deja copiee : Ctrl+V)")
    print("   Largeur 340, Hauteur 360.")
    print("=" * 60)
    if not a.log.exists():
        print(" Player.log introuvable : lance ROB RUN, j'attends...")
    print(" " + summary(t.public()))
    if not a.no_browser:
        webbrowser.open(url)

    def snapshot_offsets():
        files = [prev, a.log]
        if a.archive.is_dir():
            files += [p for p in a.archive.iterdir() if p.is_file()]
        out = {}
        for p in files:
            sig = log_sig(p)
            if sig:
                try:
                    out[sig] = p.stat().st_size
                except OSError:
                    pass
        return out

    def show_menu():
        auto = "OUI" if is_autostart() else "NON"
        print("-" * 60)
        print(" Touches :  [R] nouveau wipe (remise a zero)")
        print("            [O] rouvrir la page dans le navigateur")
        print(f"            [A] demarrage auto avec Windows (actuellement : {auto})")
        print("-" * 60)

    def ask(question):
        print(f" {question} (O/N) ", end="", flush=True)
        while True:
            c = msvcrt.getwch().lower()
            if c in ("o", "y", "n", "\x1b", "\r"):
                ok = c in ("o", "y")
                print("oui" if ok else "non")
                return ok

    def handle_key(c):
        c = c.lower()
        if c == "r":
            if ask("NOUVEAU WIPE : effacer toutes les stats ?"):
                with t.lock:
                    t.reset(snapshot_offsets())
                    t.save()
                print(" Stats remises a zero. Bon wipe !")
            else:
                print(" Annule.")
        elif c == "o":
            webbrowser.open(url)
            print(f" Page ouverte : {url}")
        elif c == "a":
            if is_autostart():
                set_autostart(False)
                print(" Demarrage automatique : DESACTIVE.")
            else:
                set_autostart(True)
                print(" Demarrage automatique : ACTIVE.")
        else:
            return
        show_menu()

    use_keys = os.name == "nt"
    if use_keys:
        import msvcrt
        show_menu()

    last_save = 0.0
    last_sync = 0.0
    try:
        while True:
            if use_keys:
                while msvcrt.kbhit():
                    ch = msvcrt.getwch()
                    if ch in ("\x00", "\xe0"):
                        msvcrt.getwch()
                        continue
                    handle_key(ch)
            if time.time() - last_sync >= 0.5:
                last_sync = time.time()
                with t.lock:
                    changed = t.sync(a.log)
                    if t.dirty and time.time() - last_save > 2:
                        t.save()
                        last_save = time.time()
                        if changed:
                            print(time.strftime("%H:%M:%S"), summary(t.public()))
            time.sleep(0.05)
    except KeyboardInterrupt:
        with t.lock:
            t.save()
        print("\nStats sauvegardees. A bientot.")


if __name__ == "__main__":
    main()