from odoo import api, fields, models, _
from dateutil.relativedelta import relativedelta

class GovernmentDocument(models.Model):
    _name = 'government.document'
    _description = 'Documento Gubernamental Requerido'
    _order = 'sequence, id'

    name = fields.Char('Nombre del Documento', required=True)
    code = fields.Char('Código', help="Código de referencia del documento")
    description = fields.Text('Descripción')
    sequence = fields.Integer('Secuencia', default=10)
    is_required = fields.Boolean('Obligatorio', default=True)
    attachment_id = fields.Many2one('ir.attachment', string='Archivo Adjunto')
    document_type = fields.Selection([
        ('identification', 'Documento de Identidad'),
        ('tax', 'Documento Fiscal'),
        ('registration', 'Registro Mercantil/Comercial'),
        ('certification', 'Certificación'),
        ('technical', 'Documento Técnico'),
        ('other', 'Otro')
    ], string='Tipo de Documento', default='other', required=True)
    expiration_date = fields.Date('Fecha de Vencimiento')
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', string='Compañía', 
                               default=lambda self: self.env.company, required=True)
    
    # Número o identificador único asociado al documento
    reference_number = fields.Char('Número de Referencia', 
                                 help="Por ejemplo: Número de Cédula, RNC, Registro, etc.")
    
    # Para documentos que requieren renovación
    issue_date = fields.Date('Fecha de Emisión')
    issuing_entity = fields.Char('Entidad Emisora')
    
    # Estado del documento
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('valid', 'Válido'),
        ('expired', 'Vencido'),
        ('pending_renewal', 'Pendiente de Renovación')
    ], string='Estado', default='draft', compute='_compute_state', store=True)
    
    @api.depends('expiration_date')
    def _compute_state(self):
        today = fields.Date.today()
        for record in self:
            if not record.expiration_date:
                record.state = 'valid' if record.attachment_id else 'draft'
            else:
                if record.expiration_date < today:
                    record.state = 'expired'
                elif record.expiration_date < today + relativedelta(months=1):
                    
                    record.state = 'pending_renewal'
                else:
                    record.state = 'valid'