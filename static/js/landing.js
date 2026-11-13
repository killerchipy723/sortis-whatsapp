let idPlanSeleccionado = '';
let nombrePlanActual = '';

function abrirInscripcion(idPlan, nombrePlan) {
    idPlanSeleccionado = idPlan;
    nombrePlanActual = nombrePlan;
    document.getElementById('nombrePlanSeleccionado').innerText = nombrePlan;
    new bootstrap.Modal(document.getElementById('modalInscripcion')).show();
}

document.addEventListener('DOMContentLoaded', function() {
    const formInscripcion = document.getElementById('formInscripcion');
    
    if (formInscripcion) {
        formInscripcion.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const nombre = document.getElementById('insNombre').value.trim().toUpperCase();
            const dni = document.getElementById('insDni').value.trim();
            const cuil = document.getElementById('insCuil').value.trim();
            const domicilio = document.getElementById('insDomicilio').value.trim();
            const tel = document.getElementById('insTel').value.trim();
            const aceptaContrato = document.getElementById('checkContrato').checked ? 'on' : '';
            
            const formData = new FormData();
            formData.append('nombre', nombre);
            formData.append('dni', dni);
            formData.append('cuil', cuil);
            formData.append('domicilio', domicilio);
            formData.append('telefono', tel);
            formData.append('idplan', idPlanSeleccionado);
            formData.append('contrato', aceptaContrato);
            
            try {
                const response = await fetch('/api/inscribir', {
                    method: 'POST',
                    body: formData
                });
                
                const resultado = await response.json();
                
                if (resultado.success) {
                    alert(resultado.message);
                    
                    const telefonoSortis = "5493810000000"; // Tu número comercial
                    const mensaje = `Hola Sortis Motos! Acabo de registrarme en la web al plan *${nombrePlanActual}*.\n\n*Mis datos:*\n- Nombre: ${nombre}\n- DNI: ${dni}\n- CUIL: ${cuil}\n- Domicilio: ${domicilio}\n- Teléfono: ${tel}\n\nQuedo a la espera de las instrucciones para el pago virtual.`;
                    
                    window.open(`https://wa.me/${telefonoSortis}?text=${encodeURIComponent(mensaje)}`, '_blank');
                    location.reload();
                } else {
                    alert("Aviso: " + resultado.message);
                }
            } catch (error) {
                console.error("Error en la petición:", error);
                alert("Ocurrió un error al conectar con el servidor.");
            }
        });
    }
});