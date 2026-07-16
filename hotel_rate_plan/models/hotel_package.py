from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class HotelPackage(models.Model):
    _name = 'hotel.package'
    _description = 'Hotel Bundled Packages'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Package Name", required=True, tracking=True)
    code = fields.Char(string="Package Code", required=True, tracking=True)
    valid_from = fields.Date(string="Valid From")
    valid_to = fields.Date(string="Valid To")

    price_mode = fields.Selection([
        ('fixed', 'Fixed Package Price'),
        ('dynamic', 'Dynamic (Room Rate + Add-ons)')
    ], string="Price Mode", default='fixed', required=True, tracking=True)

    fixed_package_price = fields.Float(string="Fixed Package Price", default=0.0, tracking=True)
    inclusion_notes = fields.Text(string="Package Inclusions")


class HotelBooking(models.Model):
    _inherit = 'hotel.booking'

    package_id = fields.Many2one('hotel.package', string='Select Package', tracking=True)
    fixed_package_price = fields.Float(
        string="Package Price",
        related='package_id.fixed_package_price',
        readonly=True,
        store=True
    )

    @api.depends('package_id.fixed_package_price', 'package_id.price_mode')
    def _compute_room_subtotal(self):
        super()._compute_room_subtotal()
        for record in self:
            package_bill = 0.0
            if record.package_id and record.package_id.price_mode == 'fixed':
                package_bill = record.fixed_package_price or 0.0
            record.room_subtotal += package_bill


class HotelFolio(models.Model):
    _inherit = 'hotel.folio'

    @api.model_create_multi
    def create(self, vals_list):
        folios = super(HotelFolio, self).create(vals_list)

        for folio in folios:
            if folio.booking_id and folio.booking_id.package_id and folio.booking_id.fixed_package_price > 0:
                existing_line = folio.folio_line_ids.filtered(lambda l: 'Package:' in l.name)

                if not existing_line:
                    package_product = self.env['product.product'].search([('name', '=', 'Hotel Package')], limit=1)

                    if not package_product:
                        package_product = self.env['product.product'].create({
                            'name': 'Hotel Package',
                            'type': 'service',
                            'invoice_policy': 'order',
                        })

                    self.env['hotel.folio.line'].create({
                        'folio_id': folio.id,
                        'product_id': package_product.id,
                        'name': f"Package: {folio.booking_id.package_id.name}",
                        'quantity': 1.0,
                        'price_unit': folio.booking_id.fixed_package_price,
                    })

        folios.invalidate_recordset(['folio_line_ids'])
        return folios


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.model_create_multi
    def create(self, vals_list):
        invoices = super(AccountMove, self).create(vals_list)

        for invoice in invoices:
            if invoice.move_type == 'out_invoice':
                package_lines = invoice.invoice_line_ids.filtered(lambda l: 'Package:' in l.name)
                if package_lines:
                    package_lines.write({'tax_ids': [(5, 0, 0)]})

                    invoice._compute_tax_totals()

        return invoices