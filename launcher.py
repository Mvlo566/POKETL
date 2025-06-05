import os
import subprocess
import string
import threading
import time
from PIL import Image, ImageSequence
from blessed import Terminal

term = Terminal()

scripts_order = [
    "scraping_tournaments.py",
    "insert_wrk_cards.py",
    "insert_wrk_decklists.py",
    "insert_wrk_tournaments.py",
    "insert_wrk_players.py",
    "insert_wrk_matches.py",
    "insert_wrk_results.py"
]
selected_scripts = [True] * len(scripts_order)  # coche tous les scripts par défaut


animation_path = os.path.join(os.path.dirname(__file__), "GIF", "pikachu_loading.gif")
log_lines = []
frame_lines = []
menu_frame_lines = []
stop_event = threading.Event()
menu_stop_event = threading.Event()

current_script = ""
launch_count = 0
lock = threading.Lock()

# OUTILS

def keep_ascii(text):
    return ''.join(c if c in string.printable else '.' for c in text)

def remove_white_background(image):
    image = image.convert("RGBA")
    datas = image.getdata()
    new_data = [(0, 0, 0, 0) if r > 240 and g > 240 and b > 240 else (r, g, b, a)
                for (r, g, b, a) in datas]
    image.putdata(new_data)
    return image

def convert_frame_to_ascii(image, width):
    image = image.convert("RGBA")
    w, h = image.size
    new_height = int((h / w) * width * 0.55)
    image = image.resize((width, new_height))
    lines = []
    for y in range(new_height):
        line = ""
        for x in range(width):
            r, g, b, a = image.getpixel((x, y))
            if a == 0:
                line += " "
            else:
                line += term.color_rgb(r, g, b)("█")
        lines.append(line)
    return lines

# ANIMATIONS

def play_animation():
    try:
        with Image.open(animation_path) as im:
            frames = []
            durations = []
            for frame in ImageSequence.Iterator(im):
                clean = remove_white_background(frame.copy())
                frames.append(convert_frame_to_ascii(clean, width=60))
                durations.append(frame.info.get("duration", 80) / 1000)
            current = 0
            while not stop_event.is_set():
                frame_lines[:] = frames[current]
                time.sleep(durations[current])
                current = (current + 1) % len(frames)
    except Exception as e:
        frame_lines[:] = [f"[ERREUR GIF] {e}"]

def load_logo_ascii(image_path, width=60):
    try:
        with Image.open(image_path) as img:
            img = remove_white_background(img)
            return convert_frame_to_ascii(img, width)
    except Exception as e:
        return [f"[ERREUR LOGO] {e}"]

def show_menu():
    selected = 0

    # Texte ASCII à afficher en haut
    ascii_logo = [
        "                                                                                                 ",
        "8 888888888o       ,o888888o.     8 8888     ,88' 8 8888888888 8888888 8888888888 8 8888         ",
        "8 8888    `88.  . 8888     `88.   8 8888    ,88'  8 8888             8 8888       8 8888         ",
        "8 8888     `88 ,8 8888       `8b  8 8888   ,88'   8 8888             8 8888       8 8888         ",
        "8 8888     ,88 88 8888        `8b 8 8888  ,88'    8 8888             8 8888       8 8888         ",
        "8 8888.   ,88' 88 8888         88 8 8888 ,88'     8 888888888888     8 8888       8 8888         ",
        "8 888888888P'  88 8888         88 8 8888 88'      8 8888             8 8888       8 8888         ",
        "8 8888         88 8888        ,8P 8 888888<       8 8888             8 8888       8 8888         ",
        "8 8888         `8 8888       ,8P  8 8888 `Y8.     8 8888             8 8888       8 8888         ",
        "8 8888          ` 8888     ,88'   8 8888   `Y8.   8 8888             8 8888       8 8888         ",
        "8 8888             `8888888P'     8 8888     `Y8. 8 888888888888     8 8888       8 888888888888 "
    ]

    with term.fullscreen(), term.cbreak(), term.hidden_cursor():
        should_redraw = True
        while True:
            if should_redraw:
                print(term.clear)
                top_margin = 2
                for i, line in enumerate(ascii_logo):
                    x = max(0, (term.width - len(line)) // 2)
                    print(term.move_yx(top_margin + i, x) + term.bold_white(line))

                center_y = top_margin + len(ascii_logo) + 2
                print(term.move(center_y, 0) + term.center(term.bold_magenta("✨ POKEMON SCRIPTS LAUNCHER ✨")))

                for i, name in enumerate(scripts_order):
                    checked = "✅" if selected_scripts[i] else "⬜"
                    prefix = "👉 " if i == selected else "   "
                    style = term.bold_cyan if i == selected else term.white
                    line = f"{prefix}{checked} {name}"
                    print(term.move_yx(center_y + 2 + i, max(0, (term.width - len(line)) // 2)) + style(line))

                instructions = "[Entrée] Lancer  [Espace] Cocher/Décocher  [T] Tout  [Échap] Quitter"
                print(term.move_yx(center_y + len(scripts_order) + 4, 0) + term.center(term.yellow(instructions)))
                should_redraw = False

            key = term.inkey()  # Attend une touche
            if key.code == term.KEY_UP:
                selected = (selected - 1) % len(scripts_order)
                should_redraw = True
            elif key.code == term.KEY_DOWN:
                selected = (selected + 1) % len(scripts_order)
                should_redraw = True
            elif key == " ":
                selected_scripts[selected] = not selected_scripts[selected]
                should_redraw = True
            elif key.lower() == "t":
                all_selected = all(selected_scripts)
                selected_scripts[:] = [not all_selected] * len(scripts_order)
                should_redraw = True
            elif key.name == "KEY_ENTER" or key == "\n":
                return [s for s, sel in zip(scripts_order, selected_scripts) if sel]
            elif key.code == term.KEY_ESCAPE:
                return []


# EXECUTION DES SCRIPTS

def run_scripts(to_run):
    global current_script, launch_count
    root_dir = os.path.dirname(os.path.abspath(__file__))
    scripts_dir = os.path.join(root_dir, "scripts")

    for idx, script in enumerate(to_run, 1):
        with lock:
            current_script = script
            launch_count = idx

        log_lines.append(f"🚀 Lancement de {script}")
        path = os.path.join(scripts_dir, script)
        try:
            process = subprocess.Popen(
                ["python", "-u", path],
                cwd=root_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                env={**os.environ, "PYTHONIOENCODING": "utf-8"}
            )
            while True:
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                if line:
                    cleaned = line.strip()
                    log_lines.append(f"> {cleaned}")
                    if len(log_lines) > 10:
                        log_lines.pop(0)

            log_lines.append(f"✅ Fin de {script}")
            if len(log_lines) > 10:
                log_lines.pop(0)

        except Exception as e:
            log_lines.append(f"❌ Erreur {script}: {e}")

def run_scripts(to_run):
    global current_script, launch_count
    root_dir = os.path.dirname(os.path.abspath(__file__))
    scripts_dir = os.path.join(root_dir, "scripts")

    for idx, script in enumerate(to_run, 1):
        with lock:
            current_script = script
            launch_count = idx

        log_lines.append(f"🚀 Lancement de {script}")
        path = os.path.join(scripts_dir, script)
        try:
            process = subprocess.Popen(
                ["python", "-u", path],
                cwd=root_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                env={**os.environ, "PYTHONIOENCODING": "utf-8"}
            )
            while True:
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                if line:
                    cleaned = line.strip()
                    log_lines.append(f"> {cleaned}")
                    if len(log_lines) > 10:
                        log_lines.pop(0)

            log_lines.append(f"✅ Fin de {script}")
            if len(log_lines) > 10:
                log_lines.pop(0)

        except Exception as e:
            log_lines.append(f"❌ Erreur {script}: {e}")


# AFFICHAGE EN TEMPS RÉEL

def display_loop():
    global current_script, launch_count
    with term.fullscreen(), term.hidden_cursor():
        prev_frame = []
        prev_log1, prev_log2 = "", ""
        while not stop_event.is_set():
            log1 = log_lines[-2] if len(log_lines) >= 2 else ""
            log2 = log_lines[-1] if len(log_lines) >= 1 else ""

            if log1 != prev_log1:
                print(term.move_yx(0, 0) + term.clear_eol + term.bold_white(log1.ljust(term.width)))
                prev_log1 = log1
            if log2 != prev_log2:
                print(term.move_yx(1, 0) + term.clear_eol + term.bold_white(log2.ljust(term.width)))
                prev_log2 = log2

            frame = frame_lines[:]
            frame_height = len(frame)
            start_y = max(2, (term.height - frame_height) // 2)
            center_x = term.width // 2

            for i, line in enumerate(frame):
                y = start_y + i
                x = max(0, center_x - len(line) // 2)
                print(term.move_yx(y, 0) + term.clear_eol + term.move_yx(y, x) + line)

            with lock:
                script = current_script
                count = launch_count

            if script:
                print(term.move_yx(start_y + frame_height + 1, 0) + term.clear_eol +
                      term.bold_cyan(f"⚙️ {script}"))
                print(term.move_yx(start_y + frame_height + 2, 0) + term.clear_eol +
                      term.bold_yellow(f"📊 {count} / {len(scripts_order)}"))

            for i in range(len(frame), len(prev_frame)):
                y = start_y + i
                print(term.move_yx(y, 0) + term.clear_eol)

            prev_frame = frame
            time.sleep(0.03)

# MAIN

def main():
    to_run = show_menu()
    if to_run:
        animation_thread = threading.Thread(target=play_animation)
        display_thread = threading.Thread(target=display_loop)
        runner_thread = threading.Thread(target=run_scripts, args=(to_run,))

        animation_thread.start()
        display_thread.start()
        runner_thread.start()

        runner_thread.join()
        stop_event.set()
        animation_thread.join()
        display_thread.join()

        print(term.move(term.height, 0) + term.normal_cursor())
        print(term.bold_green("🎉 Tous les scripts ont été exécutés avec succès !"))
    else:
        print(term.bold_red("👋 Fermeture..."))


if __name__ == "__main__":
    main()
