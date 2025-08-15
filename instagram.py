import json
import os
from instagrapi import Client
from datetime import datetime, timedelta
import pytz
import tkinter as tk
from tkinter import messagebox, ttk, filedialog
import threading
import time

# ==================== CONFIG ====================
SESSION_FILE = "session.json"
CREDENTIALS_FILE = "credentials.json"
LOG_FILE = "post_log.txt"
BG_COLOR = "#f7f9fc"     # Cor de fundo
BTN_COLOR = "#4a90e2"    # Azul do botão
BTN_HOVER = "#357abd"    # Azul mais escuro
FONT_MAIN = ("Segoe UI", 11)
FONT_TITLE = ("Segoe UI", 14, "bold")
VALID_EXTENSIONS = (".png", ".jpg", ".jpeg")

# ==================== FUNÇÕES ====================
def load_credentials():
    if os.path.exists(CREDENTIALS_FILE):
        with open(CREDENTIALS_FILE, 'r') as f:
            return json.load(f)
    return None

def save_credentials(username, password):
    with open(CREDENTIALS_FILE, 'w') as f:
        json.dump({"username": username, "password": password}, f)

def log_result(message):
    with open(LOG_FILE, 'a') as f:
        f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: {message}\n")

def login_instagram(username, password):
    cl = Client()
    if os.path.exists(SESSION_FILE):
        cl.load_settings(SESSION_FILE)
        try:
            cl.login(username, password)
            return cl
        except Exception as e:
            log_result(f"Erro ao usar sessão existente: {str(e)}")
            return None

    try:
        cl.login(username, password)
        cl.dump_settings(SESSION_FILE)
        return cl
    except Exception as e:
        log_result(f"Erro de login: {str(e)}")
        return None

def post_image(client, photo_path, caption, schedule_time, image_name, result_label):
    try:
        if not os.path.exists(photo_path):
            raise FileNotFoundError(f"Arquivo {photo_path} não encontrado.")
        
        media = client.photo_upload(path=photo_path, caption=caption)
        result = f"{image_name} às {schedule_time.strftime('%Y-%m-%d %H:%M')}: ✅ Postagem enviada com sucesso! ID: {media.id}"
        log_result(result)
        update_result_label(result, "green")
    except Exception as e:
        result = f"{image_name} às {schedule_time.strftime('%Y-%m-%d %H:%M')}: ❌ Erro ao postar: {str(e)}"
        log_result(result)
        update_result_label(result, "red")

def update_result_label(text, color):
    current_text = result_label.cget("text")
    new_text = current_text + "\n" + text if current_text else text
    result_label.config(text=new_text, foreground=color)

def parse_times(times_input, base_date):
    try:
        times = [t.strip() for t in times_input.split(",")]
        schedule_times = []
        for t in times:
            time_obj = datetime.strptime(t, "%H:%M")
            schedule_time = base_date.replace(
                hour=time_obj.hour,
                minute=time_obj.minute,
                second=0,
                microsecond=0
            )
            schedule_times.append(schedule_time)
        return sorted(schedule_times)
    except ValueError:
        raise ValueError("Formato de horários inválido. Use HH:MM,HH:MM,HH:MM (ex.: 09:00,12:00,15:00).")

def select_folder():
    folder_path = filedialog.askdirectory(title="Selecionar Pasta de Imagens")
    if folder_path:
        folder_path_entry.delete(0, tk.END)
        folder_path_entry.insert(0, folder_path)

def schedule_post_gui():
    username = username_entry.get()
    password = password_entry.get()
    folder_path = folder_path_entry.get()
    caption = caption_entry.get("1.0", tk.END).strip()
    schedule_input = schedule_time_entry.get()
    times_input = times_entry.get()

    if not all([username, password, folder_path, caption, schedule_input, times_input]):
        messagebox.showerror("Erro", "Por favor, preencha todos os campos.")
        return

    try:
        base_date = datetime.strptime(schedule_input, "%Y-%m-%d")
        base_date = pytz.timezone("America/Sao_Paulo").localize(base_date)
    except ValueError:
        messagebox.showerror("Erro", "Formato de data inválido. Use AAAA-MM-DD.")
        return

    try:
        schedule_times = parse_times(times_input, base_date)
    except ValueError as e:
        messagebox.showerror("Erro", str(e))
        return

    # Listar imagens na pasta
    image_files = [f for f in os.listdir(folder_path) if f.lower().endswith(VALID_EXTENSIONS)]
    if not image_files:
        messagebox.showerror("Erro", "Nenhuma imagem válida encontrada na pasta.")
        return

    if len(image_files) > len(schedule_times):
        messagebox.showerror("Erro", f"Mais imagens ({len(image_files)}) do que horários ({len(schedule_times)}). Adicione mais horários.")
        return

    # Verificar login
    save_credentials(username, password)
    client = login_instagram(username, password)
    if not client:
        result_label.config(text="❌ Falha no login.", foreground="red")
        return

    # Agendar postagens
    results = []
    current_time = datetime.now(pytz.timezone("America/Sao_Paulo"))

    for i, image_file in enumerate(image_files):
        photo_path = os.path.join(folder_path, image_file)
        if not os.path.exists(photo_path):
            results.append(f"{image_file}: ❌ Arquivo não encontrado.")
            continue
        schedule_time = schedule_times[i]
        time_diff = (schedule_time - current_time).total_seconds()

        if time_diff < 0:
            results.append(f"{image_file}: ❌ Horário {schedule_time.strftime('%Y-%m-%d %H:%M')} já passou.")
            continue

        # Agendar postagem com threading.Timer
        threading.Timer(time_diff, post_image, args=(
            client, photo_path, caption, schedule_time, image_file, result_label
        )).start()
        results.append(f"{image_file}: Agendado para {schedule_time.strftime('%Y-%m-%d %H:%M')}")

    result_label.config(text="\n".join(results), foreground="blue")
    messagebox.showinfo("Sucesso", "Postagens agendadas com sucesso! Mantenha o programa aberto até que todas as postagens sejam concluídas.")

# ==================== INTERFACE ====================
root = tk.Tk()
root.title("📅 Agendador de Postagens - Instagram")
root.geometry("450x620")
root.configure(bg=BG_COLOR)
root.resizable(False, False)

# ====== ESTILO ======
style = ttk.Style()
style.theme_use("clam")
style.configure("TLabel", background=BG_COLOR, font=FONT_MAIN)
style.configure("TEntry", padding=5, font=FONT_MAIN)
style.configure("TButton", font=FONT_MAIN, background=BTN_COLOR, foreground="white")
style.map("TButton",
          background=[("active", BTN_HOVER)],
          foreground=[("active", "white")])

# ====== TÍTULO ======
title_label = tk.Label(root, text="Agendador de Postagens", font=FONT_TITLE, bg=BG_COLOR, fg="#333")
title_label.pack(pady=15)

# ====== FRAME CAMPOS ======
form_frame = tk.Frame(root, bg=BG_COLOR)
form_frame.pack(pady=5)

def create_field(label_text, is_password=False):
    tk.Label(form_frame, text=label_text, font=FONT_MAIN, bg=BG_COLOR).pack(pady=(10, 2), anchor="w")
    entry = ttk.Entry(form_frame, show="*" if is_password else "")
    entry.pack(fill="x", padx=5)
    return entry

username_entry = create_field("Usuário:")
password_entry = create_field("Senha:", is_password=True)

# ====== CAMPO DE PASTA COM BOTÃO ======
tk.Label(form_frame, text="Pasta de Imagens:", font=FONT_MAIN, bg=BG_COLOR).pack(pady=(10, 2), anchor="w")
folder_frame = tk.Frame(form_frame, bg=BG_COLOR)
folder_frame.pack(fill="x", padx=5)
folder_path_entry = ttk.Entry(folder_frame)
folder_path_entry.pack(side="left", fill="x", expand=True)
select_button = ttk.Button(folder_frame, text="📁 Selecionar", command=select_folder)
select_button.pack(side="right", padx=(5, 0))

tk.Label(form_frame, text="Legenda:", font=FONT_MAIN, bg=BG_COLOR).pack(pady=(10, 2), anchor="w")
caption_entry = tk.Text(form_frame, height=4, font=FONT_MAIN)
caption_entry.pack(fill="x", padx=5)

schedule_time_entry = create_field("Data Inicial (AAAA-MM-DD):")
times_entry = create_field("Horários (HH:MM,HH:MM,HH:MM):")

# ====== BOTÃO ======
schedule_button = ttk.Button(root, text="🚀 Agendar Postagens", command=schedule_post_gui)
schedule_button.pack(pady=20, ipadx=10, ipady=5)

# ====== RESULTADO ======
result_label = tk.Label(root, text="", bg=BG_COLOR, font=("Segoe UI", 10), wraplength=380, justify="center")
result_label.pack(pady=10)

root.mainloop()
