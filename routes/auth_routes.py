from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify, flash
from models.usuario import UsuarioModel

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/', methods=['GET'])
def index():
    if 'user' in session:
        return redirect(url_for('dashboard.index'))
    return render_template('auth/login.html')

@auth_bp.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')

    user = UsuarioModel.autenticar(username, password)
    if user:
        session['user'] = user
        if user.get('nivel') == 'Gerente':
            return redirect(url_for('auth.registro'))
        return redirect(url_for('dashboard.index'))

    flash("Datos incorrectos o usuario no autorizado", "danger")
    return redirect(url_for('auth.index'))

@auth_bp.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({"message": "Sesión cerrada exitosamente"}), 200

@auth_bp.route('/get-user-data', methods=['GET'])
def get_user_data():
    if 'user' in session:
        return jsonify({"apenomb": session['user'].get('apenomb')})
    return jsonify({"error": "No autorizado"}), 401