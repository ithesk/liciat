from odoo import api, fields, models, tools

class SupplierQuoteAnalysis(models.Model):
    _name = 'supplier.quote.analysis'
    _description = 'Análisis de Cotizaciones de Proveedores'
    _auto = False
    _order = 'price_unit'

    product_id = fields.Many2one('product.product', string='Producto', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Proveedor', readonly=True)
    quote_id = fields.Many2one('supplier.quote', string='Cotización', readonly=True)
    price_unit = fields.Float('Precio Unitario', readonly=True)
    currency_id = fields.Many2one('res.currency', string='Moneda', readonly=True)
    date = fields.Date('Fecha', readonly=True)
    validity_date = fields.Date('Validez', readonly=True)
    delivery_time = fields.Integer('Tiempo de Entrega', readonly=True)
    warranty_time = fields.Integer('Garantía', readonly=True)
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('confirmed', 'Confirmada'),
        ('expired', 'Expirada'),
        ('canceled', 'Cancelada')
    ], string='Estado', readonly=True)
    is_valid = fields.Boolean('Válida', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE or REPLACE VIEW %s AS (
                SELECT
                    row_number() OVER () as id,
                    l.product_id,
                    q.partner_id,
                    l.quote_id,
                    l.price_unit,
                    q.currency_id,
                    q.date,
                    q.validity_date,
                    l.delivery_time,
                    l.warranty_time,
                    q.state,
                    (q.state = 'confirmed' AND 
                     (q.validity_date IS NULL OR q.validity_date >= CURRENT_DATE)) as is_valid
                FROM supplier_quote_line l
                JOIN supplier_quote q ON l.quote_id = q.id
                WHERE q.state != 'canceled'
            )
        """ % (self._table,))