from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)

class TenderState(models.Model):
    _name = 'tender.state'
    _description = 'Estados de Licitación'
    _order = 'sequence'

    name = fields.Char('Nombre', required=True, translate=True)
    code = fields.Char('Código', required=True)
    sequence = fields.Integer('Secuencia', default=10)
    description = fields.Text('Descripción')
    is_done = fields.Boolean('Es Estado Final', default=False)
    fold = fields.Boolean('Plegado en Kanban', default=False)
    color = fields.Integer('Color', default=0)

    _sql_constraints = [
        ('unique_code', 'UNIQUE(code)', 'El código de estado debe ser único')
    ]


class TenderTags(models.Model):
    _name = 'tender.tags'
    _description = 'Etiquetas de Licitación'

    name = fields.Char('Nombre', required=True)
    color = fields.Integer('Color', default=0)

    _sql_constraints = [
        ('name_uniq', 'unique (name)', "El nombre de la etiqueta ya existe!"),
    ]