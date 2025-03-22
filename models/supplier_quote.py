from odoo import api, fields, models, _
from datetime import timedelta

class SupplierQuote(models.Model):
    _name = 'supplier.quote'
    _description = 'Cotización de Proveedor'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char('Referencia', required=True, copy=False, 
                     readonly=True, default=lambda self: _('Nueva Cotización'))
    
    partner_id = fields.Many2one('res.partner', string='Proveedor', required=True, 
                               domain=[('supplier_rank', '>', 0)], tracking=True)
    
    date = fields.Date('Fecha', default=fields.Date.today(), required=True, tracking=True)
    validity_date = fields.Date('Fecha de Validez', tracking=True)
    
    currency_id = fields.Many2one('res.currency', string='Moneda', required=True,
                                default=lambda self: self.env.company.currency_id)
    
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('confirmed', 'Confirmada'),
        ('expired', 'Expirada'),
        ('canceled', 'Cancelada')
    ], string='Estado', default='draft', tracking=True)
    
    line_ids = fields.One2many('supplier.quote.line', 'quote_id', string='Líneas')
    
    note = fields.Text('Notas')
    terms = fields.Text('Términos y Condiciones')
    payment_term_id = fields.Many2one('account.payment.term', string='Condiciones de Pago')
    
    attachment_ids = fields.Many2many('ir.attachment', string='Documentos Adjuntos')
    company_id = fields.Many2one('res.company', string='Compañía', 
                              default=lambda self: self.env.company, required=True)
    
    user_id = fields.Many2one('res.users', string='Responsable', 
                            default=lambda self: self.env.user)
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Nueva Cotización')) == _('Nueva Cotización'):
                vals['name'] = self.env['ir.sequence'].next_by_code('supplier.quote') or _('Nueva Cotización')
        return super(SupplierQuote, self).create(vals_list)
    
    def action_confirm(self):
        self.write({'state': 'confirmed'})
    
    def action_cancel(self):
        self.write({'state': 'canceled'})
    
    def action_set_draft(self):
        self.write({'state': 'draft'})
    
    @api.model
    def _cron_check_validity(self):
        """Verificar cotizaciones expiradas"""
        today = fields.Date.today()
        expired_quotes = self.search([
            ('state', '=', 'confirmed'),
            ('validity_date', '<', today)
        ])
        expired_quotes.write({'state': 'expired'})
    
    def copy_to_proposal(self):
        """Crear una propuesta basada en esta cotización"""
        self.ensure_one()
        
        proposal_obj = self.env['tender.proposal']
        proposal_line_obj = self.env['tender.proposal.line']
        
        # Crear cabecera de propuesta
        proposal_vals = {
            'partner_id': self.partner_id.id,
            'currency_id': self.currency_id.id,
            'submission_date': fields.Date.today(),
            'user_id': self.env.user.id,
            'is_our_company': True,
            'terms': self.terms,
            'note': self.note,
        }
        
        new_proposal = proposal_obj.create(proposal_vals)
        
        # Crear líneas de propuesta
        for line in self.line_ids:
            proposal_line_obj.create({
                'proposal_id': new_proposal.id,
                'product_id': line.product_id.id,
                'name': line.name,
                'product_uom_qty': line.quantity,
                'product_uom_id': line.product_uom_id.id,
                'price_unit': line.price_unit,
                'discount': 0.0,
            })
        
        # Abrir la propuesta creada
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'tender.proposal',
            'view_mode': 'form',
            'res_id': new_proposal.id,
            'target': 'current',
            'context': {'form_view_initial_mode': 'edit'},
        }


class SupplierQuoteLine(models.Model):
    _name = 'supplier.quote.line'
    _description = 'Línea de Cotización de Proveedor'
    _order = 'sequence, id'

    sequence = fields.Integer('Secuencia', default=10)
    quote_id = fields.Many2one('supplier.quote', string='Cotización', ondelete='cascade')
    
    product_id = fields.Many2one('product.product', string='Producto', required=True)
    name = fields.Char('Descripción', required=True)
    
    quantity = fields.Float('Cantidad', default=1.0, required=True)
    product_uom_id = fields.Many2one('uom.uom', string='UdM', required=True,
                                   default=lambda self: self.env.ref('uom.product_uom_unit'))
    
    price_unit = fields.Float('Precio Unitario', required=True, digits='Product Price')
    
    currency_id = fields.Many2one(related='quote_id.currency_id')
    subtotal = fields.Monetary('Subtotal', compute='_compute_subtotal', store=True)
    
    delivery_time = fields.Integer('Tiempo de Entrega (días)', help="Tiempo de entrega en días")
    warranty_time = fields.Integer('Garantía (meses)', help="Tiempo de garantía en meses")
    
    notes = fields.Text('Notas')
    
    @api.depends('quantity', 'price_unit')
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.quantity * line.price_unit
    
    @api.onchange('product_id')
    def _onchange_product_id(self):
        if not self.product_id:
            return
        
        self.name = self.product_id.name
        self.product_uom_id = self.product_id.uom_id.id
        
        # Obtener el precio de proveedor si está disponible
        if self.quote_id.partner_id:
            seller = self.product_id._select_seller(
                partner_id=self.quote_id.partner_id,
                quantity=self.quantity,
                date=self.quote_id.date,
                uom_id=self.product_uom_id)
            
            if seller:
                self.price_unit = seller.price
                if seller.delay:
                    self.delivery_time = seller.delay
            else:
                self.price_unit = self.product_id.standard_price