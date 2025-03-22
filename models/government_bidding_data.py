from odoo import api, fields, models, _

class GovernmentBiddingData(models.Model):
    _name = 'government.bidding.data'
    _description = 'Datos para Licitaciones Gubernamentales'
    
    name = fields.Char('Nombre', required=True)
    company_id = fields.Many2one('res.company', string='Compañía', 
                               default=lambda self: self.env.company, required=True)
    
    # Números de registro
    rpe_number = fields.Char('Número RPE', help="Registro de Proveedores del Estado")
    rnc_number = fields.Char('Número RNC/Cédula')
    mercantile_registry = fields.Char('Registro Mercantil')
    
    # Certificaciones
    has_dgi_certification = fields.Boolean('Certificación DGI')
    dgi_certification_number = fields.Char('Número Certificación DGI')
    dgi_expiration_date = fields.Date('Vencimiento Certificación DGI')
    
    # Documentos requeridos
    document_ids = fields.Many2many('government.document', string='Documentos')
    
    # Representante legal
    legal_representative = fields.Char('Representante Legal')
    representative_id = fields.Char('Cédula del Representante')
    representative_position = fields.Char('Cargo del Representante')
    
    # Datos bancarios para licitaciones
    bank_id = fields.Many2one('res.bank', string='Banco')
    bank_account = fields.Char('Cuenta Bancaria')
    
    # Datos adicionales
    additional_notes = fields.Text('Notas Adicionales')
    
    @api.model
    def get_company_data(self, company_id=None):
        """Obtiene los datos de licitación para una compañía específica o la actual"""
        if not company_id:
            company_id = self.env.company.id
            
        data = self.search([('company_id', '=', company_id)], limit=1)
        if not data:
            # Crear datos por defecto si no existen
            data = self.create({
                'name': self.env.company.name + ' - Datos de Licitación',
                'company_id': company_id,
            })
        
        return data