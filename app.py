import os
import streamlit as st
from bokeh.models.widgets import Button
from bokeh.models import CustomJS
from streamlit_bokeh_events import streamlit_bokeh_events
from PIL import Image
import time
import paho.mqtt.client as paho
import json

# ==========================================
# 1. ARQUITECTURA MQTT (Hilo en segundo plano)
# ==========================================
# st.cache_resource asegura que la conexión se cree solo una vez y no en cada recarga
@st.cache_resource
def init_mqtt_client():
    broker = "broker.mqttdashboard.com"
    port = 1883
    
    # Se recomienda un ID único para evitar desconexiones si hay otro cliente con el mismo ID
    client = paho.Client("GIT-HUBCSAMUEL-WEB-UI") 

    def on_publish(client, userdata, result):
        print("El dato ha sido publicado en el broker MQTT.\n")

    def on_message(client, userdata, message):
        # Nota: Actualizar la UI de Streamlit directamente desde este hilo de callback es complicado.
        # Por ahora, solo imprimimos en consola.
        msg = str(message.payload.decode("utf-8"))
        print(f"Mensaje recibido: {msg}")

    client.on_publish = on_publish
    client.on_message = on_message

    try:
        client.connect(broker, port)
        # ESTA ES LA MAGIA DEL THREADING:
        # loop_start() maneja la red en un hilo separado de forma automática.
        client.loop_start() 
    except Exception as e:
        print(f"Error conectando al broker MQTT: {e}")

    return client

# Inicializamos el cliente al cargar la app
mqtt_client = init_mqtt_client()


# ==========================================
# 2. INTERFAZ MULTIMODAL DE STREAMLIT
# ==========================================
st.title("INTERFACES MULTIMODALES")
st.subheader("CONTROL POR VOZ")

# Manejo seguro de la imagen por si el archivo no se encuentra
try:
    image = Image.open('voice_ctrl.jpg')
    st.image(image, width=200)
except FileNotFoundError:
    st.warning("⚠️ No se encontró la imagen 'voice_ctrl.jpg'.")

st.write("Toca el Botón y habla ")

# Botón de Bokeh que invoca el JavaScript de Web Speech API
stt_button = Button(label=" Inicio ", width=200)

# Agregué "recognition.lang = 'es-ES';" para asegurar una mejor transcripción en español
stt_button.js_on_event("button_click", CustomJS(code="""
    var recognition = new webkitSpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = 'es-ES'; 
 
    recognition.onresult = function (e) {
        var value = "";
        for (var i = e.resultIndex; i < e.results.length; ++i) {
            if (e.results[i].isFinal) {
                value += e.results[i][0].transcript;
            }
        }
        if ( value != "") {
            document.dispatchEvent(new CustomEvent("GET_TEXT", {detail: value}));
        }
    }
    recognition.start();
"""))

result = streamlit_bokeh_events(
    stt_button,
    events="GET_TEXT",
    key="listen",
    refresh_on_update=False,
    override_height=75,
    debounce_time=0
)

# ==========================================
# 3. PROCESAMIENTO DE VOZ Y PUBLICACIÓN MQTT
# ==========================================
if result and "GET_TEXT" in result:
    # Capturamos el texto, le quitamos espacios extra y lo pasamos a minúsculas para facilitar la comparación
    texto_hablado = result.get("GET_TEXT").strip().lower()
    st.info(f"🗣️ Escuchado: '{texto_hablado}'")
    
    # Lógica de detección de la palabra clave
    if "abrir" in texto_hablado:
        st.success("✅ ¡Comando 'abrir' detectado! Ejecutando acción en MQTT...")
        
        # Preparamos el payload en JSON
        payload = json.dumps({
            "comando": "abrir", 
            "texto_original": texto_hablado
        })
        
        # Publicamos usando el cliente que ya está conectado en el hilo de segundo plano
        mqtt_client.publish("samuel/comandos", payload)
    else:
        st.warning("No se detectó el comando. Di la palabra 'abrir' para activar la publicación.")

# Creación del directorio temporal
try:
    os.makedirs("temp", exist_ok=True)
except Exception:
    pass
