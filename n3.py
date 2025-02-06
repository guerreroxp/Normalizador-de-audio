import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk  # Para manejar la imagen del splash screen
import ffmpeg
import threading
import subprocess

# Función para mostrar el splash screen con la imagen sp.png
def mostrar_splash_screen():
    splash = tk.Toplevel()
    splash.overrideredirect(True)  # Eliminar bordes y barra de título

    try:
        # Cargar la imagen sp.png
        imagen = Image.open("sp.png")
        imagen_tk = ImageTk.PhotoImage(imagen)

        # Mostrar la imagen en un label
        label_imagen = tk.Label(splash, image=imagen_tk)
        label_imagen.pack()

        # Centrar la ventana en la pantalla
        ancho_ventana = imagen.width
        alto_ventana = imagen.height
        ancho_pantalla = splash.winfo_screenwidth()
        alto_pantalla = splash.winfo_screenheight()
        x = (ancho_pantalla // 2) - (ancho_ventana // 2)
        y = (alto_pantalla // 2) - (alto_ventana // 2)
        splash.geometry(f"{ancho_ventana}x{alto_ventana}+{x}+{y}")

        # Cerrar el splash screen después de 3 segundos
        splash.after(3000, splash.destroy)

        # Mantener una referencia a la imagen para evitar que sea eliminada por el recolector de basura
        splash.imagen_tk = imagen_tk

        # Mostrar la ventana de splash
        splash.update()
    except Exception as e:
        messagebox.showerror("Error", f"No se pudo cargar la imagen del splash screen: {e}")
        splash.destroy()

# Función para analizar el volumen
def analizar_volumen(input_file):
    try:
        cmd = (
            ffmpeg
            .input(input_file)
            .filter('volumedetect')
            .output('null', format='null')
            .compile()
        )
        result = subprocess.run(cmd, stderr=subprocess.PIPE, text=True)
        for line in result.stderr.split('\n'):
            if 'mean_volume:' in line:
                volumen = float(line.split('mean_volume:')[1].split('dB')[0].strip())
                return volumen
        raise ValueError("No se pudo encontrar el volumen en la salida de FFmpeg.")
    except Exception as e:
        messagebox.showerror("Error", f"No se pudo analizar el volumen del archivo {input_file}: {e}")
        return None

# Función para ajustar la ganancia
def ajustar_ganancia_con_metadatos(input_file, output_file, ganancia_db):
    try:
        cmd = (
            ffmpeg
            .input(input_file)
            .output(output_file, af=f"volume={ganancia_db}dB", **{'map_metadata': '0', 'c:a': 'flac'})
            .compile()
        )
        result = subprocess.run(cmd, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            raise Exception(result.stderr)
        print(f"Archivo ajustado guardado en: {output_file}")
    except Exception as e:
        messagebox.showerror("Error", f"Error al ajustar la ganancia del archivo {input_file}:\n{e}")

# Función para cargar la carpeta
def cargar_carpeta(carpeta, lista_archivos):
    archivos = os.listdir(carpeta)
    archivos_audio = [f for f in archivos if f.lower().endswith(('.mp3', '.flac', '.wav', '.aiff'))]
    for archivo in archivos_audio:
        input_path = os.path.join(carpeta, archivo)
        volumen_original = analizar_volumen(input_path)
        if volumen_original is not None:
            lista_archivos.insert(tk.END, f"Archivo: {archivo} - Volumen original: {volumen_original} dB")

# Función para seleccionar carpeta
def seleccionar_carpeta():
    carpeta = filedialog.askdirectory()
    if carpeta:
        lista_archivos.delete(0, tk.END)
        barra_progreso['value'] = 0
        cargar_carpeta(carpeta, lista_archivos)
        return carpeta
    return None

# Función para normalizar archivos
def normalizar_archivos(carpeta, db_normalizacion, lista_archivos, barra_progreso, opcion_guardado):
    archivos = os.listdir(carpeta)
    archivos_audio = [f for f in archivos if f.lower().endswith(('.mp3', '.flac', '.wav', '.aiff'))]
    total_archivos = len(archivos_audio)
    resultados = []

    for idx, archivo in enumerate(archivos_audio):
        input_path = os.path.join(carpeta, archivo)
        if opcion_guardado == "crear":
            output_path = os.path.join(carpeta, f"{os.path.splitext(archivo)[0]}_normalizado{os.path.splitext(archivo)[1]}")
        elif opcion_guardado == "reemplazar":
            output_path = os.path.join(carpeta, f"{os.path.splitext(archivo)[0]}_temp{os.path.splitext(archivo)[1]}")

        volumen_original = analizar_volumen(input_path)
        if volumen_original is None:
            continue

        ganancia_db = db_normalizacion - volumen_original
        ajustar_ganancia_con_metadatos(input_path, output_path, ganancia_db)

        if opcion_guardado == "reemplazar":
            os.replace(output_path, input_path)
            output_path = input_path

        volumen_normalizado = analizar_volumen(output_path)
        resultados.append(f"Archivo: {archivo}")
        resultados.append(f"  Volumen original: {volumen_original} dB")
        resultados.append(f"  Volumen normalizado: {volumen_normalizado} dB")
        resultados.append("")

        lista_archivos.insert(tk.END, f"Procesado: {archivo}")
        lista_archivos.insert(tk.END, f"  Original: {volumen_original} dB")
        lista_archivos.insert(tk.END, f"  Normalizado: {volumen_normalizado} dB")
        lista_archivos.yview(tk.END)
        barra_progreso['value'] = (idx + 1) / total_archivos * 100
        root.update_idletasks()

    with open(os.path.join(carpeta, "resultados_normalizacion.txt"), "w") as f:
        f.write("\n".join(resultados))

    messagebox.showinfo("Completado", "Proceso de normalización finalizado.")

# Función para iniciar la normalización
def iniciar_normalizacion():
    carpeta = seleccionar_carpeta()
    if carpeta:
        try:
            db_normalizacion = float(entry_db.get())
        except ValueError:
            messagebox.showerror("Error", "Por favor, ingresa un valor válido para los dB de normalización.")
            return

        opcion_guardado = var_guardado.get()
        hilo = threading.Thread(target=normalizar_archivos, args=(carpeta, db_normalizacion, lista_archivos, barra_progreso, opcion_guardado))
        hilo.start()

# Interfaz gráfica principal
root = tk.Tk()
root.withdraw()  # Ocultar la ventana principal temporalmente

# Mostrar el splash screen
mostrar_splash_screen()

# Esperar 3 segundos antes de mostrar la ventana principal
root.after(3000, root.deiconify)  # Mostrar la ventana principal después del splash screen

# Configuración de la ventana principal
root.title("Normalizador de Audio")
root.geometry("1000x550")

# Frame para dB de normalización
frame_db = tk.Frame(root)
frame_db.pack(pady=10)

label_db = tk.Label(frame_db, text="dB de normalización:")
label_db.pack(side=tk.LEFT, padx=10)

entry_db = tk.Entry(frame_db)
entry_db.pack(side=tk.LEFT, padx=10)
entry_db.insert(0, "-23")  # Valor predeterminado

# Opciones de guardado
frame_guardado = tk.Frame(root)
frame_guardado.pack(pady=10)

var_guardado = tk.StringVar(value="crear")  # Valor predeterminado: Crear archivo normalizado

radio_crear = tk.Radiobutton(frame_guardado, text="Crear archivo normalizado", variable=var_guardado, value="crear")
radio_reemplazar = tk.Radiobutton(frame_guardado, text="Reemplazar archivo original", variable=var_guardado, value="reemplazar")

radio_crear.pack(side=tk.LEFT, padx=10)
radio_reemplazar.pack(side=tk.LEFT, padx=10)

# Lista de archivos
lista_archivos = tk.Listbox(root, width=80, height=15)
lista_archivos.pack(pady=10)

# Barra de progreso
barra_progreso = ttk.Progressbar(root, length=800, mode="determinate")
barra_progreso.pack(pady=10)

# Botones
boton_cargar = tk.Button(root, text="Cargar Carpeta", command=seleccionar_carpeta)
boton_cargar.pack(pady=10)

boton_iniciar = tk.Button(root, text="Iniciar Normalización", command=iniciar_normalizacion)
boton_iniciar.pack(pady=10)

# Iniciar la aplicación principal
root.mainloop()