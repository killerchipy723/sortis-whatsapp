from flask import Blueprint, request, jsonify, send_file
from models.mensaje import CuotaModel
from services.mensaje_service import ReciboService

mensaje_bp = Blueprint('mensaje', __name__)

@mensaje_bp.route('/update-cuota', methods=['POST'])
def update_cuota():
    data = request.json or request.form
    
    try:
        idcuota = int(data.get('idcuota'))
        importe = float(data.get('importe'))
        nrecibo = int(data.get('nrecibo'))
        idvendedor = int(data.get('idvendedor'))
        fechapago = data.get('fechapago')
        formapago = data.get('formapago')
        obs = data.get('obs')
        estado = data.get('estado')
    except (TypeError, ValueError):
        return "Datos no válidos", 400

    exito = CuotaModel.actualizar_cuota(idcuota, importe, formapago, nrecibo, fechapago, idvendedor, obs, estado)
    if exito:
        return "Cuota actualizada correctamente", 200
    return "Cuota no encontrada", 404

@mensaje_bp.route('/generar-pdf/<int:idc>', methods=['GET'])
def generar_pdf(idc):
    buffer = ReciboService.generar_pdf_recibo(idc)
    if not buffer:
        return "No se encontró la cuota", 404

    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"OrdenPago-{idc}.pdf",
        mimetype='application/pdf'
    )