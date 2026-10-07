import io
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from models.mensaje import CuotaModel

class ReciboService:
    @staticmethod
    def generar_pdf_recibo(id_cuota, vendedor_nombre=""):
        cuota = CuotaModel.obtener_detalle_recibo(id_cuota)
        if not cuota:
            return None

        buffer = io.BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=letter)
        
        # Encabezado
        pdf.rect(40, 650, 520, 100)
        pdf.setFont("Helvetica-Bold", 16)
        pdf.drawString(380, 720, "SORTIS-MOTOS")
        pdf.setFont("Helvetica", 10)
        pdf.drawString(380, 700, "San José de Metán")
        pdf.drawString(380, 670, f"Vendedor: {vendedor_nombre}")

        # Título y Detalle
        pdf.setFont("Helvetica-Bold", 14)
        pdf.drawString(40, 620, "RECIBO DE PAGO")
        
        pdf.rect(40, 380, 520, 220)
        pdf.setFont("Helvetica", 11)
        pdf.drawString(50, 580, f"Identificador: {id_cuota}")
        pdf.drawString(50, 560, f"Recibí de: {cuota['apenomb']}")
        pdf.drawString(50, 540, f"La cantidad de Pesos: ${cuota['importe']}")
        pdf.drawString(50, 520, f"En concepto de Pago cuota N°: {cuota['numcuota']}")
        pdf.drawString(50, 500, f"Fecha de Vencimiento: {str(cuota['fechavenc'])}")
        pdf.drawString(50, 480, f"Fecha de Pago: {str(cuota['fechapago'])}")
        pdf.drawString(50, 460, f"Estado: {cuota['estado']}")
        pdf.drawString(50, 440, f"Observaciones: {cuota['obs'] or ''}")

        pdf.showPage()
        pdf.save()
        
        buffer.seek(0)
        return buffer