from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)

class Tender(models.Model):
    _name = 'tender.tender'
    _description = 'Licitación'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_published desc, id desc'

    name = fields.Char('Número de Licitación', required=True, copy=False, 
                       readonly=True, states={'draft': [('readonly', False)]}, 
                       index=True, default=lambda self: _('Nueva'))
    
    title = fields.Char('Título', required=True, tracking=True)
    description = fields.Html('Descripción', sanitize=True)
    
    entity_id = fields.Many2one('res.partner', string='Entidad Licitante', 
                               required=True, tracking=True, 
                               domain=[('is_company', '=', True)])
    
    contact_id = fields.Many2one('res.partner', string='Contacto', 
                                domain="[('parent_id', '=', entity_id)]")
    
    user_id = fields.Many2one('res.users', string='Responsable', 
                             default=lambda self: self.env.user, tracking=True)
    
    company_id = fields.Many2one('res.company', string='Compañía', 
                                required=True, default=lambda self: self.env.company)
    
    currency_id = fields.Many2one('res.currency', string='Moneda', 
                                 required=True, 
                                 default=lambda self: self.env.company.currency_id)
    
    estimated_budget = fields.Monetary('Presupuesto Estimado', tracking=True)
    
    date_published = fields.Date('Fecha de Publicación', required=True, tracking=True)
    date_closing = fields.Date('Fecha de Cierre', required=True, tracking=True)
    
    state_id = fields.Many2one('tender.state', string='Estado', 
                              required=True, tracking=True, 
                              default=lambda self: self.env['tender.state'].search([('code', '=', 'draft')], limit=1))
    
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('published', 'Publicada'),
        ('in_process', 'En Proceso'),
        ('evaluation', 'En Evaluación'),
        ('awarded', 'Adjudicada'),
        ('closed', 'Cerrada'),
        ('canceled', 'Cancelada')
    ], string='Estado', default='draft', tracking=True)
    
    tag_ids = fields.Many2many('tender.tags', string='Etiquetas')
    
    # Documentos
    document_ids = fields.One2many('tender.document', 'tender_id', 
                                  string='Documentos')
    
    # Criterios de evaluación
    criteria_ids = fields.One2many('tender.criteria', 'tender_id', 
                                  string='Criterios de Evaluación')
    
    # Propuestas relacionadas
    proposal_ids = fields.One2many('tender.proposal', 'tender_id', 
                                  string='Propuestas')
    proposal_count = fields.Integer(compute='_compute_proposal_count', 
                                   string='Número de Propuestas')
    
    # Productos o servicios requeridos
    line_ids = fields.One2many('tender.line', 'tender_id', 
                              string='Productos/Servicios')
    
    has_our_proposal = fields.Boolean(compute='_compute_has_our_proposal', 
                                     string='Tenemos Propuesta', store=True)
    
    our_proposal_id = fields.Many2one('tender.proposal', compute='_compute_has_our_proposal', 
                                     string='Nuestra Propuesta', store=True)
    
    notes = fields.Text('Notas Internas')
    priority = fields.Selection([
        ('0', 'Baja'),
        ('1', 'Media'),
        ('2', 'Alta'),
        ('3', 'Muy Alta')
    ], default='1', string='Prioridad')
    
    color = fields.Integer('Color', compute='_compute_color')
    
    kanban_state = fields.Selection([
        ('normal', 'En progreso'),
        ('done', 'Listo para siguiente etapa'),
        ('blocked', 'Bloqueado')
    ], string='Estado Kanban', default='normal', tracking=True)

    active = fields.Boolean(default=True, string='Activo')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Nueva')) == _('Nueva'):
                vals['name'] = self.env['ir.sequence'].next_by_code('tender.tender') or _('Nueva')
        return super(Tender, self).create(vals_list)
    
    def _compute_proposal_count(self):
        for tender in self:
            tender.proposal_count = len(tender.proposal_ids)
    
    @api.depends('proposal_ids', 'proposal_ids.is_our_company')
    def _compute_has_our_proposal(self):
        for tender in self:
            our_proposals = tender.proposal_ids.filtered(lambda p: p.is_our_company)
            tender.has_our_proposal = bool(our_proposals)
            tender.our_proposal_id = our_proposals[0].id if our_proposals else False
    
    def _compute_color(self):
        for record in self:
            if record.state == 'draft':
                record.color = 0
            elif record.state == 'published':
                record.color = 4  # Azul
            elif record.state == 'in_process':
                record.color = 1  # Rojo claro
            elif record.state == 'evaluation':
                record.color = 3  # Amarillo
            elif record.state == 'awarded':
                record.color = 10  # Verde
            elif record.state == 'closed':
                record.color = 5  # Morado
            elif record.state == 'canceled':
                record.color = 1  # Rojo
            else:
                record.color = 0
    
    def action_draft(self):
        self.write({'state': 'draft'})
    
    def action_publish(self):
        self.write({'state': 'published'})
    
    def action_process(self):
        self.write({'state': 'in_process'})
    
    def action_evaluate(self):
        self.write({'state': 'evaluation'})
    
    def action_award(self):
        self.write({'state': 'awarded'})
    
    def action_close(self):
        self.write({'state': 'closed'})
    
    def action_cancel(self):
        self.write({'state': 'canceled'})
    
    def action_view_proposals(self):
        self.ensure_one()
        return {
            'name': _('Propuestas'),
            'view_mode': 'tree,form',
            'res_model': 'tender.proposal',
            'domain': [('tender_id', '=', self.id)],
            'type': 'ir.actions.act_window',
            'context': {'default_tender_id': self.id}
        }
    
    def action_create_proposal(self):
        self.ensure_one()
        return {
            'name': _('Crear Propuesta'),
            'view_mode': 'form',
            'res_model': 'tender.proposal',
            'type': 'ir.actions.act_window',
            'context': {
                'default_tender_id': self.id,
                'default_is_our_company': True,
            }
        }
    
    @api.constrains('date_published', 'date_closing')
    def _check_dates(self):
        for tender in self:
            if tender.date_closing and tender.date_published and tender.date_closing < tender.date_published:
                raise ValidationError(_('La fecha de cierre no puede ser anterior a la fecha de publicación.'))
    
    @api.onchange('entity_id')
    def _onchange_entity_id(self):
        if self.entity_id:
            return {'domain': {'contact_id': [('parent_id', '=', self.entity_id.id)]}}
        return {'domain': {'contact_id': []}}


class TenderLine(models.Model):
    _name = 'tender.line'
    _description = 'Línea de Licitación'
    _order = 'sequence, id'

    sequence = fields.Integer(string='Secuencia', default=10)
    tender_id = fields.Many2one('tender.tender', string='Licitación', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Producto', domain=[('sale_ok', '=', True)])
    name = fields.Char('Descripción', required=True)
    product_uom_qty = fields.Float('Cantidad', required=True, default=1.0)
    product_uom_id = fields.Many2one('uom.uom', string='UdM', required=True, 
                                    default=lambda self: self.env['uom.uom'].search([], limit=1, order='id'))
    price_unit = fields.Float('Precio Unitario', digits='Product Price')
    price_subtotal = fields.Monetary('Subtotal', compute='_compute_amount', store=True)
    company_id = fields.Many2one(related='tender_id.company_id', store=True)
    currency_id = fields.Many2one(related='tender_id.currency_id', store=True)
    
    @api.depends('product_uom_qty', 'price_unit')
    def _compute_amount(self):
        for line in self:
            line.price_subtotal = line.product_uom_qty * line.price_unit
    
    @api.onchange('product_id')
    def _onchange_product_id(self):
        if not self.product_id:
            return
        
        self.name = self.product_id.name
        self.product_uom_id = self.product_id.uom_id
        self.price_unit = self.product_id.list_price


class TenderDocument(models.Model):
    _name = 'tender.document'
    _description = 'Documento de Licitación'
    _order = 'sequence, id'

    sequence = fields.Integer(string='Secuencia', default=10)
    name = fields.Char('Nombre', required=True)
    description = fields.Text('Descripción')
    tender_id = fields.Many2one('tender.tender', string='Licitación', required=True, ondelete='cascade')
    attachment_id = fields.Many2one('ir.attachment', string='Archivo')
    date = fields.Date('Fecha', default=fields.Date.today)
    is_required = fields.Boolean('Requerido para Propuesta', default=False)
    
    def action_download(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=true' % self.attachment_id.id,
            'target': 'self',
        }


class TenderCriteria(models.Model):
    _name = 'tender.criteria'
    _description = 'Criterio de Evaluación'
    _order = 'sequence, id'

    sequence = fields.Integer(string='Secuencia', default=10)
    name = fields.Char('Nombre', required=True)
    description = fields.Text('Descripción')
    tender_id = fields.Many2one('tender.tender', string='Licitación', required=True, ondelete='cascade')
    weight = fields.Float('Peso (%)', required=True, default=100.0)
    
    @api.constrains('weight')
    def _check_weight(self):
        for criteria in self:
            if criteria.weight <= 0 or criteria.weight > 100:
                raise ValidationError(_('El peso debe estar entre 0 y 100.'))