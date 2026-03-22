import streamlit as st
import anthropic
import PyPDF2
import base64
import io
from PIL import Image
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH

# ─── CONFIGURACIÓN DE PÁGINA ───
st.set_page_config(
    page_title="Asistente Jurídico",
    page_icon="⚖️",
    layout="centered"
)

# ─── CSS PERSONALIZADO ───
st.markdown("""
<style>
    /* Header de la app */
    .app-header {
        background: #1a2744;
        padding: 16px 24px;
        border-radius: 10px 10px 0 0;
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 0;
    }
    .app-header-left {
        display: flex;
        align-items: center;
        gap: 12px;
    }
    .app-logo {
        width: 36px;
        height: 36px;
        background: #c9a84c;
        border-radius: 6px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 18px;
    }
    .app-title {
        color: white;
        font-size: 15px;
        font-weight: 600;
        margin: 0;
    }
    .app-subtitle {
        color: rgba(255,255,255,0.5);
        font-size: 11px;
        margin: 0;
    }
    .app-user-badge {
        background: #1a2744;
        border: 1px solid rgba(255,255,255,0.3);
        border-radius: 4px;
        padding: 4px 10px;
        color: white;
        font-size: 10px;
        letter-spacing: 0.5px;
    }
    /* Pasos del análisis */
    .paso-badge {
        background: #1a2744;
        border-radius: 3px;
        padding: 2px 8px;
        color: white;
        font-size: 10px;
        font-weight: 600;
        display: inline-block;
        margin-bottom: 4px;
        letter-spacing: 0.5px;
    }
    .paso-card {
        background: #f8f9fa;
        border-radius: 8px;
        padding: 12px 16px;
        border-left: 3px solid #1a2744;
        margin-bottom: 10px;
    }
    /* Botones de acción */
    .stDownloadButton > button {
        background: #1a2744 !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 10px 20px !important;
        font-weight: 500 !important;
        width: 100% !important;
    }
    .stButton > button {
        background: #1a2744 !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 10px 20px !important;
        font-weight: 500 !important;
        width: 100% !important;
    }
    /* Ocultar elementos de Streamlit */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ─── SYSTEM PROMPT ───
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

USUARIOS
Adaptá el nivel de detalle según el perfil:
- Titular o senior: comunicación directa, foco en estrategia.
- Junior o pasante: incluí el razonamiento detrás de cada decisión.

PROTOCOLO DE CITAS JURÍDICAS
Toda cita se clasifica obligatoriamente:
✓ CONFIRMADO: legislación vigente con artículo citado
⚠ PROBABLE: doctrina mayoritaria, verificar antes de citar
✗ A VERIFICAR: requiere confirmación en base oficial

LÍMITES
No afirmás resultados judiciales con certeza.
No tomás decisiones procesales.
Advertís cuando una consulta está fuera del área de especialización.

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

# ─── FUNCIONES ───
def analizar_pdf_digital(archivo_bytes):
    lector = PyPDF2.PdfReader(io.BytesIO(archivo_bytes))
    texto = ""
    for pagina in lector.pages:
        texto += pagina.extract_text() or ""
    return texto

def analizar_pdf_escaneado(archivo_bytes):
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

def obtener_analisis(contenido, es_imagen=False, prompt_extra=""):
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
        texto_final = "Analizá este documento jurídico y aplicá el flujo completo de 5 pasos."
        if prompt_extra:
            texto_final = prompt_extra
        mensaje_contenido.append({"type": "text", "text": texto_final})
    else:
        if prompt_extra:
            mensaje_contenido = f"{prompt_extra}\n\n{contenido}"
        else:
            mensaje_contenido = f"Analizá este documento jurídico y aplicá el flujo completo de 5 pasos:\n\n{contenido}"
    
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": mensaje_contenido}]
    )
    return message.content[0].text

def generar_word(texto_analisis, nombre_documento):
    doc = Document()
    titulo = doc.add_heading('ANÁLISIS JURÍDICO', 0)
    titulo.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitulo = doc.add_paragraph(f'Documento: {nombre_documento}')
    subtitulo.alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph('─' * 60)
    lineas = texto_analisis.split('\n')
    for linea in lineas:
        linea = linea.strip()
        if not linea:
            doc.add_paragraph('')
            continue
        if linea.startswith('###') or linea.startswith('##'):
            doc.add_heading(linea.replace('###','').replace('##','').strip(), level=2)
        elif linea.startswith('#'):
            doc.add_heading(linea.replace('#','').strip(), level=1)
        elif linea.startswith('**') and linea.endswith('**'):
            p = doc.add_paragraph()
            run = p.add_run(linea.replace('**',''))
            run.bold = True
        elif linea.startswith('- ') or linea.startswith('* '):
            doc.add_paragraph(linea[2:], style='List Bullet')
        elif linea.startswith('✓') or linea.startswith('⚠') or linea.startswith('✗'):
            doc.add_paragraph(linea, style='List Bullet')
        else:
            doc.add_paragraph(linea)
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# ─── HEADER ───
nombre_estudio = st.secrets.get("NOMBRE_ESTUDIO", "Estudio Jurídico")
nombre_usuario = st.secrets.get("NOMBRE_USUARIO", "Dr./Dra.")

st.markdown(f"""
<div class="app-header">
    <div class="app-header-left">
        <div class="app-logo">⚖️</div>
        <div>
            <p class="app-title">{nombre_estudio}</p>
            <p class="app-subtitle">Asistente jurídico con IA</p>
        </div>
    </div>
    <div class="app-user-badge">{nombre_usuario}</div>
</div>
""", unsafe_allow_html=True)

st.markdown("<div style='height: 16px'></div>", unsafe_allow_html=True)

# ─── UPLOAD ───
st.markdown("**Documento a analizar**")
archivo = st.file_uploader(
    "Subí el PDF del caso",
    type=['pdf'],
    help="Compatible con PDFs digitales y escaneados",
    label_visibility="collapsed"
)

if archivo:
    st.success(f"✓ {archivo.name}")
    
    if st.button("Analizar documento"):
        with st.spinner("Analizando... esto puede tomar unos segundos"):
            archivo_bytes = archivo.read()
            try:
                texto = analizar_pdf_digital(archivo_bytes)
                if len(texto.strip()) > 100:
                    st.info("📄 PDF digital detectado")
                    resultado = obtener_analisis(texto)
                    contenido_guardado = texto
                    es_imagen_guardada = False
                else:
                    raise ValueError("Texto insuficiente")
            except:
                st.info("🖼️ PDF escaneado — procesando con Vision")
                imagenes = analizar_pdf_escaneado(archivo_bytes)
                resultado = obtener_analisis(imagenes, es_imagen=True)
                contenido_guardado = imagenes
                es_imagen_guardada = True
            
            st.session_state['resultado'] = resultado
            st.session_state['contenido'] = contenido_guardado
            st.session_state['es_imagen'] = es_imagen_guardada
            st.session_state['nombre_archivo'] = archivo.name

# ─── RESULTADO ───
if 'resultado' in st.session_state:
    resultado = st.session_state['resultado']
    
    st.markdown("---")
    st.markdown("🟢 **Análisis completado**")
    st.markdown(resultado)
    
    st.markdown("<div style='height: 8px'></div>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        word_buffer = generar_word(resultado, st.session_state['nombre_archivo'])
        st.download_button(
            label="⬇️ Descargar Word editable",
            data=word_buffer,
            file_name=f"analisis_{st.session_state['nombre_archivo'].replace('.pdf','')}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
    
    with col2:
        if st.button("✍️ Redactar contestación"):
            with st.spinner("Redactando contestación..."):
                prompt_redaccion = """Basándote en el análisis anterior, redactá una contestación de demanda completa en formato procesal argentino. 
                El escrito debe estar listo para editar y presentar. 
                Marcá con [COMPLETAR: descripción] los campos donde el abogado debe agregar datos específicos."""
                
                contestacion = obtener_analisis(
                    st.session_state['contenido'],
                    es_imagen=st.session_state['es_imagen'],
                    prompt_extra=prompt_redaccion
                )
                st.session_state['contestacion'] = contestacion
    
    if 'contestacion' in st.session_state:
        st.markdown("---")
        st.markdown("✍️ **Contestación redactada**")
        st.markdown(st.session_state['contestacion'])
        
        word_contestacion = generar_word(
            st.session_state['contestacion'],
            f"contestacion_{st.session_state['nombre_archivo']}"
        )
        st.download_button(
            label="⬇️ Descargar contestación en Word",
            data=word_contestacion,
            file_name=f"contestacion_{st.session_state['nombre_archivo'].replace('.pdf','')}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            key="dl_contestacion"
        )
