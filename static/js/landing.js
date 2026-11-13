 let planActual = '';
        function abrirInscripcion(nombrePlan) {
            planActual = nombrePlan;
            document.getElementById('nombrePlanSeleccionado').innerText = nombrePlan;
            new bootstrap.Modal(document.getElementById('modalInscripcion')).show();
        }

        document.getElementById('formInscripcion').addEventListener('submit', function(e) {
            e.preventDefault();
            const nombre = document.getElementById('insNombre').value;
            const dni = document.getElementById('insDni').value;
            const tel = document.getElementById('insTel').value;
            
            // Reemplaza este número por el WhatsApp comercial de Sortis Motos (con código de país, ej: 549...)
            const telefonoSortis = "5493810000000"; 
            const mensaje = `Hola Sortis Motos! Quiero inscribirme en el plan *${planActual}*.\n\n*Mis datos:*\n- Nombre: ${nombre}\n- DNI: ${dni}\n- Teléfono: ${tel}`;
            
            window.open(`https://wa.me/${telefonoSortis}?text=${encodeURIComponent(mensaje)}`, '_blank');
        });