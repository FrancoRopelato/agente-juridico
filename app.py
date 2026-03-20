import streamlit as st
import anthropic
import PyPDF2
import base64
import io
from PIL import Image

# Configuración de la página
st.set_page_config(
    page_title="Asistente Jurídico",
    page_icon="⚖️",
    layout="centered"
)

# Título y descripción
st.title("⚖️ Asistente Jurídico")
st.markdown("Subí un documento jurídico en PDF y recibí un análisis profesional completo.")

# System prompt
SYSTEM_PROMPT = """
Sos un asistente jurídico profesional especializado 
en derecho argentino. Tu función es asistir a los 
profesionales del estudio en el análisis de casos, 
elaboración de estrategias procesales y redacción 
de documentos judiciales y extrajudiciales.

No sos un abogado. No ejercés la profesión. Toda 
decisión procesal y todo documento generado requiere 
revisión y aprobación del profesional autorizado 
antes de cualquier uso oficial.

PROTOCOLO DE CITAS JURÍDICAS
Toda cita se clasifica obligatoriamente:
✓ CONFIRMADO: legislación vigente con artículo citado
⚠ PROBABLE: doctrina mayoritaria, verificar antes de citar
✗ A VERIFICAR: requiere confirmación en base oficial

FLUJO DE TRABAJO OBLIGATORIO
Paso 1 - Comprensión: identificar proceso, partes, datos faltantes.
Paso 2 - Análisis: hechos, puntos controvertidos, argumentos.
Paso 3 - Estrategia: procesal y de negociación, ventajas y riesgos.
Paso 4 - Redacción: formato procesal argentino, citas clasificadas.
Paso 5 - Revisión: solidez argumental, coherencia, debilidades.

CIERRE OBLIGATORIO
─────────────────────────────
REVISIÓN PROFESIONAL REQUERIDA
PRÓXIMOS PASOS SUGERIDOS: [acciones en orden]
DATOS PENDIENTES: [campos COMPLETAR]
CITAS A VERIFICAR: [citas marcadas con ✗]
─────────────────────────────
"""

def analizar_pdf_digital(archivo_bytes):
    """Extrae texto de PDF digital."""
    lector = PyPDF2.PdfReader(io.BytesIO(archivo_bytes))
    texto = ""
    for pagina in lector.pages:
        texto += pagina.extract_text() or ""
    return texto

def analizar_pdf_escaneado(archivo_bytes):
    """Procesa PDF escaneado como imágenes."""
    from pdf2image import convert_from_bytes
    paginas = convert_from_bytes(archivo_bytes, dpi=100)
    imagenes = []
    for pagina in paginas:
        pagina.thumbnail((1500, 1500), Image.LANCZOS)
        buffer = io.BytesIO()
        pagina.save(buffer, format='JPEG', quality=75)
        imagen_b64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        imagenes.append(imagen_b64)
    return imagenes

def obtener_analisis(contenido, es_imagen=False):
    """Manda el contenido a Claude y obtiene el análisis."""
    client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
    
    if es_imagen:
        mensaje_contenido = []
        for img in contenido:
            mensaje_contenido.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": img
                }
            })
        mensaje_contenido.append({
            "type": "text",
            "text": "Analizá este documento jurídico y aplicá el flujo completo de 5 pasos."
        })
    else:
        mensaje_contenido = f"Analizá este documento jurídico y aplicá el flujo completo de 5 pasos:\n\n{contenido}"
    
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": mensaje_contenido}]
    )
    return message.content[0].text

# Interfaz principal
archivo = st.file_uploader(
    "Seleccioná el documento PDF",
    type=['pdf'],
    help="Podés subir PDFs digitales o escaneados"
)

if archivo:
    st.success(f"✓ Documento recibido: {archivo.name}")
    
    if st.button("🔍 Analizar documento", type="primary"):
        with st.spinner("Analizando documento... esto puede tomar unos segundos"):
            
            archivo_bytes = archivo.read()
            
            # Intentar como PDF digital primero
            try:
                texto = analizar_pdf_digital(archivo_bytes)
                if len(texto.strip()) > 100:
                    st.info("📄 PDF digital detectado")
                    resultado = obtener_analisis(texto, es_imagen=False)
                else:
                    raise ValueError("Texto insuficiente")
            except:
                st.info("🖼️ PDF escaneado detectado — procesando con Vision")
                imagenes = analizar_pdf_escaneado(archivo_bytes)
                resultado = obtener_analisis(imagenes, es_imagen=True)
        
        st.success("✓ Análisis completado")
        st.markdown("---")
        st.markdown(resultado)
        
        # Botón para descargar el análisis
        st.download_button(
            label="⬇️ Descargar análisis",
            data=resultado,
            file_name=f"analisis_{archivo.name}.txt",
            mime="text/plain"
        )
