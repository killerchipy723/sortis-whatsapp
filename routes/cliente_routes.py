from flask import Blueprint, request, jsonify, session
from models.cliente import ClienteModel
from models.mensaje import CuotaModel

cliente_bp = Blueprint('cliente', __name__)

@cliente_bp.route('/buscar-afiliado', methods=['GET'])
def buscar_afiliado():
    if 'user' not in session:
        return jsonify({"error": "No autorizado"}), 401
    
    dni = request.args.get('dni')
    if not dni:
        return jsonify({"error": "DNI requerido"}), 400

    afiliados = ClienteModel.buscar_por_dni(dni)
    return jsonify(afiliados)

@cliente_bp.route('/get-cuotas', methods=['GET'])
def get_cuotas():
    try:
        idafiliado = int(request.args.get('idafiliado'))
        idplan = int(request.args.get('idplan'))
    except (TypeError, ValueError):
        return jsonify({"error": "Parámetros inválidos"}), 400

    cuotas = CuotaModel.get_cuotas_por_afiliado_y_plan(idafiliado, idplan)
    if cuotas:
        return jsonify(cuotas)
    return jsonify({"message": "No se encontraron cuotas"}), 404