from PyPDF2 import PdfReader, PdfWriter, PageObject
from reportlab.pdfgen import canvas
import io

def agregar_folio_encabezado_derecho_bajo(pdf_entrada, pdf_salida, inicio=1, margen_derecho=50, margen_superior=70):
    """
    Agrega números de página con el prefijo "Folio:" en el encabezado derecho de cada página de un PDF,
    posicionados más abajo en la página.

    :param pdf_entrada: Ruta al archivo PDF original.
    :param pdf_salida: Ruta donde se guardará el PDF con los números de página.
    :param inicio: Número desde el cual comenzará la numeración.
    :param margen_derecho: Puntos desde el borde derecho donde se colocará el texto.
    :param margen_superior: Puntos desde el borde superior donde se colocará el texto.
    """
    # Leer el PDF original
    reader = PdfReader(pdf_entrada)
    writer = PdfWriter()
    num_paginas = len(reader.pages)

    for i in range(num_paginas):
        pagina_original = reader.pages[i]

        # Obtener el tamaño de la página
        width = float(pagina_original.mediabox.width)
        height = float(pagina_original.mediabox.height)

        # Crear un PDF en memoria con el número de página
        packet = io.BytesIO()
        can = canvas.Canvas(packet, pagesize=(width, height))

        # Configurar el texto "Folio: X"
        folio_texto = f"Folio: {i + inicio}"
        font = "Helvetica-Bold"
        tamaño_fuente = 12
        can.setFont(font, tamaño_fuente)
        text_width = can.stringWidth(folio_texto, font, tamaño_fuente)

        # Posición del texto (superior derecho, más abajo)
        x = width - text_width - margen_derecho
        y = height - margen_superior

        can.drawString(x, y, folio_texto)
        can.save()

        # Mover el buffer al inicio
        packet.seek(0)
        folio_pdf = PdfReader(packet)
        pagina_folio = folio_pdf.pages[0]

        # Crear una nueva página combinada
        pagina_combinada = PageObject.create_blank_page(
            width=pagina_original.mediabox.width,
            height=pagina_original.mediabox.height
        )

        # Añadir la página original
        pagina_combinada.merge_page(pagina_original)

        # Añadir la página del folio
        pagina_combinada.merge_page(pagina_folio)

        # Añadir la página combinada al writer
        writer.add_page(pagina_combinada)

        print(f"Procesando página {i + 1} de {num_paginas}...")

    # Escribir el PDF de salida
    with open(pdf_salida, "wb") as f_out:
        writer.write(f_out)

    print(f"\nFolios agregados y guardados en '{pdf_salida}'.")

if __name__ == "__main__":
    # Reemplaza estos nombres con las rutas de tus archivos
    pdf_entrada = "original.pdf"    # Archivo PDF original
    pdf_salida = "numerado.pdf"     # Archivo PDF de salida con folios

    # Llamada a la función con márgenes ajustados
    agregar_folio_encabezado_derecho_bajo(
        pdf_entrada=pdf_entrada,
        pdf_salida=pdf_salida,
        inicio=1,
        margen_derecho=50,     # Ajusta este valor si deseas más o menos espacio desde el borde derecho
        margen_superior=70    # Aumenta este valor para posicionar el folio más abajo (a mayor margen, más abajo)
    )
