from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta
import logging
import math

_logger = logging.getLogger(__name__)

class TenderProposal(models.Model):
    _name = 'tender.proposal'
    _description = 'Propuesta de Licitación'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc, id desc'

    name = fields.Char('Número de Propuesta', required=True, copy=False, 
                      readonly=True, states={'draft': [('readonly', False)]}, 
                      index=True, default=lambda self: _('Nueva'))
    
    tender_id = fields.Many2one('tender.tender', string='Licitación', 
                               required=True, ondelete='restrict', tracking=True)
    
    partner_id = fields.Many2one('res.partner', string='Proveedor', 
                                required=True, tracking=True, 
                                domain=[('is_company', '=', True)])
    
    user_id = fields.Many2one('res.users', string='Responsable', 
                             default=lambda self: self.env.user, tracking=True)
    
    submission_date = fields.Date('Fecha de Presentación', default=fields.Date.today, 
                                 required=True, tracking=True)
    
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('submitted', 'Presentada'),
        ('in_review', 'En Revisión'),
        ('selected', 'Seleccionada'),
        ('awarded', 'Adjudicada'),
        ('rejected', 'Rechazada'),
        ('canceled', 'Cancelada')
    ], string='Estado', default='draft', tracking=True)
    
    is_our_company = fields.Boolean('Es Nuestra Propuesta', default=False, tracking=True,
                                  help="Indica si esta propuesta es de nuestra empresa")
    
    company_id = fields.Many2one('res.company', string='Compañía', 
                                required=True, default=lambda self: self.env.company)
    
    currency_id = fields.Many2one('res.currency', string='Moneda', 
                                 required=True, related='tender_id.currency_id', store=True)
    
    line_ids = fields.One2many('tender.proposal.line', 'proposal_id', 
                               string='Líneas de Propuesta')
    
    amount_untaxed = fields.Monetary(string='Base Imponible', store=True, 
                                    compute='_compute_amount', tracking=True)
    
    amount_tax = fields.Monetary(string='Impuestos', store=True, 
                                compute='_compute_amount', tracking=True)
    
    amount_total = fields.Monetary(string='Total', store=True, 
                                  compute='_compute_amount', tracking=True)
    
    note = fields.Text('Notas Internas')
    terms = fields.Text('Términos y Condiciones')
    technical_proposal = fields.Html('Propuesta Técnica', sanitize=True)
    
    attachment_ids = fields.Many2many('ir.attachment', string='Documentos Adjuntos')
    
    evaluation_ids = fields.One2many('tender.proposal.evaluation', 'proposal_id', 
                                    string='Evaluaciones')
    
    score = fields.Float('Puntuación', compute='_compute_score', store=True)
    
    color = fields.Integer('Color', compute='_compute_color')
    active = fields.Boolean(default=True, string='Activo')

    government_document_ids = fields.Many2many(
        'government.document', 
        string='Documentos Gubernamentales',
        help="Documentos requeridos por entidades gubernamentales"
    )
    
    bidding_data_id = fields.Many2one(
        'government.bidding.data',
        string='Datos de Licitación',
        default=lambda self: self.env['government.bidding.data'].get_company_data().id
    )

    @api.depends('line_ids.cost_price', 'line_ids.price_subtotal')
    def _compute_margin_percentage(self):
            for proposal in self:
                total_cost = sum(line.cost_price * line.product_uom_qty for line in proposal.line_ids)
                if total_cost > 0 and proposal.amount_untaxed > 0:
                    proposal.margin_percentage = (proposal.amount_untaxed - total_cost) / total_cost * 100
                else:
                    proposal.margin_percentage = 0.0

    margin_percentage = fields.Float(
            '% Margen', compute='_compute_margin_percentage', store=True,
            help="Porcentaje de margen global de la propuesta")
    
    def _prepare_government_documents(self):
        """Prepara automáticamente los documentos requeridos"""
        company_data = self.env['government.bidding.data'].get_company_data()
        if company_data and company_data.document_ids:
            self.government_document_ids = [(6, 0, company_data.document_ids.ids)]
            
    @api.model_create_multi
    def create(self, vals_list):
        records = super(TenderProposal, self).create(vals_list)
        for record in records:
            record._prepare_government_documents()
        return records
    

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Nueva')) == _('Nueva'):
                vals['name'] = self.env['ir.sequence'].next_by_code('tender.proposal') or _('Nueva')
        return super(TenderProposal, self).create(vals_list)
    
    @api.depends('line_ids.price_subtotal')
    def _compute_amount(self):
        for proposal in self:
            amount_untaxed = sum(line.price_subtotal for line in proposal.line_ids)
            amount_tax = sum(line.price_tax for line in proposal.line_ids)
            proposal.update({
                'amount_untaxed': amount_untaxed,
                'amount_tax': amount_tax,
                'amount_total': amount_untaxed + amount_tax,
            })
    
    @api.depends('evaluation_ids.score', 'evaluation_ids.weight')
    def _compute_score(self):
        for proposal in self:
            if not proposal.evaluation_ids:
                proposal.score = 0.0
                continue
                
            total_weight = sum(evaluation.weight for evaluation in proposal.evaluation_ids)
            if total_weight:
                weighted_score = sum(evaluation.score * evaluation.weight / 100.0 for evaluation in proposal.evaluation_ids)
                proposal.score = weighted_score
            else:
                proposal.score = 0.0
    
    def _compute_color(self):
        for record in self:
            if record.state == 'draft':
                record.color = 0
            elif record.state == 'submitted':
                record.color = 4  # Azul
            elif record.state == 'in_review':
                record.color = 3  # Amarillo
            elif record.state == 'selected':
                record.color = 10  # Verde
            elif record.state == 'awarded':
                record.color = 2  # Verde oscuro
            elif record.state == 'rejected':
                record.color = 1  # Rojo
            elif record.state == 'canceled':
                record.color = 1  # Rojo
            else:
                record.color = 0
    
    def action_draft(self):
        self.write({'state': 'draft'})
    
    def action_submit(self):
        self.write({'state': 'submitted'})
    
    def action_review(self):
        self.write({'state': 'in_review'})
    
    def action_select(self):
        self.write({'state': 'selected'})
    
    def action_award(self):
        self.write({'state': 'awarded'})
        if self.tender_id.state != 'awarded':
            self.tender_id.action_award()
    
    def action_reject(self):
        self.write({'state': 'rejected'})
    
    def action_cancel(self):
        self.write({'state': 'canceled'})
    
    @api.onchange('tender_id')
    def _onchange_tender_id(self):
        if not self.tender_id:
            return
            
        lines = []
        for line in self.tender_id.line_ids:
            lines.append((0, 0, {
                'name': line.name,
                'product_id': line.product_id.id,
                'product_uom_qty': line.product_uom_qty,
                'product_uom_id': line.product_uom_id.id,
                'price_unit': line.price_unit,
            }))
        
        self.line_ids = lines
    
    def action_generate_evaluation(self):
        self.ensure_one()
        
        # Eliminar evaluaciones existentes
        self.evaluation_ids.unlink()
        
        # Crear nuevas evaluaciones basadas en los criterios de la licitación
        evaluations = []
        for criteria in self.tender_id.criteria_ids:
            evaluations.append((0, 0, {
                'name': criteria.name,
                'description': criteria.description,
                'weight': criteria.weight,
                'score': 0.0,
            }))
        
        self.write({'evaluation_ids': evaluations})
        
        return {
            'name': _('Evaluar Propuesta'),
            'view_mode': 'tree,form',
            'res_model': 'tender.proposal.evaluation',
            'domain': [('proposal_id', '=', self.id)],
            'type': 'ir.actions.act_window',
            'target': 'current',
        }
    
    def action_print_proposal(self):
        self.ensure_one()
        return self.env.ref('tender_management.action_report_tender_proposal').report_action(self)


class TenderProposalLine(models.Model):
    _name = 'tender.proposal.line'
    _description = 'Línea de Propuesta'
    _order = 'sequence, id'

    sequence = fields.Integer(string='Secuencia', default=10)
    proposal_id = fields.Many2one('tender.proposal', string='Propuesta', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Producto', domain=[('sale_ok', '=', True)])
    name = fields.Char('Descripción', required=True)
    product_uom_qty = fields.Float('Cantidad', required=True, default=1.0)
    product_uom_id = fields.Many2one('uom.uom', string='UdM', required=True)
    price_unit = fields.Float('Precio Unitario', required=True, digits='Product Price')
    
    tax_ids = fields.Many2many('account.tax', string='Impuestos', 
                             domain=['|', ('active', '=', False), ('active', '=', True)])
    
    discount = fields.Float('Descuento (%)', digits='Discount', default=0.0)
    
    price_subtotal = fields.Monetary('Subtotal', compute='_compute_amount', store=True)
    price_tax = fields.Monetary('Importe Impuestos', compute='_compute_amount', store=True)
    price_total = fields.Monetary('Total', compute='_compute_amount', store=True)
    
    company_id = fields.Many2one(related='proposal_id.company_id')
    currency_id = fields.Many2one(related='proposal_id.currency_id')

    
    supplier_quote_count = fields.Integer('Cotizaciones', compute='_compute_supplier_quote_count')
    best_supplier_price = fields.Float('Mejor Precio', compute='_compute_best_supplier_price')
    best_supplier_id = fields.Many2one('res.partner', string='Mejor Proveedor', compute='_compute_best_supplier_price')
    margin = fields.Float('Margen (%)', default=15.0)
    cost_price = fields.Float('Costo', compute='_compute_cost_price')
    
    def _compute_supplier_quote_count(self):
        for line in self:
            if line.product_id:
                # Contar cotizaciones activas para este producto
                quotes = self.env['supplier.quote.line'].search([
                    ('product_id', '=', line.product_id.id),
                    ('quote_id.state', '=', 'confirmed')
                ])
                line.supplier_quote_count = len(quotes)
            else:
                line.supplier_quote_count = 0
    
    def _compute_best_supplier_price(self):
        for line in self:
            best_price = 0.0
            best_supplier = False
            
            if line.product_id:
                # Buscar cotizaciones activas para este producto
                quote_lines = self.env['supplier.quote.line'].search([
                    ('product_id', '=', line.product_id.id),
                    ('quote_id.state', '=', 'confirmed')
                ])
                
                if quote_lines:
                    # Encontrar el mejor precio (más bajo)
                    min_price_line = min(quote_lines, key=lambda x: x.price_unit)
                    best_price = min_price_line.price_unit
                    best_supplier = min_price_line.quote_id.partner_id.id
            
            line.best_supplier_price = best_price
            line.best_supplier_id = best_supplier
    
    @api.depends('best_supplier_price', 'margin')
    def _compute_cost_price(self):
        for line in self:
            if line.best_supplier_price > 0:
                # Usar el mejor precio de proveedor como costo
                line.cost_price = line.best_supplier_price
            else:
                # Usar el costo estándar del producto
                line.cost_price = line.product_id.standard_price
    
    @api.onchange('cost_price', 'margin')
    def _onchange_margin(self):
        """Calcular precio de venta basado en costo y margen"""
        for line in self:
            if line.cost_price > 0:
                # Precio = Costo + (Costo * Margen / 100)
                line.price_unit = line.cost_price * (1 + line.margin / 100)
                
    def action_view_supplier_quotes(self):
        """Ver cotizaciones de proveedores para este producto"""
        self.ensure_one()
        quote_lines = self.env['supplier.quote.line'].search([
            ('product_id', '=', self.product_id.id),
            ('quote_id.state', '=', 'confirmed')
        ])
        
        return {
            'name': _('Cotizaciones para %s') % self.product_id.name,
            'type': 'ir.actions.act_window',
            'res_model': 'supplier.quote.line',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', quote_lines.ids)],
            'context': {'create': False}
        }
    
    @api.depends('product_uom_qty', 'price_unit', 'tax_ids', 'discount')
    def _compute_amount(self):
        for line in self:
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            taxes = line.tax_ids.compute_all(price, line.proposal_id.currency_id, 
                                           line.product_uom_qty, 
                                           product=line.product_id)
            line.update({
                'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                'price_total': taxes['total_included'],
                'price_subtotal': taxes['total_excluded'],
            })
    
    @api.onchange('product_id')
    def _onchange_product_id(self):
        if not self.product_id:
            return
            
        self.name = self.product_id.name
        self.product_uom_id = self.product_id.uom_id
        self.price_unit = self.product_id.list_price
        
        # Impuestos por defecto
        taxes = self.product_id.taxes_id.filtered(lambda x: x.company_id == self.company_id)
        self.tax_ids = taxes


class TenderProposalEvaluation(models.Model):
    _name = 'tender.proposal.evaluation'
    _description = 'Evaluación de Propuesta'
    _order = 'sequence, id'

    sequence = fields.Integer(string='Secuencia', default=10)
    proposal_id = fields.Many2one('tender.proposal', string='Propuesta', required=True, ondelete='cascade')
    name = fields.Char('Criterio', required=True)
    description = fields.Text('Descripción')
    weight = fields.Float('Peso (%)', required=True)
    score = fields.Float('Puntuación (0-100)', required=True)
    notes = fields.Text('Observaciones')
    
    @api.constrains('score')
    def _check_score(self):
        for evaluation in self:
            if evaluation.score < 0 or evaluation.score > 100:
                raise ValidationError(_('La puntuación debe estar entre 0 y 100.'))
    
    @api.constrains('weight')
    def _check_weight(self):
        for evaluation in self:
            if evaluation.weight <= 0 or evaluation.weight > 100:
                raise ValidationError(_('El peso debe estar entre 0 y 100.'))